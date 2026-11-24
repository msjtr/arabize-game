"""The live loop: capture → detect change → OCR → translate (in the background) → show.

Runs in its own QThread so the UI and the game never wait for it.

Built for fast text:
- the screen is compared every few tens of milliseconds and read as soon as it settles, or every max_wait_ms while
  the picture keeps moving (camera, particles), so text over a moving scene is not skipped;
- translation runs on worker threads, so the next frame is read while the last one is still being translated;
- text that is still being typed out (typewriter dialogue) is translated once it stops growing, without waiting
  for a whole calm screen;
- a line that disappeared before its translation arrived is still shown long enough to read it.
"""
from __future__ import annotations

import collections
import concurrent.futures as cf
import threading
import time

from PySide6.QtCore import QThread, Signal

from .capture import Capturer, ChangeDetector
from .engines import AllEnginesFailed, Manager, Request
from .logs import log
from .ocr import OcrError, create_ocr
from .platform_utils import find_game_window, process_usage
from .textproc import TextTracker, classify, group_lines, normalize_key, similarity


def hold_seconds(text: str) -> float:
    """How long a translation stays after its source text left the screen: enough to read it, never forever."""
    return max(1.6, min(6.0, 0.9 + len(text) * 0.045))


def overlaps(a, b) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


class LiveTranslator(QThread):
    status = Signal(str, str)          # code, Arabic message: running|paused|offline|error|stopped|reading|translating
    result = Signal(dict)              # see _emit
    cleared = Signal()                 # the game text disappeared from the screen
    metrics = Signal(dict)

    RETRY_OFFLINE_S = 3.0
    GROW_WAIT_S = 0.45                 # text still being typed out is re-translated at most this often
    SAME_TEXT = 0.92                   # OCR jitter: lines this similar are the same line

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
        self._lock = threading.RLock()
        self._pool = cf.ThreadPoolExecutor(max_workers=3, thread_name_prefix="translate")
        self._tr: collections.OrderedDict[str, dict] = collections.OrderedDict()   # key -> translation (LRU)
        self._inflight: set[str] = set()
        self._fail_until: dict[str, float] = {}
        self._seen: dict[str, dict] = {}          # key -> {"item", "last", "first"}
        self._read_t = 0.0                        # time of the latest OCR read
        self._prev_keys: list[str] = []
        self._grow_sent: dict[str, float] = {}
        self._shown_sig: tuple = ()
        self._last_hist = None
        self._offline = False
        self.stats = {"frames": 0, "reads": 0, "translations": 0, "cap_ms": 0.0, "ocr_ms": 0.0, "tr_ms": 0.0,
                      "screen_to_text_ms": 0.0}

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
        with self._lock:
            self.tracker.reset()
            self._seen.clear()
            self._shown_sig = ()

    def set_exclusions(self, rects):
        self._exclusions = list(rects)

    # ---------- loop ----------
    def run(self):
        from .ocr import PERF_PRESETS
        prof = self.settings.profile
        perf_cfg = self.settings.data.get("performance", {})
        perf = {**PERF_PRESETS.get(perf_cfg.get("preset", "balanced"), PERF_PRESETS["balanced"]), "gpu": bool(perf_cfg.get("gpu"))}
        try:
            self._ocr = create_ocr(prof["ocr"]["engine"], _ocr_lang(prof["lang"]["src"]), prof["ocr"]["min_conf"], perf)
        except OcrError as e:
            log.error("OCR start failed: %s", e)
            self.status.emit("error", f"تعذّر تشغيل قراءة النص: {e}")
            return
        cap_cfg = prof["capture"]
        cap = Capturer(cap_cfg.get("method", "auto"))
        game, game_t = None, 0.0
        detector = ChangeDetector(cap_cfg["sensitivity"], min(cap_cfg["stable_ms"], 150), perf["max_wait_ms"])
        self.status.emit("running", f"يعمل ({self._ocr.name}) — بانتظار نص جديد")
        log.info("live start: ocr=%s method=%s preset=%s", self._ocr.name, cap_cfg.get("method", "auto"), perf_cfg.get("preset"))
        process_usage()
        last_metrics = 0.0
        stats = self.stats
        while not self._stop:
            t_loop = time.perf_counter()
            prof = self.settings.profile
            c = prof["capture"]
            detector.sensitivity, detector.stable_ms = c["sensitivity"], min(c["stable_ms"], 150)
            if self._paused:
                self.msleep(150)
                continue
            try:
                t0 = time.perf_counter()
                if cap.method != c.get("method", "auto"):
                    cap.close(); cap = Capturer(c.get("method", "auto"))
                if cap.method == "window" and time.monotonic() - game_t > 2.0:   # look the game window up every 2 s
                    game, game_t = find_game_window(prof.get("exe") or None), time.monotonic()
                img, box = cap.grab(c["monitor"], None if c["full"] else c["region"], game)
                stats["capture"] = cap.active
                stats["cap_ms"] = (time.perf_counter() - t0) * 1000
                stats["frames"] += 1
                now = time.monotonic()
                fire = detector.update(img, now)
                if self._force:
                    fire, self._force = True, False
                    self.reset_text()
                if fire:
                    self._read(img, box, prof, now)
                self._retry_failed(prof)
                self._publish()
            except Exception as e:  # never let one bad frame kill the loop
                log.exception("capture/read loop error")
                self.status.emit("error", f"خطأ أثناء الالتقاط: {e}")
                self.msleep(1000)
            if time.monotonic() - last_metrics > 1.0:
                cpu, mem = process_usage()
                self.metrics.emit({**stats, "cpu": cpu, "mem": mem, "engines": self.manager.engine_state()})
                last_metrics = time.monotonic()
            spent = (time.perf_counter() - t_loop) * 1000
            poll = min(int(c["interval_ms"]), int(perf["poll_ms"]))
            self.msleep(int(max(15, poll - spent)))
        cap.close()
        self._pool.shutdown(wait=False, cancel_futures=True)
        self.status.emit("stopped", "متوقف")

    # ---------- reading ----------
    def _ocr_read(self, img, prof):
        try:
            return self._ocr.read(img)
        except Exception as e:
            if getattr(self._ocr, "name", "") == "rapid":
                raise
            # Windows OCR failed on this machine: switch to the bundled engine and carry on
            from .ocr import RapidOcr
            self._ocr = RapidOcr(prof["ocr"]["min_conf"])
            self.status.emit("running", f"تحوّلت القراءة إلى المحرك المدمج ({e})")
            return self._ocr.read(img)

    def _read(self, img, box, prof, t_frame: float):
        t0 = time.perf_counter()
        lines = self._ocr_read(img, prof)
        self.stats["ocr_ms"] = (time.perf_counter() - t0) * 1000
        self.stats["reads"] += 1
        lines = [l for l in lines if not self._excluded(l, box)]
        blocks = group_lines(lines)
        items = []
        for b in blocks:
            x, y, w, h = b.box
            line_h = sorted(l.h for l in b.lines)[len(b.lines) // 2]
            items.append({"label": b.label, "src": b.text, "box": b.box, "line_h": line_h,
                          "abs": (box["left"] + x, box["top"] + y, w, h)})
        for it, kind in zip(items, classify(items)):
            it["kind"] = kind
        now = time.monotonic()
        keys = []
        with self._lock:
            self._read_t = now
            for it in items:
                key = self._key_for(normalize_key((it["label"] + ": " if it["label"] else "") + it["src"]))
                it["key"] = key
                keys.append(key)
                s = self._seen.get(key)
                if s:
                    s["item"], s["last"] = it, now
                else:
                    self._seen[key] = {"item": it, "first": t_frame, "last": now}
            # a new line drawn where an old one was replaces it at once (no ghost of the previous line)
            for k, s in list(self._seen.items()):
                if k not in keys and any(overlaps(s["item"]["abs"], it["abs"]) for it in items):
                    del self._seen[k]
            todo = []
            for it in items:
                k = it["key"]
                if k in self._tr or k in self._inflight or self._fail_until.get(k, 0) > now:
                    continue
                if self._growing(k) and now - self._grow_sent.get(self._root(k), 0) < self.GROW_WAIT_S:
                    continue                       # still being typed out: wait for the rest (or GROW_WAIT_S)
                if self._growing(k):
                    self._grow_sent[self._root(k)] = now
                todo.append(it)
            self._prev_keys = keys
        if not items:
            self.status.emit("running", "يعمل — لا يوجد نص على الشاشة")
        elif todo:
            self._submit(todo, prof)
        else:
            self.status.emit("running", "يعمل — النص لم يتغير")

    def _key_for(self, key: str) -> str:
        """OCR rarely reads a line twice exactly the same: reuse the key of a line already known that is nearly equal."""
        if key in self._tr or key in self._seen or not key:
            return key
        for k in list(self._seen)[-40:] + list(self._tr)[-80:]:
            if abs(len(k) - len(key)) > max(3, len(key) // 10):
                continue
            short, long_ = sorted((k, key), key=len)
            if len(long_) - len(short) > 2 and long_.startswith(short):
                continue                 # the same line with more words typed out: that is new text
            if similarity(k, key) >= self.SAME_TEXT:
                return k
        return key

    def _growing(self, key: str) -> bool:
        return any(len(key) > len(p) + 1 and key.startswith(p) for p in self._prev_keys)

    def _root(self, key: str) -> str:
        return key[:12]

    def _submit(self, items, prof):
        with self._lock:
            for it in items:
                self._inflight.add(it["key"])
        self.status.emit("translating", "يترجم…")
        snap = [dict(it) for it in items]
        f = self._pool.submit(self._translate_job, snap, prof)
        f.add_done_callback(lambda fut: self._job_done(fut, snap))

    def _translate_job(self, items, prof):
        t0 = time.perf_counter()
        out, engine, source = self._translate_items(items, prof)
        return out, engine, source, (time.perf_counter() - t0) * 1000

    def _job_done(self, fut, items):
        keys = [it["key"] for it in items]
        try:
            out, engine, source, ms = fut.result()
        except AllEnginesFailed as e:
            with self._lock:
                for k in keys:
                    self._inflight.discard(k)
                    self._fail_until[k] = time.monotonic() + self.RETRY_OFFLINE_S
            self._offline = True
            if e.network:
                self.status.emit("offline", "لا يوجد اتصال بالإنترنت — سأعيد المحاولة تلقائياً")
            else:
                log.warning("translation failed: %s", e)
                self.status.emit("error", f"تعذّرت الترجمة: {e}")
            return
        except Exception as e:  # pragma: no cover - a bug must not leave lines stuck "in flight"
            log.exception("translation job failed")
            with self._lock:
                for k in keys:
                    self._inflight.discard(k)
                    self._fail_until[k] = time.monotonic() + self.RETRY_OFFLINE_S
            self.status.emit("error", f"تعذّرت الترجمة: {e}")
            return
        self._offline = False
        prof = self.settings.profile
        with self._lock:
            for it in out:
                self._tr[it["key"]] = {"tr": it.get("tr", ""), "label_tr": it.get("label_tr", ""), "engine": engine, "source": source}
                self._tr.move_to_end(it["key"])
                self._inflight.discard(it["key"])
                self._fail_until.pop(it["key"], None)
            while len(self._tr) > 600:
                self._tr.popitem(last=False)
            first = min((self._seen[k]["first"] for k in keys if k in self._seen), default=None)
        if first is not None:
            self.stats["screen_to_text_ms"] = (time.monotonic() - first) * 1000
        self.stats["tr_ms"] = ms
        self.stats["translations"] += 1
        tr_text = "\n".join((f"{it.get('label_tr') or it['label']}: " if it["label"] else "") + it.get("tr", "") for it in out)
        src_text = "\n".join((f"{it['label']}: " if it["label"] else "") + it["src"] for it in out)
        try:
            self._last_hist = self.store.add_history(prof["name"], src_text, tr_text, engine, prof["lang"]["src"], prof["lang"]["tgt"])
        except Exception:  # history is a convenience; never lose the subtitle for it
            log.exception("history write failed")
        self._publish(engine, source)
        self.status.emit("running", "يعمل — بانتظار نص جديد")

    def _retry_failed(self, prof):
        """Lines whose translation failed (offline) are tried again while they are still on screen."""
        now = time.monotonic()
        with self._lock:
            due = [s["item"] for k, s in self._seen.items()
                   if k in self._fail_until and self._fail_until[k] <= now and k not in self._inflight and k not in self._tr
                   and now - s["last"] < 30]
            for it in due:
                self._fail_until.pop(it["key"], None)
        if due:
            self._submit(due, prof)

    # ---------- what is on screen ----------
    def visible_items(self, now: float | None = None) -> list[dict]:
        """Translated lines to show: the ones on screen now, plus lines that already left the screen but whose
        translation has not been up long enough to read (fast text). A line that was read at leisure disappears
        together with the game text."""
        now = time.monotonic() if now is None else now
        out = []
        with self._lock:
            for k, s in list(self._seen.items()):
                tr = self._tr.get(k)
                on_screen = s["last"] >= self._read_t - 1e-6
                if tr and tr["tr"] and "shown" not in s:
                    s["shown"] = now
                if not on_screen:
                    if "shown" in s:
                        keep = now - s["shown"] < hold_seconds(tr["tr"]) if tr else False
                    else:   # still being translated: wait for it, but not forever
                        keep = now - s["last"] < 8.0 and (k in self._inflight or k in self._fail_until)
                    if not keep:
                        del self._seen[k]
                        continue
                if tr and tr["tr"]:
                    it = dict(s["item"])
                    it["tr"], it["label_tr"] = tr["tr"], tr["label_tr"] or it["label"]
                    it["engine"], it["source"] = tr["engine"], tr["source"]
                    it["_on"] = on_screen
                    out.append(it)
            # once newer text is on screen and translated, lines that already left the screen give way to it
            newest = max((self._seen[it["key"]]["first"] for it in out if it.get("_on")), default=None)
            if newest is not None:
                out = [it for it in out if it.get("_on") or self._seen[it["key"]]["last"] >= newest]
        out.sort(key=lambda it: (it["abs"][1], it["abs"][0]))
        for it in out:
            it.pop("_on", None)
        return out

    def _publish(self, engine: str = "", source: str = ""):
        with self._lock:
            self._publish_locked(engine, source)

    def _publish_locked(self, engine: str, source: str):
        items = self.visible_items()
        sig = tuple((it["key"], it["tr"], tuple(round(v / 8) for v in it["abs"])) for it in items)
        if sig == self._shown_sig:
            return
        self._shown_sig = sig
        if not items:
            self.cleared.emit()
            return
        self.tracker.current = [it["key"] for it in items]
        tr_text = "\n".join((f"{it['label_tr']}: " if it["label"] else "") + it["tr"] for it in items)
        src_text = "\n".join((f"{it['label']}: " if it["label"] else "") + it["src"] for it in items)
        self.result.emit({"items": items, "engine": engine or items[-1].get("engine", ""), "source": source or items[-1].get("source", "engine"),
                          "text": tr_text, "src_text": src_text, "history_id": self._last_hist,
                          "ms": {"ocr": round(self.stats["ocr_ms"]), "tr": round(self.stats["tr_ms"]),
                                 "total": round(self.stats["screen_to_text_ms"])}})

    # ---------- translation ----------
    def _translate_items(self, items, prof):
        src, tgt, style = prof["lang"]["src"], prof["lang"]["tgt"], prof["translate"]["style"]
        ctx = tuple(self.context)
        gl = tuple((g.get("src", ""), g.get("tr", "")) for g in prof.get("glossary", []) if g.get("src") and g.get("tr"))
        engine_used, source_used = "", ""
        labels = [it["label"] for it in items if it["label"]]
        # One request for the new lines and the speaker names together (one round trip), split back by line.
        lines = [it["src"] for it in items] + labels
        res = self.manager.translate(Request("\n".join(lines), src, tgt, style, ctx, gl))
        parts = [p.strip() for p in res.text.split("\n") if p.strip()]
        if len(parts) == len(lines):
            for it, p in zip(items, parts):
                it["tr"] = p
            lab = iter(parts[len(items):])
            for it in items:
                if it["label"]:
                    it["label_tr"] = next(lab, it["label"])
            engine_used, source_used = res.engine, res.source
        else:  # the engine merged/split lines: translate line by line, in parallel
            def one(text, c=ctx):
                return self.manager.translate(Request(text, src, tgt, style, c, gl))
            futs = [self._pool_lines.submit(one, it["src"]) for it in items]
            lfuts = {id(it): self._pool_lines.submit(one, it["label"], ()) for it in items if it["label"]}
            for it, f in zip(items, futs):
                r = f.result()
                it["tr"], engine_used, source_used = r.text, r.engine, r.source
            for it in items:
                if it["label"]:
                    it["label_tr"] = lfuts[id(it)].result().text.strip() or it["label"]
        for it in items:
            self.context.append((it["label"] + ": " if it["label"] else "") + it["src"])
        return items, engine_used, source_used

    _pool_lines = cf.ThreadPoolExecutor(max_workers=6, thread_name_prefix="translate-line")

    def _excluded(self, line, box) -> bool:
        if not self._exclusions:
            return False
        cx = box["left"] + line.x + line.w / 2
        cy = box["top"] + line.y + line.h / 2
        return any(x <= cx <= x + w and y <= cy <= y + h for x, y, w, h in self._exclusions)


def _ocr_lang(src: str) -> str:
    return "en" if src in ("auto", "", None) else src
