"""The live loop: capture → detect change → OCR → dedupe → translate → emit.

Runs in its own QThread so the UI and the game never wait for it. CPU stays low because
OCR only runs after the picture changed *and* settled, and translation only runs for text
that is actually new.
"""
from __future__ import annotations

import collections
import time

from PySide6.QtCore import QThread, Signal

from .capture import Capturer, ChangeDetector
from .engines import AllEnginesFailed, Manager, Request
from .ocr import OcrError, create_ocr
from .platform_utils import process_usage
from .textproc import TextTracker, classify, group_lines


class LiveTranslator(QThread):
    status = Signal(str, str)          # code, Arabic message: running|paused|offline|error|stopped|reading|translating
    result = Signal(dict)              # see _emit_result
    cleared = Signal()                 # the game text disappeared from the screen
    metrics = Signal(dict)

    RETRY_OFFLINE_S = 3.0

    def __init__(self, settings, store, manager: Manager, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.store = store
        self.manager = manager
        self._stop = False
        self._paused = False
        self._force = False
        self._exclusions: list[tuple[int, int, int, int]] = []   # absolute physical rects to ignore
        self.tracker = TextTracker()
        self.context = collections.deque(maxlen=6)
        self._pending: list | None = None
        self._next_retry = 0.0

    # ---------- control (called from the UI thread) ----------
    def stop(self):
        self._stop = True

    def set_paused(self, p: bool):
        self._paused = p
        self.status.emit("paused" if p else "running", "متوقف مؤقتاً" if p else "يعمل")

    def trigger(self):
        """Translate what is on screen now, even if it was already translated."""
        self._force = True

    def reset_text(self):
        self.tracker.reset()

    def set_exclusions(self, rects):
        self._exclusions = list(rects)

    # ---------- loop ----------
    def run(self):
        prof = self.settings.profile
        try:
            self._ocr = create_ocr(prof["ocr"]["engine"], _ocr_lang(prof["lang"]["src"]), prof["ocr"]["min_conf"])
        except OcrError as e:
            self.status.emit("error", f"تعذّر تشغيل قراءة النص: {e}")
            return
        cap = Capturer()
        cap_cfg = prof["capture"]
        detector = ChangeDetector(cap_cfg["sensitivity"], cap_cfg["stable_ms"])
        self.status.emit("running", f"يعمل ({self._ocr.name}) — بانتظار نص جديد")
        process_usage()
        last_metrics = 0.0
        stats = {"frames": 0, "reads": 0, "translations": 0, "cap_ms": 0.0, "ocr_ms": 0.0, "tr_ms": 0.0}
        while not self._stop:
            t_loop = time.perf_counter()
            prof = self.settings.profile
            c = prof["capture"]
            detector.sensitivity, detector.stable_ms = c["sensitivity"], c["stable_ms"]
            if self._paused:
                self.msleep(150)
                continue
            try:
                t0 = time.perf_counter()
                img, box = cap.grab(c["monitor"], None if c["full"] else c["region"])
                stats["cap_ms"] = (time.perf_counter() - t0) * 1000
                stats["frames"] += 1
                now = time.monotonic()
                fire = detector.update(img, now)
                retry_due = self._pending is not None and now >= self._next_retry
                if self._force:
                    fire, self._force = True, False
                    self.tracker.reset()
                if fire or retry_due:
                    self._read_and_translate(self._ocr, img, box, prof, stats, retry_due and not fire)
            except Exception as e:  # never let one bad frame kill the loop
                self.status.emit("error", f"خطأ أثناء الالتقاط: {e}")
                self.msleep(1000)
            if time.monotonic() - last_metrics > 1.0:
                cpu, mem = process_usage()
                self.metrics.emit({**stats, "cpu": cpu, "mem": mem, "engines": self.manager.engine_state()})
                last_metrics = time.monotonic()
            spent = (time.perf_counter() - t_loop) * 1000
            self.msleep(int(max(30, c["interval_ms"] - spent)))
        self.status.emit("stopped", "متوقف")

    def _read_and_translate(self, ocr, img, box, prof, stats, retry_only: bool):
        if retry_only:
            items = self._pending
        else:
            self.status.emit("reading", "يقرأ النص…")
            t0 = time.perf_counter()
            try:
                lines = ocr.read(img)
            except Exception as e:
                if getattr(ocr, "name", "") == "rapid":
                    raise
                # Windows OCR failed on this machine: switch to the bundled engine and carry on
                from .ocr import RapidOcr
                self._ocr = ocr = RapidOcr(prof["ocr"]["min_conf"])
                self.status.emit("running", f"تحوّلت القراءة إلى المحرك المدمج ({e})")
                lines = ocr.read(img)
            stats["ocr_ms"] = (time.perf_counter() - t0) * 1000
            stats["reads"] += 1
            lines = [l for l in lines if not self._excluded(l, box)]
            blocks = group_lines(lines)
            items = [{"label": b.label, "src": b.text, "box": b.box} for b in blocks]
            for it, kind in zip(items, classify(items)):
                it["kind"] = kind
            texts = [b.full_text for b in blocks]
            if not texts:
                if self.tracker.current:
                    self.tracker.reset()
                    self.cleared.emit()
                self.status.emit("running", "يعمل — لا يوجد نص على الشاشة")
                return
            if not self.tracker.is_new(texts):
                self.status.emit("running", "يعمل — النص لم يتغير")
                return
        self.status.emit("translating", "يترجم…")
        t0 = time.perf_counter()
        try:
            out, engine, source = self._translate_items(items, prof)
        except AllEnginesFailed as e:
            self._pending = items
            self._next_retry = time.monotonic() + self.RETRY_OFFLINE_S
            if e.network:
                self.status.emit("offline", "لا يوجد اتصال بالإنترنت — سأعيد المحاولة تلقائياً")
            else:
                self.status.emit("error", f"تعذّرت الترجمة: {e}")
            return
        self._pending = None
        stats["tr_ms"] = (time.perf_counter() - t0) * 1000
        stats["translations"] += 1
        self._emit_result(out, engine, source, prof, stats)
        self.status.emit("running", "يعمل — بانتظار نص جديد")

    def _translate_items(self, items, prof):
        src, tgt, style = prof["lang"]["src"], prof["lang"]["tgt"], prof["translate"]["style"]
        ctx = tuple(self.context)
        engine_used, source_used = "", ""
        # One request for the whole screen when possible (fast, keeps context), split back by line.
        joined = "\n".join(it["src"] for it in items)
        res = self.manager.translate(Request(joined, src, tgt, style, ctx))
        parts = [p.strip() for p in res.text.split("\n") if p.strip()]
        if len(parts) == len(items):
            for it, p in zip(items, parts):
                it["tr"] = p
            engine_used, source_used = res.engine, res.source
        else:  # the engine merged/split lines: translate block by block
            for it in items:
                r = self.manager.translate(Request(it["src"], src, tgt, style, ctx))
                it["tr"], engine_used, source_used = r.text, r.engine, r.source
        labels = [it["label"] for it in items if it["label"]]
        if labels:
            lr = self.manager.translate(Request("\n".join(labels), src, tgt, style))
            lparts = [p.strip() for p in lr.text.split("\n")]
            it_l = iter(lparts if len(lparts) == len(labels) else labels)
            for it in items:
                if it["label"]:
                    it["label_tr"] = next(it_l, it["label"])
        for it in items:
            self.context.append((it["label"] + ": " if it["label"] else "") + it["src"])
        return items, engine_used, source_used

    def _emit_result(self, items, engine, source, prof, stats):
        tr_text = "\n".join((f"{it.get('label_tr', it['label'])}: " if it["label"] else "") + it["tr"] for it in items)
        src_text = "\n".join((f"{it['label']}: " if it["label"] else "") + it["src"] for it in items)
        hid = self.store.add_history(prof["name"], src_text, tr_text, engine, prof["lang"]["src"], prof["lang"]["tgt"])
        self.result.emit({"items": items, "engine": engine, "source": source, "text": tr_text, "src_text": src_text,
                          "history_id": hid, "ms": {"ocr": round(stats["ocr_ms"]), "tr": round(stats["tr_ms"])}})

    def _excluded(self, line, box) -> bool:
        if not self._exclusions:
            return False
        cx = box["left"] + line.x + line.w / 2
        cy = box["top"] + line.y + line.h / 2
        return any(x <= cx <= x + w and y <= cy <= y + h for x, y, w, h in self._exclusions)


def _ocr_lang(src: str) -> str:
    return "en" if src in ("auto", "", None) else src
