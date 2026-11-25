"""All pages of the main window. Each page edits the ACTIVE game profile through the controller."""
from __future__ import annotations

import csv
import datetime as dt
import os
import sys

from PySide6.QtCore import QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QFont, QGuiApplication, QKeySequence
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                               QFileDialog, QFormLayout, QFrame, QGridLayout, QHBoxLayout, QHeaderView,
                               QInputDialog, QKeySequenceEdit, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QMessageBox, QPushButton, QScrollArea, QStackedWidget, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from .. import styles
from ..config import APP_NAME_AR, APP_NAME_EN, APP_VERSION, DEFAULT_HOTKEYS, ENGINE_INFO, LANGUAGES, data_dir
from ..screens import screen_label
from . import icons, theme
from .widgets import (Chips, ColorPick, FontPicker, MonitorMap, PowerButton, SubtitlePreview, TemplateGallery, ValueSlider,
                      card, hint, row, title)


class Page(QScrollArea):
    """Scrollable page with a vertical layout and a list of 'advanced only' widgets."""
    title_text = ""

    def __init__(self, ctrl):
        super().__init__()
        self.ctrl = ctrl
        self.setWidgetResizable(True)
        self.body = QWidget()
        self.v = QVBoxLayout(self.body)
        self.v.setContentsMargins(26, 8, 26, 26)
        self.v.setSpacing(16)
        self.setWidget(self.body)
        self.adv: list[QWidget] = []

    def advanced(self, w: QWidget) -> QWidget:
        self.adv.append(w)
        return w

    def set_advanced(self, on: bool):
        for w in self.adv:
            w.setVisible(on)

    def refresh(self):
        pass

    @property
    def prof(self) -> dict:
        return self.ctrl.settings.profile

    def save(self, path: str, value, apply: str = "display"):
        self.ctrl.settings.update_profile(path, value)
        if apply == "display":
            self.ctrl.apply_display()
        elif apply == "capture":
            self.ctrl.capture_changed()
        elif apply == "restart":
            self.ctrl.restart_if_running()


# ======================================================================= home
class HomePage(Page):
    title_text = "التشغيل"

    def __init__(self, ctrl):
        super().__init__(ctrl)
        top = QHBoxLayout(); top.setSpacing(16)

        hero, hl = card(gold=True)
        hrow = QHBoxLayout(); hrow.setSpacing(22)
        self.power = PowerButton(176)
        self.power.clicked.connect(ctrl.toggle)
        hrow.addWidget(self.power, 0, Qt.AlignVCenter)
        info = QVBoxLayout(); info.setSpacing(6)
        self.state_lbl = QLabel("جاهز للتشغيل"); self.state_lbl.setFont(theme.display_font(24))
        self.state_sub = hint("افتح لعبتك ثم اضغط «ابدأ الترجمة» أو Ctrl+Shift+T من داخل اللعبة.")
        self.game_chip = QLabel(); self.game_chip.setObjectName("Muted")
        info.addStretch(1); info.addWidget(self.state_lbl); info.addWidget(self.state_sub); info.addWidget(self.game_chip); info.addStretch(1)
        hrow.addLayout(info, 1)
        hl.addLayout(hrow)
        top.addWidget(hero, 3)

        side, sl = card()
        sl.addWidget(title("طريقة العرض", "vr"))
        seg = QHBoxLayout(); seg.setSpacing(8)
        self.btn_screen = QPushButton(icons.icon("monitor", theme.MIST, theme.GOLD2), "  وضع الشاشة")
        self.btn_vr = QPushButton(icons.icon("vr", theme.MIST, theme.GOLD2), "  الواقع الافتراضي")
        grp = QButtonGroup(self)
        for b in (self.btn_screen, self.btn_vr):
            b.setObjectName("Seg"); b.setCheckable(True); grp.addButton(b); seg.addWidget(b)
        self.btn_screen.clicked.connect(lambda: ctrl.set_mode("screen"))
        self.btn_vr.clicked.connect(lambda: ctrl.set_mode("vr"))
        sl.addLayout(seg)
        sl.addWidget(hint("لكل وضع إعداداته الخاصة في صفحة «المظهر». اختصار التبديل: Ctrl+Shift+V"))
        sl.addWidget(title("أوامر سريعة", "zap"))
        g = QGridLayout(); g.setSpacing(8)
        actions = [("crop", "تحديد منطقة", ctrl.select_region), ("full", "الشاشة كاملة", ctrl.use_full_screen),
                   ("eye_off", "إخفاء/إظهار الترجمة", ctrl.toggle_overlay), ("refresh", "ترجم الآن", ctrl.retranslate)]
        for i, (ic, txt, fn) in enumerate(actions):
            b = QPushButton(icons.icon(ic, theme.GOLD2), "  " + txt); b.clicked.connect(fn)
            g.addWidget(b, i // 2, i % 2)
        sl.addLayout(g)
        top.addWidget(side, 2)
        self.v.addLayout(top)

        stats = QHBoxLayout(); stats.setSpacing(12)
        self.stat = {}
        for key, ic, label in (("engine", "lang", "محرك الترجمة"), ("speed", "zap", "زمن القراءة + الترجمة"),
                               ("ping", "wifi" if "wifi" in icons.icons3d.GLYPHS else "zap", "البنق إلى خدمة الترجمة"),
                               ("usage", "cpu", "استهلاك البرنامج"), ("count", "hist", "ترجمات هذه الجلسة")):
            c, l = card()
            l.addWidget(title(label, ic))
            v = QLabel("—"); v.setObjectName("Stat"); l.addWidget(v)
            self.stat[key] = v
            stats.addWidget(c)
        self.v.addLayout(stats)

        quick, ql = card()
        qh = QHBoxLayout(); qh.addWidget(title("شكل الترجمة بضغطة", "template")); qh.addStretch(1)
        more = QPushButton("كل القوالب والطبقات والتأثيرات"); more.setObjectName("Chip")
        more.clicked.connect(lambda: ctrl.window and ctrl.window.go_name("look")); qh.addWidget(more)
        ql.addLayout(qh)
        self.quick_tpl = Chips([(k, t["name"]) for k, t in styles.TEMPLATES.items()], wrap=8)
        self.quick_tpl.changed.connect(lambda k: ctrl.apply_template(k) and ctrl.toast(f"طُبّق قالب «{styles.TEMPLATES[k]['name']}»"))
        ql.addWidget(self.quick_tpl)
        self.v.addWidget(quick)

        last, ll = card()
        hdr = QHBoxLayout(); hdr.addWidget(title("آخر ترجمة", "spark")); hdr.addStretch(1)
        self.edit_btn = QPushButton(icons.icon("edit", theme.GOLD2), "  تعديل الترجمة"); self.edit_btn.setEnabled(False)
        self.edit_btn.clicked.connect(self._edit_last)
        hdr.addWidget(self.edit_btn)
        ll.addLayout(hdr)
        self.last_tr = QLabel("ستظهر هنا آخر ترجمة مع النص الأصلي."); self.last_tr.setWordWrap(True)
        self.last_tr.setFont(theme.ui_font(15, True)); self.last_tr.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.last_src = QLabel(""); self.last_src.setObjectName("Muted"); self.last_src.setWordWrap(True)
        self.last_src.setLayoutDirection(Qt.LeftToRight); self.last_src.setAlignment(Qt.AlignLeft)
        ll.addWidget(self.last_tr); ll.addWidget(self.last_src)
        self.v.addWidget(last)
        self.v.addStretch(1)
        self._last = None
        self._count = 0
        ctrl.status.connect(self.on_status)
        ctrl.result.connect(self.on_result)
        ctrl.metrics.connect(self.on_metrics)
        ctrl.running_changed.connect(self.power.set_on)
        ctrl.mode_changed.connect(self.refresh)
        ctrl.profile_changed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        mode = self.prof["display"]["mode"]
        self.btn_screen.setChecked(mode == "screen"); self.btn_vr.setChecked(mode == "vr")
        p = self.prof
        where = "الشاشة كاملة" if p["capture"]["full"] else "منطقة محددة"
        self.game_chip.setText(f"إعدادات: {p['name']}   •   مصدر النص: الشاشة {p['capture']['monitor']} ({where})")
        self.quick_tpl.set(p["display"]["screen"].get("template", ""))

    def on_status(self, code, msg):
        names = {"running": "الترجمة تعمل", "reading": "يقرأ النص…", "translating": "يترجم…", "paused": "متوقف مؤقتاً",
                 "offline": "الترجمة تعمل — الاتصال متقطع", "warn": "الترجمة تعمل — ملاحظة", "error": "يحتاج انتباهك",
                 "stopped": "جاهز للتشغيل"}
        self.state_lbl.setText(names.get(code, msg))
        # a slow or busy translation service is not a fault of the PC: calm amber, red only when the user must act
        color = theme.ERR if code == "error" else (theme.WARN if code in ("offline", "warn") else theme.MIST)
        self.state_lbl.setStyleSheet(f"color:{color};")
        self.state_sub.setText(msg if code != "stopped" else "افتح لعبتك ثم اضغط «ابدأ الترجمة» أو Ctrl+Shift+T من داخل اللعبة.")

    def on_result(self, r):
        self._last = r
        self._count += 1
        self.last_tr.setText(r["text"])
        self.last_src.setText(r["src_text"])
        self.edit_btn.setEnabled(True)
        src = {"engine": "", "manual": " (تعديلك)"}.get(r["source"], " (من الذاكرة)")
        self.stat["engine"].setText(ENGINE_INFO.get(r["engine"], {}).get("name", r["engine"]).split(" (")[0] + src)
        self.stat["speed"].setText(f"{r['ms']['ocr']} + {r['ms']['tr']} ms")
        self.stat["count"].setText(str(self._count))

    def on_metrics(self, m):
        self.stat["usage"].setText(f"{m['cpu']:.0f}% • {m['mem']:.0f} MB")
        ping = m.get("ping") or {}
        if ping:
            eid, ms = min(ping.items(), key=lambda kv: kv[1])
            self.stat["ping"].setText(f"{ms} ms")
            self.stat["ping"].setToolTip(" • ".join(f"{ENGINE_INFO.get(k, {}).get('name', k).split(' (')[0]}: {v} ms" for k, v in ping.items()))

    def _edit_last(self):
        if not self._last:
            return
        txt, ok = QInputDialog.getMultiLineText(self, "تعديل الترجمة",
                                                "عدّل الترجمة — سيستخدم البرنامج تعديلك كلما ظهر هذا النص مرة أخرى:",
                                                self._last["text"])
        if ok and txt.strip():
            self.ctrl.edit_translation(self._last["history_id"], txt.strip(), self._last)
            self.last_tr.setText(txt.strip())


# ======================================================================= screens
class ScreensPage(Page):
    title_text = "الشاشة والمنطقة"

    def __init__(self, ctrl):
        super().__init__(ctrl)
        c, l = card()
        l.addWidget(title("مصدر النص — الشاشة التي تعمل عليها اللعبة", "monitor"))
        l.addWidget(hint("اضغط على الشاشة المطلوبة. تظهر هنا كل الشاشات والتلفزيونات المتصلة بالكمبيوتر بدقتها الحقيقية."))
        self.map = MonitorMap(); self.map.picked.connect(self._pick_monitor)
        l.addWidget(self.map)
        seg = QHBoxLayout()
        self.b_full = QPushButton(icons.icon("full", theme.MIST, theme.GOLD2), "  الشاشة كاملة")
        self.b_region = QPushButton(icons.icon("crop", theme.MIST, theme.GOLD2), "  منطقة محددة")
        grp = QButtonGroup(self)
        for b in (self.b_full, self.b_region):
            b.setObjectName("Seg"); b.setCheckable(True); grp.addButton(b); seg.addWidget(b)
        self.b_full.clicked.connect(ctrl.use_full_screen)
        self.b_region.clicked.connect(ctrl.select_region)
        l.addLayout(seg)
        self.region_lbl = hint("")
        l.addWidget(self.region_lbl)
        l.addWidget(hint("نصيحة: تحديد منطقة الحوار أو الترجمة فقط أسرع وأدق، ويقلل استهلاك الجهاز."))
        self.v.addWidget(c)

        c2, l2 = card()
        l2.addWidget(title("مكان عرض الترجمة — شاشة أو تلفزيون", "tv"))
        self.out_screen = QComboBox(); self.out_screen.currentIndexChanged.connect(self._pick_out)
        l2.addWidget(row("اعرض الترجمة على", self.out_screen))
        l2.addWidget(hint("يدعم أي شاشة أو تلفزيون (LG، Samsung وغيرها) متصل بالكمبيوتر كشاشة عرض عبر HDMI أو DisplayPort. "
                          "لا يمكن عرض الترجمة فوق تطبيقات التلفزيون نفسه بدون كمبيوتر."))
        self.v.addWidget(c2)

        cm, lm = card()
        lm.addWidget(title("طريقة التقاط اللعبة", "scan"))
        lm.addWidget(hint("البرنامج لا يسجّل ولا يحفظ أي صورة أو فيديو: يقرأ النص من الصورة في الذاكرة ثم يتركها."))
        from ..capture import METHODS
        self.method = Chips([(k, t) for k, t, _ in METHODS], wrap=2)
        self.method.changed.connect(lambda k: self.save("capture.method", k, None))
        lm.addWidget(self.method)
        self.method_hint = hint(""); lm.addWidget(self.method_hint)
        self.method_now = hint(""); lm.addWidget(self.method_now)
        self.v.addWidget(cm)

        cp, lp = card()
        lp.addWidget(title("الأداء", "cpu"))
        from ..ocr import gpu_available
        self.perf = Chips([("light", "جهاز ضعيف"), ("balanced", "متوازن"), ("high", "جهاز قوي")])
        self.perf.changed.connect(self._perf)
        lp.addWidget(self.perf)
        lp.addWidget(hint("الجهاز الضعيف: فحص أبطأ وقراءة أخف. الجهاز القوي: استجابة أسرع ودقة أعلى."))
        self.gpu = QCheckBox(); self.gpu.toggled.connect(self._gpu)
        self.gpu.setEnabled(gpu_available())
        lp.addWidget(row("قراءة النص على كرت الشاشة (GPU)", self.gpu,
                         "يخفّف الضغط على المعالج. يعمل مع أي كرت يدعم DirectX 12" if gpu_available()
                         else "غير متاح على هذا الجهاز"))
        self.perf_note = hint(""); lp.addWidget(self.perf_note)
        self.v.addWidget(cp)
        ctrl.metrics.connect(self._metrics)

        c3, l3 = card()
        l3.addWidget(title("سرعة الالتقاط والحساسية", "zap"))
        self.s_int = ValueSlider(100, 1500, 50, " ms", 300)
        self.s_int.valueChanged.connect(lambda v: self.save("capture.interval_ms", int(v), None))
        self.s_stable = ValueSlider(0, 1500, 50, " ms", 250)
        self.s_stable.valueChanged.connect(lambda v: self.save("capture.stable_ms", int(v), None))
        self.s_sens = ValueSlider(1, 20, 0.5, "", 3, 1)
        self.s_sens.valueChanged.connect(lambda v: self.save("capture.sensitivity", float(v), None))
        l3.addWidget(row("فحص الشاشة كل", self.s_int, "أقل = أسرع استجابة وأعلى استهلاكاً"))
        l3.addWidget(row("انتظار ثبات النص", self.s_stable, "يمنع ترجمة النص وهو يُكتب حرفاً حرفاً"))
        l3.addWidget(row("حساسية التغيير", self.s_sens, "أعلى = يتجاهل الحركة الخفيفة في الخلفية"))
        self.v.addWidget(self.advanced(c3))
        self.v.addStretch(1)
        ctrl.profile_changed.connect(self.refresh)
        ctrl.capture_updated.connect(self.refresh)
        self.refresh()

    def refresh(self):
        c = self.prof["capture"]
        try:
            mons = self.ctrl.monitors()
        except Exception:
            mons = []
        self.map.set_data(mons, c["monitor"], None if c["full"] else c["region"])
        self.b_full.setChecked(c["full"]); self.b_region.setChecked(not c["full"])
        self.region_lbl.setText("يقرأ الشاشة كاملة." if c["full"] or not c["region"] else
                                f"المنطقة المحددة: {c['region'][2]}×{c['region'][3]} بكسل عند ({c['region'][0]}، {c['region'][1]}).")
        self.out_screen.blockSignals(True); self.out_screen.clear()
        for i, s in enumerate(QGuiApplication.screens(), 1):
            self.out_screen.addItem(f"{i}. {screen_label(s)}", i)
        idx = max(0, self.out_screen.findData(self.prof["display"]["screen"]["monitor"]))
        self.out_screen.setCurrentIndex(idx); self.out_screen.blockSignals(False)
        self.s_int.setValue(c["interval_ms"]); self.s_stable.setValue(c["stable_ms"]); self.s_sens.setValue(c["sensitivity"])
        from ..capture import METHODS
        m = c.get("method", "auto"); self.method.set(m)
        self.method_hint.setText(next((d for k, _, d in METHODS if k == m), ""))
        perf = self.ctrl.settings.data.get("performance", {})
        self.perf.set(perf.get("preset", "balanced"))
        self.gpu.blockSignals(True); self.gpu.setChecked(bool(perf.get("gpu"))); self.gpu.blockSignals(False)

    NAMES_CAP = {"dxgi": "DXGI", "window": "نافذة اللعبة", "gdi": "طريقة النظام القديمة"}

    def _metrics(self, m):
        cap = m.get("capture")
        if cap:
            self.method_now.setText(f"يعمل الآن عبر: {self.NAMES_CAP.get(cap, cap)}")

    def _perf(self, k):
        from ..ocr import PERF_PRESETS
        p = PERF_PRESETS[k]
        self.ctrl.settings.set("performance", {**self.ctrl.settings.data.get("performance", {}), "preset": k})
        self.save("capture.interval_ms", p["interval_ms"], None); self.save("capture.stable_ms", p["stable_ms"], None)
        self.perf_note.setText("طُبّق. يبدأ أثره الكامل عند تشغيل الترجمة القادم.")
        self.refresh()

    def _gpu(self, on):
        self.ctrl.settings.set("performance", {**self.ctrl.settings.data.get("performance", {}), "gpu": bool(on)})
        self.perf_note.setText("يبدأ عند تشغيل الترجمة القادم.")

    def _pick_monitor(self, i):
        self.save("capture.monitor", i, "capture")
        if self.prof["display"]["screen"]["monitor"] != i and len(QGuiApplication.screens()) > 1:
            pass

    def _pick_out(self, _):
        self.save("display.screen.monitor", self.out_screen.currentData())
        self.save("display.screen.custom_pos", None)


# ======================================================================= look
class LookPage(Page):
    title_text = "المظهر والقوالب"

    def __init__(self, ctrl):
        super().__init__(ctrl)
        seg = QHBoxLayout()
        self.t_screen = QPushButton(icons.tile_icon("monitor", "blue", 26), "  وضع الشاشة والتلفزيون")
        self.t_vr = QPushButton(icons.tile_icon("vr", "violet", 26), "  وضع الواقع الافتراضي")
        grp = QButtonGroup(self)
        for b in (self.t_screen, self.t_vr):
            b.setObjectName("Seg"); b.setCheckable(True); b.setIconSize(QSize(26, 26)); grp.addButton(b); seg.addWidget(b)
        self.v.addLayout(seg)
        self.stack = QStackedWidget()
        self.v.addWidget(self.stack)
        self.t_screen.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.t_vr.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        self.t_screen.setChecked(True)

        # ================= screen
        sw = QWidget(); sv = QVBoxLayout(sw); sv.setContentsMargins(0, 0, 0, 0); sv.setSpacing(14)
        self.prev = SubtitlePreview(260); sv.addWidget(self.prev)
        pr = QHBoxLayout()
        b_play = QPushButton(icons.icon("play", theme.GOLD2), "  شغّل التأثير في المعاينة"); b_play.clicked.connect(self.prev.play)
        b_live = QPushButton(icons.icon("monitor", theme.GOLD2), "  اعرضه فوق اللعبة الآن"); b_live.clicked.connect(ctrl.preview_effect)
        b_live.setToolTip("يعرض ترجمة تجريبية بهذا الشكل على شاشة اللعبة لبضع ثوانٍ")
        pr.addWidget(b_play); pr.addWidget(b_live); pr.addStretch(1)
        sv.addLayout(pr)

        # ---- where the translation goes
        cp, lp = card(gold=True); lp.addWidget(title("مكان الترجمة", "move"))
        from ..overlay import PLACES
        self.place = Chips([(k, n) for k, n, _ in PLACES]); self.place.changed.connect(self._place)
        self.place_hint = hint("")
        lp.addWidget(self.place); lp.addWidget(self.place_hint)
        self.blend = QCheckBox(); self.blend.toggled.connect(lambda b: self._s("blend", b))
        lp.addWidget(row("دمج الترجمة مع واجهة اللعبة", self.blend,
                         "مع «فوق النص الأصلي»: تأخذ الترجمة لون خلفية اللعبة ولون نصها وحجمه، فيختفي الإنجليزي وتبدو اللعبة معرّبة رسمياً"))
        self.steady = QCheckBox(); self.steady.toggled.connect(lambda b: self._s("steady", b))
        lp.addWidget(row("ثبات مكان الترجمة وحجم صندوقها", self.steady,
                         "يبقى صندوق الترجمة بحجم واحد في مكانه، ولا تهتز الترجمة فوق النص مع كل قراءة"))
        self.recordable = QCheckBox(); self.recordable.toggled.connect(self._recordable)
        lp.addWidget(row("تظهر الترجمة في لقطات الشاشة والتسجيل", self.recordable,
                         "تظهر في Xbox Game Bar وأداة القص وOBS (التقاط الشاشة) وDiscord. يقرأ البرنامج حينها نافذة اللعبة نفسها مثل OBS"))
        sv.addWidget(cp)

        # ---- templates
        ct, lt = card(gold=True); lt.addWidget(title("القوالب الجاهزة", "template"))
        lt.addWidget(hint("اختر قالباً بضغطة واحدة: يضبط الخط والألوان والخلفية والتأثيرات معاً. بعدها عدّل ما تريد، واحفظه قالباً خاصاً بك."))
        self.gallery = TemplateGallery(3)
        self.gallery.applied.connect(self._apply_tpl); self.gallery.deleted.connect(self._del_tpl)
        lt.addWidget(self.gallery)
        tb = QHBoxLayout()
        b_save = QPushButton(icons.icon("plus", theme.GOLD2), "  احفظ الشكل الحالي كقالب"); b_save.clicked.connect(self._save_tpl)
        b_imp = QPushButton(icons.icon("download", theme.GOLD2), "  استيراد قوالب"); b_imp.clicked.connect(self._import_tpl)
        b_exp = QPushButton("تصدير قوالبي"); b_exp.clicked.connect(self._export_tpl)
        tb.addWidget(b_save); tb.addWidget(b_imp); tb.addWidget(b_exp); tb.addStretch(1)
        lt.addLayout(tb)
        sv.addWidget(ct)

        # ---- font
        cf, lf = card(); lf.addWidget(title("الخط", "type"))
        lf.addWidget(hint("خطوط عربية مدمجة في البرنامج، فتظهر الحروف سليمة على أي جهاز."))
        self.fontpick = FontPicker(3); self.fontpick.changed.connect(lambda f: self._s("font_family", f))
        lf.addWidget(self.fontpick)
        self.size = ValueSlider(14, 80, 1, " px", 26); self.size.valueChanged.connect(lambda v: self._s("font_size", int(v)))
        self.bold = QCheckBox(); self.bold.toggled.connect(lambda b: self._s("bold", b))
        lf.addWidget(row("حجم الخط", self.size, "للتلفزيون البعيد اختر 36 فأكثر. ومن داخل اللعبة: Ctrl+Shift+U للتكبير وCtrl+Shift+J للتصغير")); lf.addWidget(row("خط عريض", self.bold))
        sv.addWidget(cf)

        # ---- colours & box
        cc, lc = card(); lc.addWidget(title("الألوان والخلفية", "palette"))
        self.color = ColorPick(["#FFFFFF", "#FFE14D", "#F6DCA0", "#9FE8FF", "#B7FFB0", "#121212"], "#FFFFFF")
        self.color.changed.connect(lambda c: self._s("color", c))
        self.accent = ColorPick(["#E7B964", "#5CE1E6", "#FF4FD8", "#7CF29A", "#FF8466", "#C9D0EA"], "#E7B964")
        self.accent.changed.connect(lambda c: self._s("accent", c))
        self.bg = ColorPick(["#0A0E1F", "#000000", "#1B1209", "#03121A", "#FFFFFF"], "#0A0E1F")
        self.bg.changed.connect(lambda c: self._s("bg", c))
        self.opa = ValueSlider(0, 100, 5, "%", 80); self.opa.valueChanged.connect(lambda v: self._s("bg_opacity", int(v)))
        self.box = Chips(styles.BOXES); self.box.changed.connect(lambda k: self._s("box", k))
        self.tfx = Chips(styles.TEXT_FX); self.tfx.changed.connect(lambda k: self._s("text_fx", k))
        lc.addWidget(row("لون الكلام", self.color)); lc.addWidget(row("لون الاسم والحافة", self.accent, "اسم المتحدث وعنوان المهمة"))
        lc.addWidget(row("لون الخلفية", self.bg)); lc.addWidget(row("شفافية الخلفية", self.opa))
        lc.addWidget(QLabel("شكل الخلفية")); lc.addWidget(self.box)
        lc.addWidget(QLabel("تأثير الحروف")); lc.addWidget(self.tfx)
        self.radius = ValueSlider(0, 40, 1, " px", 16); self.radius.valueChanged.connect(lambda v: self._s("radius", int(v)))
        self.align = Chips([("center", "في الوسط"), ("start", "من جهة البداية")]); self.align.changed.connect(lambda k: self._s("align", k))
        lc.addWidget(self.advanced(row("استدارة الزوايا", self.radius)))
        lc.addWidget(self.advanced(row("محاذاة الكلام", self.align)))
        sv.addWidget(cc)

        # ---- effects
        ce, le = card(); le.addWidget(title("تأثيرات الظهور والاختفاء", "wand"))
        self.fx_in = Chips(styles.FX_IN, wrap=3); self.fx_in.changed.connect(lambda k: self._s("fx_in", k, play=True))
        self.fx_out = Chips(styles.FX_OUT); self.fx_out.changed.connect(lambda k: self._s("fx_out", k))
        self.fx_ms = ValueSlider(0, 1200, 20, " ms", 280); self.fx_ms.valueChanged.connect(lambda v: self._s("fx_ms", int(v)))
        le.addWidget(QLabel("عند ظهور ترجمة جديدة")); le.addWidget(self.fx_in)
        le.addWidget(QLabel("عند اختفاء النص من اللعبة")); le.addWidget(self.fx_out)
        le.addWidget(row("سرعة التأثير", self.fx_ms, "الأقل أسرع؛ 0 يلغي التأثير"))
        sv.addWidget(ce)

        # ---- layers
        cl, ll = card(); ll.addWidget(title("الطبقات: الحوار والمهمة والخيارات", "layers"))
        ll.addWidget(hint("يفرز البرنامج نصوص اللعبة تلقائياً: كلام الشخصيات في طبقة، والمهمة الحالية في طبقة، وخيارات الرد في طبقة. "
                          "لكل طبقة مكانها وحجمها، ويمكن إيقافها فيذهب نصها إلى صندوق الحوار."))
        self.layers_on = QCheckBox(); self.layers_on.toggled.connect(lambda b: self._s("layers_on", b))
        ll.addWidget(row("فصل النصوص في طبقات", self.layers_on, "عند الإيقاف تظهر كل الترجمة في صندوق واحد"))
        # dialogue = the main subtitle position
        self.anchor = QComboBox()
        for k, t in styles.ANCHORS:
            self.anchor.addItem(t, k)
        self.anchor.currentIndexChanged.connect(lambda _: (self._s("anchor", self.anchor.currentData()), self._s("custom_pos", None)))
        self.offset = ValueSlider(0, 600, 10, " px", 80); self.offset.valueChanged.connect(lambda v: self._s("offset", int(v)))
        self.width = ValueSlider(30, 100, 5, "%", 70); self.width.valueChanged.connect(lambda v: self._s("width_pct", int(v)))
        dl = self._layer_head("dialogue", "chat", "gold")
        b_move = QPushButton(icons.icon("move", theme.GOLD2), "  حرّك بالماوس"); b_move.clicked.connect(lambda: ctrl.edit_overlay_position("dialogue"))
        dl.addWidget(b_move)
        ll.addLayout(dl)
        ll.addWidget(row("المكان", self.anchor)); ll.addWidget(row("البعد عن الحافة", self.offset)); ll.addWidget(row("العرض", self.width))
        self.layer_w: dict[str, dict] = {}
        for k, ic, hue in (("quest", "flag", "coral"), ("choices", "list", "cyan"), ("other", "info", "slate")):
            box = QFrame(); box.setObjectName("LayerBox"); bl = QVBoxLayout(box); bl.setContentsMargins(12, 10, 12, 10); bl.setSpacing(6)
            head = self._layer_head(k, ic, hue)
            on = QCheckBox(); on.toggled.connect(lambda b, k=k: self._l(k, "on", b)); head.addWidget(on)
            mv = QPushButton(icons.icon("move", theme.GOLD2), "  حرّك"); mv.clicked.connect(lambda _=False, k=k: ctrl.edit_overlay_position(k))
            head.addWidget(mv)
            bl.addLayout(head)
            anc = QComboBox()
            for a, t in styles.ANCHORS:
                anc.addItem(t, a)
            anc.currentIndexChanged.connect(lambda _, k=k, anc=anc: (self._l(k, "anchor", anc.currentData()), self._l(k, "custom_pos", None)))
            sc = ValueSlider(50, 150, 5, "%", 80); sc.valueChanged.connect(lambda v, k=k: self._l(k, "scale", round(v / 100, 2)))
            wd = ValueSlider(15, 100, 5, "%", 30); wd.valueChanged.connect(lambda v, k=k: self._l(k, "width_pct", int(v)))
            off = ValueSlider(0, 400, 10, " px", 40); off.valueChanged.connect(lambda v, k=k: self._l(k, "offset", int(v)))
            bl.addWidget(row("المكان", anc)); bl.addWidget(row("حجم الخط نسبةً للحوار", sc))
            bl.addWidget(self.advanced(row("العرض", wd))); bl.addWidget(self.advanced(row("البعد عن الحافة", off)))
            ll.addWidget(box)
            self.layer_w[k] = {"box": box, "on": on, "anchor": anc, "scale": sc, "width_pct": wd, "offset": off}
        self.orig = QCheckBox(); self.orig.toggled.connect(lambda b: self._s("show_original", b))
        self.lines = ValueSlider(1, 8, 1, "", 4); self.lines.valueChanged.connect(lambda v: self._s("max_lines", int(v)))
        ll.addWidget(row("إظهار النص الأصلي تحت الترجمة", self.orig))
        ll.addWidget(self.advanced(row("أقصى عدد فقرات في الطبقة", self.lines)))
        sv.addWidget(cl)
        self.stack.addWidget(sw)

        # ================= vr
        vw = QWidget(); vv = QVBoxLayout(vw); vv.setContentsMargins(0, 0, 0, 0); vv.setSpacing(14)
        self.vprev = SubtitlePreview(230); vv.addWidget(self.vprev)
        c3, l3 = card(); l3.addWidget(title("لوحة الترجمة داخل النظارة", "vr"))
        l3.addWidget(hint("يعمل مع أي نظارة تعمل عبر SteamVR: Valve Index وHTC Vive وMeta Quest (عبر Link أو Air Link أو Virtual Desktop) وPico وWindows MR. "
                          "تتبع اللوحة رأسك على المسافة والارتفاع المحددين. القالب المختار يحدد خط اللوحة وألوانها."))
        from ..vr import PLACEMENTS
        self.vplace = Chips([(k, t) for k, t, _ in PLACEMENTS]); self.vplace.changed.connect(self._vplace)
        l3.addWidget(QLabel("مكان اللوحة")); l3.addWidget(self.vplace)
        self.vplace_hint = hint(""); l3.addWidget(self.vplace_hint)
        self.vside = ValueSlider(-1.5, 1.5, 0.05, " م", 0.0, 2); self.vside.valueChanged.connect(lambda v: self._v("side_m", v))
        self.vdist = ValueSlider(0.5, 4.0, 0.1, " م", 1.4, 1); self.vdist.valueChanged.connect(lambda v: self._v("distance_m", v))
        self.vwid = ValueSlider(0.4, 3.0, 0.1, " م", 1.1, 1); self.vwid.valueChanged.connect(lambda v: self._v("width_m", v))
        self.vh = ValueSlider(-1.0, 1.0, 0.05, " م", -0.35, 2); self.vh.valueChanged.connect(lambda v: self._v("height_m", v))
        self.vsize = ValueSlider(20, 90, 2, " px", 44); self.vsize.valueChanged.connect(lambda v: self._v("font_size", int(v)))
        self.vfont = FontPicker(3); self.vfont.changed.connect(lambda f: self._v("font_family", f))
        self.vcolor = ColorPick(["#FFFFFF", "#FFE14D", "#F6DCA0", "#9FE8FF"], "#FFFFFF"); self.vcolor.changed.connect(lambda c: self._v("color", c))
        self.vopa = ValueSlider(0, 100, 5, "%", 80); self.vopa.valueChanged.connect(lambda v: self._v("bg_opacity", int(v)))
        self.vorig = QCheckBox(); self.vorig.toggled.connect(lambda b: self._v("show_original", b))
        for lab, w in (("المسافة أمام العين", self.vdist), ("عرض اللوحة", self.vwid), ("الارتفاع (سالب = أسفل النظر)", self.vh),
                       ("يمين / يسار", self.vside), ("حجم الخط", self.vsize)):
            l3.addWidget(row(lab, w))
        l3.addWidget(QLabel("خط اللوحة")); l3.addWidget(self.vfont)
        for lab, w in (("لون الكلام", self.vcolor), ("شفافية الخلفية", self.vopa), ("إظهار النص الأصلي", self.vorig)):
            l3.addWidget(row(lab, w))
        b_vr = QPushButton(icons.icon("vr", theme.GOLD2), "  اختبر اللوحة في النظارة الآن"); b_vr.clicked.connect(ctrl.test_vr)
        l3.addWidget(b_vr)
        l3.addWidget(hint("يشغّل البرنامج SteamVR بنفسه إن لم يكن يعمل، ويعيد الاتصال تلقائياً إذا أُغلق. "
                          "لنظارات Meta Quest عبر Link أو Air Link: شغّل Meta Quest Link، ثم اجعل SteamVR مشغّل OpenXR "
                          "(SteamVR ← الإعدادات ← OpenXR) حتى تظهر الترجمة داخل ألعاب Meta أيضاً. "
                          "واختر في «الشاشات والالتقاط» نافذة اللعبة نفسها لتُقرأ نصوصها."))
        vv.addWidget(c3)
        c4, l4 = card(); l4.addWidget(title("التحكم وأنت داخل النظارة", "keyboard", "violet"))
        l4.addWidget(hint("تعمل هذه الاختصارات في وضع الواقع الافتراضي بدون نزع النظارة، وتحفظ التغيير لهذه اللعبة. "
                          "ويمكنك ربطها بأزرار الذراع من إعدادات SteamVR ← Controller Bindings ← Keyboard. تغييرها من صفحة «الاختصارات»."))
        self.vkeys = QLabel(); self.vkeys.setTextFormat(Qt.RichText); self.vkeys.setWordWrap(True)
        l4.addWidget(self.vkeys)
        vv.addWidget(c4)
        self.stack.addWidget(vw)
        self.v.addStretch(1)
        ctrl.profile_changed.connect(self.refresh)
        self.refresh()

    def _layer_head(self, k: str, ic: str, hue: str) -> QHBoxLayout:
        h = QHBoxLayout(); h.setSpacing(10)
        t = QLabel(); t.setPixmap(icons.tile(ic, hue, 30)); h.addWidget(t)
        _, name, desc = next(x for x in styles.LAYERS if x[0] == k)
        lab = QLabel(f"<b>طبقة {name}</b><br><span style='color:{theme.MUTED}'>{desc}</span>")
        h.addWidget(lab, 1)
        return h

    # ---------- saving ----------
    def _place(self, k):
        from ..overlay import PLACES
        self.place_hint.setText({a: c for a, _, c in PLACES}.get(k, ""))
        self._s("place", k)

    def _recordable(self, on: bool):
        self._s("recordable", on)
        self.ctrl.hud.recordable = on
        self.ctrl.restart_if_running()

    def _s(self, key, val, play: bool = False):
        self.ctrl.settings.update_profile(f"display.screen.{key}", val)
        if key in styles.LOOK_KEYS and self.prof["display"]["screen"].get("template") != "custom":
            self.ctrl.settings.update_profile("display.screen.template", "custom")
            self.gallery.set_templates(self.ctrl.templates(), "custom")
        self.ctrl.apply_display()
        self.prev.set_style(self.prof["display"]["screen"], play=play)

    def _l(self, layer, key, val):
        self.ctrl.settings.update_profile(f"display.screen.layers.{layer}.{key}", val)
        self.ctrl.apply_display()
        self.prev.set_style(self.prof["display"]["screen"])
        if key == "on":
            self._layer_enable()

    def _vplace(self, k):
        self._v("placement", k)
        self.ctrl.vr.recenter()
        self.ctrl.apply_display()
        self.refresh()

    def _v(self, key, val):
        self.save(f"display.vr.{key}", val)
        self.vprev.set_style(self.prof["display"]["vr"], vr=True)

    # ---------- templates ----------
    def _apply_tpl(self, tid):
        if self.ctrl.apply_template(tid):
            self.ctrl.toast(f"طُبّق قالب «{self.ctrl.templates()[tid]['name']}»")
            self.prev.play()

    def _save_tpl(self):
        name, ok = QInputDialog.getText(self, "حفظ قالب", "اسم القالب:")
        if ok and name.strip():
            self.ctrl.save_template(name)
            self.ctrl.toast(f"حُفظ القالب «{name.strip()}»")

    def _del_tpl(self, tid):
        t = self.ctrl.templates().get(tid)
        if t and QMessageBox.question(self, "حذف قالب", f"حذف القالب «{t['name']}»؟") == QMessageBox.Yes:
            self.ctrl.delete_template(tid)

    def _import_tpl(self):
        path, _ = QFileDialog.getOpenFileName(self, "استيراد قوالب", "", "قوالب عرب لعبتك (*.json)")
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                n = self.ctrl.import_templates(f.read())
        except (OSError, ValueError) as e:
            self.ctrl.toast(f"تعذّر قراءة الملف: {e}", err=True); return
        self.ctrl.toast(f"استُورد {n} قالب" if n else "لم يُعثر على قوالب صالحة في الملف", err=not n)

    def _export_tpl(self):
        if not self.ctrl.settings.get("templates"):
            self.ctrl.toast("لا توجد قوالب خاصة بعد — احفظ شكلاً أولاً", err=True); return
        path, _ = QFileDialog.getSaveFileName(self, "تصدير قوالبي", "arabize-templates.json", "JSON (*.json)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.ctrl.export_templates())
            self.ctrl.toast("صُدّرت القوالب — شاركها مع أصدقائك")

    # ---------- refresh ----------
    def _layer_enable(self):
        s = self.prof["display"]["screen"]
        for k, w in self.layer_w.items():
            on = s.get("layers_on", True) and s.get("layers", {}).get(k, {}).get("on", True)
            for key in ("anchor", "scale", "width_pct", "offset"):
                w[key].setEnabled(bool(on))
            w["on"].setEnabled(bool(s.get("layers_on", True)))

    def refresh(self):
        s, v = self.prof["display"]["screen"], self.prof["display"]["vr"]
        widgets = [self.anchor, self.bold, self.orig, self.vorig, self.layers_on, self.blend, self.steady, self.recordable] + [w[k] for w in self.layer_w.values() for k in ("on", "anchor")]
        for w in widgets:
            w.blockSignals(True)
        self.gallery.set_templates(self.ctrl.templates(), s.get("template", "custom"))
        self.fontpick.set(s["font_family"]); self.vfont.set(v.get("font_family"))
        self.size.setValue(s["font_size"]); self.bold.setChecked(s["bold"]); self.color.set(s["color"]); self.bg.set(s["bg"])
        self.accent.set(s.get("accent", "#E7B964"))
        self.opa.setValue(s["bg_opacity"]); self.box.set(s.get("box", "card")); self.tfx.set(s.get("text_fx", "shadow"))
        self.radius.setValue(s.get("radius", 16)); self.align.set(s.get("align", "center"))
        from ..overlay import PLACES
        self.place.set(s.get("place", "cover")); self.place_hint.setText({a: c for a, _, c in PLACES}.get(s.get("place", "cover"), ""))
        self.blend.setChecked(s.get("blend", True)); self.steady.setChecked(s.get("steady", True))
        self.recordable.setChecked(s.get("recordable", True))
        self.fx_in.set(s.get("fx_in", "fade")); self.fx_out.set(s.get("fx_out", "fade")); self.fx_ms.setValue(s.get("fx_ms", 260))
        self.anchor.setCurrentIndex(max(0, self.anchor.findData(s["anchor"])))
        self.offset.setValue(s["offset"]); self.width.setValue(s["width_pct"]); self.orig.setChecked(s["show_original"])
        self.lines.setValue(s["max_lines"]); self.layers_on.setChecked(s.get("layers_on", True))
        for k, w in self.layer_w.items():
            cfg = {**styles.DEFAULT_LAYERS[k], **s.get("layers", {}).get(k, {})}
            w["on"].setChecked(cfg["on"]); w["anchor"].setCurrentIndex(max(0, w["anchor"].findData(cfg["anchor"])))
            w["scale"].setValue(cfg["scale"] * 100); w["width_pct"].setValue(cfg["width_pct"]); w["offset"].setValue(cfg["offset"])
        self.vdist.setValue(v["distance_m"]); self.vwid.setValue(v["width_m"]); self.vh.setValue(v["height_m"])
        self.vside.setValue(v.get("side_m", 0.0)); self.vplace.set(v.get("placement", "head"))
        from ..vr import PLACEMENTS
        self.vplace_hint.setText(next((d for k, _, d in PLACEMENTS if k == v.get("placement", "head")), ""))
        hk = self.ctrl.settings.data["hotkeys"]
        rows = [(HotkeysPage.NAMES[k], hk.get(k, "")) for k in HotkeysPage.NAMES if k.startswith("vr_")] + [(HotkeysPage.NAMES["hide"], hk.get("hide", ""))]
        self.vkeys.setText("<table cellspacing=6>" + "".join(f"<tr><td>{n}</td><td dir=ltr><b>{s_}</b></td></tr>" for n, s_ in rows) + "</table>")
        self.vsize.setValue(v["font_size"]); self.vcolor.set(v["color"]); self.vopa.setValue(v["bg_opacity"]); self.vorig.setChecked(v["show_original"])
        for w in widgets:
            w.blockSignals(False)
        self._layer_enable()
        self.prev.set_style(s); self.vprev.set_style(v, vr=True)
        if self.prof["display"]["mode"] == "vr":
            self.t_vr.setChecked(True); self.stack.setCurrentIndex(1)


# ======================================================================= engines
class EnginesPage(Page):
    title_text = "المحركات واللغة"

    def __init__(self, ctrl):
        super().__init__(ctrl)
        s = ctrl.settings
        c, l = card(); l.addWidget(title("اللغة وأسلوب الترجمة", "lang"))
        self.src = QComboBox(); self.tgt = QComboBox()
        for code, name in LANGUAGES:
            self.src.addItem(name, code)
            if code != "auto":
                self.tgt.addItem(name, code)
        self.src.currentIndexChanged.connect(lambda _: self.save("lang.src", self.src.currentData(), "restart"))
        self.tgt.currentIndexChanged.connect(lambda _: self.save("lang.tgt", self.tgt.currentData(), "restart"))
        self.style = QComboBox()
        for k, t in (("gaming", "فصحى الألعاب (طبيعية ومختصرة)"), ("formal", "فصحى رسمية"), ("saudi", "عامية سعودية — محرك Claude"),
                     ("close", "قريبة من الأصل")):
            self.style.addItem(t, k)
        self.style.currentIndexChanged.connect(lambda _: self.save("translate.style", self.style.currentData(), None))
        l.addWidget(row("لغة اللعبة", self.src, "«اكتشاف تلقائي» يعرف لغة النص بنفسه"))
        l.addWidget(row("ترجم إلى", self.tgt))
        l.addWidget(row("أسلوب الترجمة", self.style, "الأساليب تؤثر بالكامل مع محرك Claude"))
        self.ocr = QComboBox()
        for k, t in (("auto", "تلقائي (الأخف المتاح)"), ("windows", "Windows OCR — الأخف، يستخدم لغات ويندوز"), ("rapid", "RapidOCR — مدمج، قوي في الإنجليزية")):
            self.ocr.addItem(t, k)
        self.ocr.currentIndexChanged.connect(lambda _: self.save("ocr.engine", self.ocr.currentData(), "restart"))
        l.addWidget(self.advanced(row("محرك قراءة النص (OCR)", self.ocr)))
        self.v.addWidget(c)

        c2, l2 = card(); l2.addWidget(title("محركات الترجمة — بالترتيب", "spark"))
        l2.addWidget(hint("يجرّب البرنامج المحرك الأول، وإن تعطل أو انقطع ينتقل تلقائياً للذي بعده. فعّل المحركات التي تريدها ورتّبها بالأسهم."))
        hl = QHBoxLayout()
        self.list = QListWidget(); self.list.setMinimumHeight(170)
        self.list.itemChanged.connect(self._save_engines)
        hl.addWidget(self.list, 1)
        bv = QVBoxLayout()
        up = QPushButton(icons.icon("up", theme.GOLD2), ""); up.clicked.connect(lambda: self._move(-1))
        dn = QPushButton(icons.icon("down", theme.GOLD2), ""); dn.clicked.connect(lambda: self._move(1))
        bv.addWidget(up); bv.addWidget(dn); bv.addStretch(1); hl.addLayout(bv)
        l2.addLayout(hl)
        self.v.addWidget(c2)

        c3, l3 = card(); l3.addWidget(title("مفاتيح المحركات الاحترافية", "keyboard"))
        e = s.data["engines"]
        self.ckey = QLineEdit(e["claude_key"]); self.ckey.setEchoMode(QLineEdit.Password); self.ckey.setPlaceholderText("sk-ant-…")
        self.ckey.setLayoutDirection(Qt.LeftToRight); self.ckey.editingFinished.connect(lambda: self._eng("claude_key", self.ckey.text().strip()))
        self.cmodel = QLineEdit(e["claude_model"]); self.cmodel.setLayoutDirection(Qt.LeftToRight)
        self.cmodel.editingFinished.connect(lambda: self._eng("claude_model", self.cmodel.text().strip() or "claude-haiku-5-5"))
        self.dkey = QLineEdit(e["deepl_key"]); self.dkey.setEchoMode(QLineEdit.Password); self.dkey.setLayoutDirection(Qt.LeftToRight)
        self.dkey.editingFinished.connect(lambda: self._eng("deepl_key", self.dkey.text().strip()))
        self.mail = QLineEdit(e["mymemory_email"]); self.mail.setLayoutDirection(Qt.LeftToRight); self.mail.setPlaceholderText("اختياري — يرفع الحد اليومي")
        self.mail.editingFinished.connect(lambda: self._eng("mymemory_email", self.mail.text().strip()))
        for w in (self.ckey, self.dkey, self.mail, self.cmodel):
            w.setMinimumWidth(300)
        l3.addWidget(row("مفتاح Claude API", self.ckey, "الأذكى في فهم السياق والحوارات. احصل عليه من console.anthropic.com — التكلفة على حسابك."))
        l3.addWidget(self.advanced(row("نموذج Claude", self.cmodel)))
        l3.addWidget(row("مفتاح DeepL", self.dkey, "المفاتيح المجانية تنتهي بـ :fx"))
        l3.addWidget(self.advanced(row("بريد MyMemory", self.mail)))
        l3.addWidget(hint("تُحفظ المفاتيح في ملف إعداداتك على جهازك فقط."))
        self.v.addWidget(c3)

        c4, l4 = card(); l4.addWidget(title("اختبار المحركات على جهازك", "check"))
        l4.addWidget(hint("يرسل جملة تجريبية لكل محرك ويعرض النتيجة والزمن — استخدمه عند أي مشكلة في الترجمة."))
        self.test_btn = QPushButton(icons.icon("play", "#1A1204"), "  اختبر المحركات الآن"); self.test_btn.setObjectName("Primary")
        self.test_btn.clicked.connect(self._test)
        l4.addWidget(self.test_btn, 0, Qt.AlignRight)
        self.test_out = QLabel(""); self.test_out.setWordWrap(True); self.test_out.setTextFormat(Qt.RichText)
        l4.addWidget(self.test_out)
        self.v.addWidget(c4)
        self.v.addStretch(1)
        ctrl.engines_tested.connect(self._tested)
        ctrl.profile_changed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        p, e = self.prof, self.ctrl.settings.data["engines"]
        for w in (self.src, self.tgt, self.style, self.ocr):
            w.blockSignals(True)
        self.src.setCurrentIndex(max(0, self.src.findData(p["lang"]["src"])))
        self.tgt.setCurrentIndex(max(0, self.tgt.findData(p["lang"]["tgt"])))
        self.style.setCurrentIndex(max(0, self.style.findData(p["translate"]["style"])))
        self.ocr.setCurrentIndex(max(0, self.ocr.findData(p["ocr"]["engine"])))
        for w in (self.src, self.tgt, self.style, self.ocr):
            w.blockSignals(False)
        self.list.blockSignals(True); self.list.clear()
        for eid in e["order"]:
            it = QListWidgetItem(ENGINE_INFO[eid]["name"]); it.setData(Qt.UserRole, eid)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if e["enabled"].get(eid) else Qt.Unchecked)
            self.list.addItem(it)
        self.list.blockSignals(False)

    def _eng(self, key, val):
        self.ctrl.settings.set(f"engines.{key}", val)
        if key in ("claude_key", "deepl_key") and val:
            eid = key.split("_")[0]
            self.ctrl.settings.set(f"engines.enabled.{eid}", True)
            self.refresh()

    def _save_engines(self, *_):
        order, enabled = [], {}
        for i in range(self.list.count()):
            it = self.list.item(i); eid = it.data(Qt.UserRole)
            order.append(eid); enabled[eid] = it.checkState() == Qt.Checked
        self.ctrl.settings.set("engines.order", order)
        self.ctrl.settings.set("engines.enabled", enabled)

    def _move(self, d):
        r = self.list.currentRow()
        if r < 0 or not (0 <= r + d < self.list.count()):
            return
        it = self.list.takeItem(r); self.list.insertItem(r + d, it); self.list.setCurrentRow(r + d)
        self._save_engines()

    def _test(self):
        self.test_btn.setEnabled(False); self.test_out.setText("جارٍ الاختبار…")
        self.ctrl.test_engines()

    def _tested(self, rows):
        self.test_btn.setEnabled(True)
        out = []
        for r in rows:
            name = ENGINE_INFO[r["id"]]["name"]
            if r["ok"]:
                out.append(f"<p><b style='color:{theme.OK}'>✓ {name}</b> — {r['ms']} ms<br><span>{r['text']}</span></p>")
            else:
                from ..messages import engine_test_error
                out.append(f"<p><b style='color:{theme.WARN}'>✗ {name}</b> — {engine_test_error(r['error'])}</p>")
        self.test_out.setText("".join(out))


# ======================================================================= games
class GamesPage(Page):
    title_text = "الألعاب"

    def __init__(self, ctrl):
        super().__init__(ctrl)
        c, l = card(gold=True); l.addWidget(title("إعدادات مستقلة لكل لعبة", "games"))
        l.addWidget(hint("كل لعبة تحفظ منطقتها وشاشتها وشكل الترجمة ولغتها ومحركها. عند فتح لعبة محفوظة يبدّل البرنامج إعداداتها تلقائياً."))
        self.auto = QCheckBox("تبديل الإعدادات تلقائياً عند فتح لعبة محفوظة")
        self.auto.setChecked(ctrl.settings.data["auto_profile"])
        self.auto.toggled.connect(lambda b: ctrl.settings.set("auto_profile", b))
        l.addWidget(self.auto)
        self.fg = hint("")
        l.addWidget(self.fg)
        self.v.addWidget(c)
        c2, l2 = card()
        self.list = QListWidget(); self.list.setMinimumHeight(240)
        self.list.itemDoubleClicked.connect(lambda _: self._activate())
        l2.addWidget(self.list)
        b = QHBoxLayout()
        for ic, t, fn, obj in (("check", "تفعيل", self._activate, "Primary"), ("plus", "أضف من البرامج المفتوحة", self._add_running, ""),
                               ("edit", "إضافة يدوية", self._add_manual, ""), ("trash", "حذف", self._delete, "Danger")):
            btn = QPushButton(icons.icon(ic, "#1A1204" if obj == "Primary" else theme.GOLD2), "  " + t)
            if obj:
                btn.setObjectName(obj)
            btn.clicked.connect(fn); b.addWidget(btn)
        l2.addLayout(b)
        self.v.addWidget(c2)

        # ---- this game's dictionary
        c3, l3 = card()
        self.gl_title = title("قاموس اللعبة", "book", "violet"); l3.addWidget(self.gl_title)
        l3.addWidget(hint("أسماء الشخصيات والأسلحة والأماكن وأي كلمة تريد ترجمتها بطريقة ثابتة. "
                          "يُطبّق على اللعبة المفعّلة الآن، ويعمل مع كل محركات الترجمة."))
        self.gl = QTableWidget(0, 3); self.gl.setHorizontalHeaderLabels(["الكلمة في اللعبة", "ترجمتها", "النوع"])
        self.gl.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.gl.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.gl.verticalHeader().setVisible(False); self.gl.setMinimumHeight(200)
        self.gl.itemChanged.connect(lambda _: self._gl_save())
        l3.addWidget(self.gl)
        gb = QHBoxLayout()
        for ic, t, fn in (("plus", "إضافة كلمة", self._gl_add), ("trash", "حذف المحدد", self._gl_del),
                          ("download", "استيراد CSV", self._gl_import), ("save", "تصدير CSV", self._gl_export)):
            btn = QPushButton(icons.icon(ic, theme.GOLD2), "  " + t); btn.clicked.connect(fn); gb.addWidget(btn)
        gb.addStretch(1); l3.addLayout(gb)
        self.v.addWidget(c3)
        self.v.addStretch(1)
        ctrl.profile_changed.connect(self.refresh)
        ctrl.game_changed.connect(lambda exe: self.fg.setText(f"البرنامج في المقدمة الآن: {exe or '—'}"))
        self.refresh()

    KINDS = [("character", "شخصية"), ("weapon", "سلاح أو أداة"), ("place", "مكان"), ("other", "أخرى")]

    def _gl_kind_box(self, kind):
        cb = QComboBox()
        for k, t in self.KINDS:
            cb.addItem(t, k)
        cb.setCurrentIndex(max(0, cb.findData(kind)))
        cb.currentIndexChanged.connect(lambda _: self._gl_save())
        return cb

    def _gl_fill(self):
        self.gl.blockSignals(True); self.gl.setRowCount(0)
        for g in self.prof.get("glossary", []):
            r = self.gl.rowCount(); self.gl.insertRow(r)
            self.gl.setItem(r, 0, QTableWidgetItem(g.get("src", ""))); self.gl.setItem(r, 1, QTableWidgetItem(g.get("tr", "")))
            self.gl.setCellWidget(r, 2, self._gl_kind_box(g.get("kind", "other")))
        self.gl.blockSignals(False)
        self.gl_title.findChildren(QLabel)[-1].setText(f"قاموس «{self.prof['name']}»")

    def _gl_rows(self):
        out = []
        for r in range(self.gl.rowCount()):
            a, b = self.gl.item(r, 0), self.gl.item(r, 1)
            src, tr = (a.text().strip() if a else ""), (b.text().strip() if b else "")
            cb = self.gl.cellWidget(r, 2)
            out.append({"src": src, "tr": tr, "kind": cb.currentData() if cb else "other"})
        return out

    def _gl_save(self):
        self.ctrl.settings.update_profile("glossary", [g for g in self._gl_rows() if g["src"] or g["tr"]])

    def _gl_add(self):
        r = self.gl.rowCount(); self.gl.insertRow(r)
        self.gl.setItem(r, 0, QTableWidgetItem("")); self.gl.setItem(r, 1, QTableWidgetItem(""))
        self.gl.setCellWidget(r, 2, self._gl_kind_box("character"))
        self.gl.setCurrentCell(r, 0); self.gl.editItem(self.gl.item(r, 0))

    def _gl_del(self):
        rows = sorted({i.row() for i in self.gl.selectedIndexes()}, reverse=True)
        for r in rows:
            self.gl.removeRow(r)
        self._gl_save()

    def _gl_import(self):
        import csv
        path, _ = QFileDialog.getOpenFileName(self, "استيراد قاموس", "", "CSV (*.csv *.txt)")
        if not path:
            return
        try:
            with open(path, encoding="utf-8-sig", newline="") as f:
                rows = [r for r in csv.reader(f) if len(r) >= 2 and r[0].strip() and r[1].strip()]
        except (OSError, csv.Error, UnicodeDecodeError) as e:
            self.ctrl.toast(f"تعذّر قراءة الملف: {e}", err=True); return
        kinds = {k for k, _ in self.KINDS}
        new = [{"src": r[0].strip()[:80], "tr": r[1].strip()[:80], "kind": (r[2].strip() if len(r) > 2 and r[2].strip() in kinds else "other")}
               for r in rows if r[0].strip().lower() not in ("source", "الكلمة في اللعبة")]
        have = {g["src"].lower() for g in self.prof.get("glossary", [])}
        merged = self.prof.get("glossary", []) + [g for g in new if g["src"].lower() not in have]
        self.ctrl.settings.update_profile("glossary", merged); self._gl_fill()
        self.ctrl.toast(f"أُضيفت {len(merged) - len(have)} كلمة")

    def _gl_export(self):
        import csv
        path, _ = QFileDialog.getSaveFileName(self, "تصدير القاموس", f"{self.prof['name']}-dictionary.csv", "CSV (*.csv)")
        if path:
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f); w.writerow(["source", "translation", "kind"])
                for g in self.prof.get("glossary", []):
                    w.writerow([g["src"], g["tr"], g.get("kind", "other")])
            self.ctrl.toast("صُدّر القاموس")

    def refresh(self):
        self._gl_fill()
        self.list.clear()
        s = self.ctrl.settings
        for pid, p in s.data["profiles"].items():
            mark = "●  " if pid == s.profile_id else "     "
            it = QListWidgetItem(f"{mark}{p['name']}" + (f"   —   {p['exe']}" if p["exe"] else "   —   تُستخدم لأي لعبة غير محفوظة"))
            it.setData(Qt.UserRole, pid)
            self.list.addItem(it)

    def _sel(self):
        it = self.list.currentItem()
        return it.data(Qt.UserRole) if it else None

    def _activate(self):
        pid = self._sel()
        if pid:
            self.ctrl.switch_profile(pid)

    def _delete(self):
        pid = self._sel()
        if not pid or pid == "default":
            self.ctrl.toast("لا يمكن حذف الإعدادات العامة", err=True); return
        if QMessageBox.question(self, "حذف", "حذف إعدادات هذه اللعبة؟") == QMessageBox.Yes:
            self.ctrl.settings.delete_profile(pid); self.ctrl.profile_changed.emit()

    def _add_manual(self):
        name, ok = QInputDialog.getText(self, "إضافة لعبة", "اسم اللعبة:")
        if not ok or not name.strip():
            return
        exe, ok = QInputDialog.getText(self, "إضافة لعبة", "اسم ملف التشغيل (مثل eldenring.exe):")
        if ok:
            self.ctrl.add_game(name.strip(), exe.strip())

    def _add_running(self):
        procs = self.ctrl.running_games()
        if not procs:
            self.ctrl.toast("لم يُعثر على برامج بنوافذ مفتوحة", err=True); return
        exe, ok = QInputDialog.getItem(self, "أضف لعبة مفتوحة", "اختر اللعبة من البرامج المفتوحة:", procs, 0, False)
        if ok and exe:
            self.ctrl.add_game(exe.rsplit(".", 1)[0], exe)


# ======================================================================= history
class HistoryPage(Page):
    title_text = "السجل"

    def __init__(self, ctrl):
        super().__init__(ctrl)
        top = QHBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText("ابحث في الأصل أو الترجمة أو اسم اللعبة…")
        self.search.textChanged.connect(lambda _: self.t.start(250))
        top.addWidget(self.search, 1)
        for t, fn, obj in (("تصدير", self._export, ""), ("مسح السجل", self._clear, "Danger")):
            b = QPushButton(t); b.clicked.connect(fn)
            if obj:
                b.setObjectName(obj)
            top.addWidget(b)
        self.v.addLayout(top)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["الوقت", "اللعبة", "النص الأصلي", "الترجمة (قابلة للتعديل)"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(True)
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.table.setMinimumHeight(420)
        self.table.itemChanged.connect(self._edited)
        self.v.addWidget(self.table)
        self.v.addWidget(hint("نقرتان على أي ترجمة لتعديلها. التعديل يُحفظ في ذاكرة البرنامج ويُستخدم تلقائياً كلما ظهر النص نفسه."))
        mem = QHBoxLayout()
        self.mem = hint(""); mem.addWidget(self.mem, 1)
        b = QPushButton("مسح ذاكرة الترجمة"); b.clicked.connect(self._clear_mem); mem.addWidget(b)
        self.v.addLayout(mem)
        self.t = QTimer(self); self.t.setSingleShot(True); self.t.timeout.connect(self.refresh)
        ctrl.result.connect(lambda _: self.isVisible() and self.t.start(400))

    def refresh(self):
        rows = self.ctrl.store.history(self.search.text().strip(), 500)
        self.table.blockSignals(True)
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            vals = [dt.datetime.fromtimestamp(r["ts"]).strftime("%Y-%m-%d %H:%M"), r["game"], r["src_text"], r["translation"]]
            for j, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if j < 3:
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                if j == 2:
                    it.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                it.setData(Qt.UserRole, r["id"])
                self.table.setItem(i, j, it)
        self.table.resizeRowsToContents()
        self.table.blockSignals(False)
        st = self.ctrl.store.stats()
        self.mem.setText(f"ذاكرة الترجمة: {st['memory']} نص محفوظ، وفّرت {st['hits']} طلب ترجمة • تعديلاتك: {st['overrides']}")

    def _edited(self, it):
        if it.column() == 3 and it.text().strip():
            self.ctrl.store.edit_history(it.data(Qt.UserRole), it.text().strip())
            self.ctrl.toast("حُفظ تعديلك وسيُستخدم تلقائياً")

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, "تصدير السجل", str(data_dir() / "arabize-history.csv"), "CSV (*.csv);;Text (*.txt)")
        if not path:
            return
        rows = self.ctrl.store.history(self.search.text().strip(), 5000)
        if path.endswith(".txt"):
            with open(path, "w", encoding="utf-8-sig") as f:
                for r in rows:
                    f.write(f"[{dt.datetime.fromtimestamp(r['ts']):%Y-%m-%d %H:%M}] {r['game']}\n{r['src_text']}\n{r['translation']}\n\n")
        else:
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f); w.writerow(["time", "game", "original", "translation", "engine"])
                for r in rows:
                    w.writerow([dt.datetime.fromtimestamp(r["ts"]).isoformat(" ", "minutes"), r["game"], r["src_text"], r["translation"], r["engine"]])
        self.ctrl.toast(f"تم التصدير: {os.path.basename(path)}")

    def _clear(self):
        if QMessageBox.question(self, "مسح السجل", "مسح كل السجل؟ لن تتأثر ذاكرة الترجمة ولا تعديلاتك.") == QMessageBox.Yes:
            self.ctrl.store.clear_history(); self.refresh()

    def _clear_mem(self):
        if QMessageBox.question(self, "مسح الذاكرة", "مسح ذاكرة الترجمة؟ ستُطلب الترجمات من جديد عند الحاجة. تعديلاتك اليدوية تبقى.") == QMessageBox.Yes:
            n = self.ctrl.store.clear_memory(); self.refresh(); self.ctrl.toast(f"حُذف {n} نص من الذاكرة")


# ======================================================================= hotkeys
class HotkeysPage(Page):
    title_text = "الاختصارات"
    NAMES = {"toggle": "تشغيل / إيقاف الترجمة", "region": "تحديد منطقة الترجمة", "hide": "إخفاء / إظهار الترجمة",
             "mode": "التبديل بين الشاشة والواقع الافتراضي", "retranslate": "ترجم الشاشة الآن",
             "size_up": "تكبير الترجمة", "size_down": "تصغير الترجمة", "hud": "إظهار / إخفاء مؤشر الأداء (FPS والحرارة)",
             "vr_left": "VR: تحريك اللوحة لليسار", "vr_right": "VR: تحريك اللوحة لليمين", "vr_up": "VR: رفع اللوحة",
             "vr_down": "VR: خفض اللوحة", "vr_nearer": "VR: تقريب اللوحة", "vr_farther": "VR: إبعاد اللوحة",
             "vr_bigger": "VR: تكبير اللوحة", "vr_smaller": "VR: تصغير اللوحة", "vr_center": "VR: إعادة اللوحة أمامك",
             "vr_placement": "VR: تبديل مكان اللوحة (أمام العين / تتبع / ثابتة)"}

    def __init__(self, ctrl):
        super().__init__(ctrl)
        c, l = card(); l.addWidget(title("اختصارات تعمل من داخل اللعبة", "keyboard"))
        l.addWidget(hint("اضغط على الخانة ثم اضغط الاختصار الجديد. تعمل الاختصارات حتى واللعبة في المقدمة."))
        self.edits = {}
        for k, name in self.NAMES.items():
            e = QKeySequenceEdit(); e.setMaximumSequenceLength(1) if hasattr(e, "setMaximumSequenceLength") else None
            e.setLayoutDirection(Qt.LeftToRight); e.setMinimumWidth(220)
            e.editingFinished.connect(self._save)
            self.edits[k] = e
            l.addWidget(row(name, e))
        b = QHBoxLayout()
        r = QPushButton("استعادة الافتراضي"); r.clicked.connect(self._reset); b.addWidget(r); b.addStretch(1)
        l.addLayout(b)
        self.status = hint(""); l.addWidget(self.status)
        l.addWidget(hint("إن كانت اللعبة تعمل كمسؤول (Administrator) شغّل عرب لعبتك كمسؤول أيضاً حتى تصلها الاختصارات."))
        self.v.addWidget(c); self.v.addStretch(1)
        self.refresh()

    def refresh(self):
        hk = self.ctrl.settings.data["hotkeys"]
        for k, e in self.edits.items():
            e.blockSignals(True); e.setKeySequence(QKeySequence(hk.get(k, ""))); e.blockSignals(False)

    def _save(self):
        hk = {k: e.keySequence().toString(QKeySequence.PortableText) for k, e in self.edits.items()}
        self.ctrl.settings.set("hotkeys", hk)
        bad = self.ctrl.apply_hotkeys()
        self.status.setText("تم الحفظ." if not bad else "لم يُفعّل: " + "، ".join(self.NAMES[b] for b in bad))

    def _reset(self):
        self.ctrl.settings.set("hotkeys", dict(DEFAULT_HOTKEYS)); self.refresh(); self._save()


# ======================================================================= device & performance
class DevicePage(Page):
    title_text = "الجهاز والأداء"

    def __init__(self, ctrl):
        super().__init__(ctrl)
        c, l = card(gold=True); l.addWidget(title("مواصفات جهازك", "cpu"))
        self.spec_lbl = QLabel("…"); self.spec_lbl.setTextFormat(Qt.RichText); self.spec_lbl.setWordWrap(True)
        self.spec_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        l.addWidget(self.spec_lbl)
        cb = QPushButton(icons.icon("download", theme.GOLD2), "  نسخ المواصفات"); cb.clicked.connect(self._copy)
        l.addWidget(cb, 0, Qt.AlignRight)
        self.v.addWidget(c)

        c2, l2 = card(); l2.addWidget(title("القراءات الآن", "zap"))
        g = QGridLayout(); g.setHorizontalSpacing(18); g.setVerticalSpacing(10)
        self.live = {}
        for i, (k, name) in enumerate((("fps", "الإطارات في الثانية (FPS)"), ("cpu_temp", "حرارة المعالج"),
                                       ("cpu", "استخدام المعالج"), ("gpu_temp", "حرارة كرت الشاشة"),
                                       ("ram", "الذاكرة المستخدمة"), ("ping", "البنق إلى خدمة الترجمة"))):
            box = QFrame(); box.setObjectName("LayerBox"); bl = QVBoxLayout(box); bl.setContentsMargins(12, 8, 12, 8)
            bl.addWidget(QLabel(name))
            v = QLabel("—"); v.setObjectName("Stat"); bl.addWidget(v)
            n = hint(""); bl.addWidget(n)
            self.live[k] = (v, n)
            g.addWidget(box, i // 3, i % 3)
        l2.addLayout(g)
        self.admin_btn = QPushButton(icons.icon("power", theme.GOLD2), "  إعادة التشغيل كمسؤول لقراءة FPS")
        self.admin_btn.clicked.connect(ctrl.restart_admin); self.admin_btn.hide()
        l2.addWidget(self.admin_btn, 0, Qt.AlignRight)
        l2.addWidget(hint("FPS يُقرأ بأداة PresentMon من Intel (نفسها التي تستخدمها برامج قياس الأداء)، وويندوز يسمح بها للمسؤول فقط. "
                          "حرارة المعالج: يقرأها البرنامج من LibreHardwareMonitor إن كان يعمل (الأدق)، وإلا من حساس ويندوز التقريبي."))
        self.v.addWidget(c2)

        c3, l3 = card(); l3.addWidget(title("مؤشر الأداء فوق اللعبة", "monitor"))
        l3.addWidget(hint("نافذة صغيرة في زاوية الشاشة تعرض FPS والحرارة والذاكرة والبنق أثناء اللعب، ولا تستقبل الماوس. "
                          "اختصارها من داخل اللعبة: Ctrl+Shift+F."))
        self.hud_on = QCheckBox(); self.hud_on.toggled.connect(lambda b: ctrl.set_hud(b))
        l3.addWidget(row("إظهار المؤشر", self.hud_on))
        from ..hud import CORNERS
        self.corner = QComboBox()
        for k, t in CORNERS:
            self.corner.addItem(t, k)
        self.corner.currentIndexChanged.connect(lambda _: self._hud("corner", self.corner.currentData()))
        l3.addWidget(row("مكانه", self.corner))
        self.hud_items = {}
        hr = QHBoxLayout(); hr.setSpacing(14)
        for k, t in (("fps", "FPS"), ("cpu_temp", "حرارة المعالج"), ("cpu", "استخدام المعالج"), ("gpu_temp", "كرت الشاشة"),
                     ("ram", "الذاكرة"), ("ping", "البنق")):
            cbx = QCheckBox(t); cbx.toggled.connect(lambda b, k=k: self._hud(k, b)); hr.addWidget(cbx); self.hud_items[k] = cbx
        hr.addStretch(1); l3.addLayout(hr)
        self.hud_scale = ValueSlider(70, 200, 10, "%", 100); self.hud_scale.valueChanged.connect(lambda v: self._hud("scale", int(v)))
        l3.addWidget(row("الحجم", self.hud_scale))
        self.v.addWidget(c3); self.v.addStretch(1)
        self._specs = None
        self._timer = QTimer(self, interval=1000, timeout=self._tick)

    def _hud(self, key, val):
        self.ctrl.settings.set(f"hud.{key}", val)
        if key == "fps" and val and self.ctrl.hud.isVisible():
            self.ctrl.fps.start()
        if self.ctrl.hud.isVisible():
            self.ctrl.hud.refresh()

    def refresh(self):
        from .. import hwinfo
        if self._specs is None:
            try:
                self._specs = hwinfo.specs()
            except Exception:
                self._specs = {"os": "", "cpu": "", "cores": 0, "threads": 0, "cpu_mhz": None, "gpus": [], "ram_gb": None, "drives": []}
        s = self._specs
        def L(x) -> str:                           # keep English names and numbers in one left-to-right piece
            return "⁦" + str(x) + "⁩"

        def gb(v) -> str:
            return L(f"{v:g} GB")

        gl = "<br>".join(L(g["name"]) + (" — الذاكرة " + gb(g["vram_gb"]) if g.get("vram_gb") else "")
                         for g in s["gpus"]) or "غير معروف"
        dl = "<br>".join(L(d["mount"]) + ": السعة " + gb(d["total_gb"]) + "، المتاح " + gb(d["free_gb"])
                         for d in s["drives"]) or "غير معروف"
        speed = (" • السرعة: " + L(f"{s['cpu_mhz'] / 1000:.2f} GHz")) if s.get("cpu_mhz") else ""
        cpu = (L(s["cpu"]) + f"<br><span style='color:{theme.MUTED}'>الأنوية: {s['cores']} • المسارات: {s['threads']}"
               + speed + "</span>")
        rows = [("النظام", L(s["os"])), ("المعالج (CPU)", cpu), ("كرت الشاشة (GPU)", gl),
                ("الذاكرة العشوائية (RAM)", gb(s["ram_gb"]) if s.get("ram_gb") else "غير معروف"), ("التخزين", dl)]
        self.spec_lbl.setText("<table cellspacing=8>" + "".join(
            f"<tr><td style='color:{theme.GOLD2}'><b>{a}</b></td><td>\u200f{b.replace('<br>', '<br>\u200f')}</td></tr>" for a, b in rows) + "</table>")
        h = self.ctrl.settings.get("hud", {}) or {}
        for w in [self.hud_on, self.corner, self.hud_scale] + list(self.hud_items.values()):
            w.blockSignals(True)
        self.hud_on.setChecked(self.ctrl.hud.isVisible())
        self.corner.setCurrentIndex(max(0, self.corner.findData(h.get("corner", "top-left"))))
        for k, cbx in self.hud_items.items():
            cbx.setChecked(bool(h.get(k, True)))
        self.hud_scale.setValue(h.get("scale", 100))
        for w in [self.hud_on, self.corner, self.hud_scale] + list(self.hud_items.values()):
            w.blockSignals(False)

    def showEvent(self, e):
        super().showEvent(e)
        self.ctrl.sensors.start(); self.ctrl.fps.start()
        self._timer.start(); self._tick()

    def hideEvent(self, e):
        super().hideEvent(e)
        self._timer.stop()
        self.ctrl.sensors.stop()
        if not self.ctrl.hud.isVisible():
            self.ctrl.fps.stop()

    def _tick(self):
        from ..hwinfo import FPS_STATES, TEMP_SOURCES
        d, fps = self.ctrl.sensors.data, self.ctrl.fps
        f = fps.current()
        self.live["fps"][0].setText(f"{f:.0f}" if f is not None else "—")
        self.live["fps"][1].setText(f"اللعبة: {fps.exe}" if (fps.state == "running" and fps.exe) else FPS_STATES.get(fps.state, ""))
        self.admin_btn.setVisible(fps.state == "need_admin")
        t = d.get("cpu_temp")
        self.live["cpu_temp"][0].setText(f"{t:.0f}°C" if t is not None else "—")
        self.live["cpu_temp"][1].setText(TEMP_SOURCES.get(d.get("cpu_temp_src"), d.get("cpu_temp_src") or "") if t is not None
                                         else self.ctrl.sensors.temp_note or "جارٍ القراءة…")
        self.live["cpu"][0].setText(f"{d['cpu']:.0f}%" if d.get("cpu") is not None else "—")
        g = d.get("gpu_temp")
        self.live["gpu_temp"][0].setText(f"{g:.0f}°C" if g is not None else "—")
        self.live["gpu_temp"][1].setText(f"الحمل {d['gpu_load']:.0f}%" if d.get("gpu_load") is not None else
                                         ("" if g is not None else "متاح مع NVIDIA أو LibreHardwareMonitor"))
        self.live["ram"][0].setText(f"{d['ram_used_gb']:.1f} / {d['ram_total_gb']:.0f} GB" if d.get("ram_used_gb") is not None else "—")
        self.live["ram"][1].setText(f"{d['ram_pct']:.0f}%" if d.get("ram_pct") is not None else "")
        ping = self.ctrl.manager.ping()
        self.live["ping"][0].setText(f"{min(ping.values())} ms" if ping else "—")
        self.live["ping"][1].setText("" if ping else "يظهر بعد أول ترجمة")

    def _copy(self):
        from .. import hwinfo
        QGuiApplication.clipboard().setText(hwinfo.specs_text(self._specs or hwinfo.specs()))
        self.ctrl.toast("نُسخت مواصفات جهازك")


# ======================================================================= help
class HelpPage(Page):
    title_text = "المساعدة"
    FAQ = [
        ("الترجمة لا تظهر فوق اللعبة", "البرنامج يعيد رفع الترجمة فوق اللعبة باستمرار، ويعمل مع «ملء الشاشة» في معظم ألعاب ويندوز 10 و11. "
         "بعض الألعاب القديمة في «ملء الشاشة الحصري» تمنع أي نافذة من الظهور فوقها: اختر فيها «نافذة بلا حواف» (Borderless). وتأكد أن الترجمة ليست مخفية (Ctrl+Shift+H)."),
        ("الصورة سوداء أو لا يقرأ شيئاً", "من صفحة «الشاشة والمنطقة» جرّب طريقة التقاط أخرى: «نافذة اللعبة فقط» تلتقط اللعبة نفسها مثل OBS، و«DXGI» تعمل مع ملء الشاشة."),
        ("لا يقرأ النص أو يقرأه خطأ", "حدّد منطقة الحوار فقط بدل الشاشة كاملة، واجعل حجم الترجمة في اللعبة أكبر إن أمكن. جرّب محرك القراءة الآخر من صفحة المحركات (الوضع المتقدم)."),
        ("الترجمة بطيئة", "حدّد منطقة صغيرة، وقلّل «انتظار ثبات النص»، وفعّل محرك ترجمة واحد سريع. النصوص المتكررة تُترجم فوراً من الذاكرة."),
        ("تظهر ملاحظة عن خدمة الترجمة", "خدمات الترجمة مواقع على الإنترنت؛ إن تأخرت إحداها أو انشغلت ينتقل البرنامج للخدمة التالية ويعيد المحاولة وحده. "
         "جهازك سليم ولا يلزمك فعل شيء. الجمل المترجمة سابقاً تظهر فوراً من الذاكرة حتى دون إنترنت. وزمن الاتصال (البنق) ظاهر في صفحة التشغيل."),
        ("الترجمة لا تظهر في تصوير الشاشة أو التسجيل", "فعّل «تظهر الترجمة في لقطات الشاشة والتسجيل» من صفحة المظهر (مفعّل افتراضياً). "
         "في OBS استخدم «التقاط الشاشة» (Display Capture)؛ «التقاط اللعبة» (Game Capture) يأخذ اللعبة وحدها دون أي نافذة فوقها."),
        ("FPS لا يظهر", "قراءة الإطارات تحتاج صلاحية المسؤول في ويندوز: من صفحة «الجهاز والأداء» اضغط «إعادة التشغيل كمسؤول»."),
        ("حرارة المعالج لا تظهر", "ويندوز لا يعطي حرارة المعالج لكل الأجهزة. شغّل برنامج LibreHardwareMonitor المجاني بجانب عرب لعبتك، وسيقرأ منه الحرارة الدقيقة تلقائياً."),
        ("الاختصارات لا تعمل داخل اللعبة", "إن كانت اللعبة تعمل كمسؤول، شغّل البرنامج كمسؤول أيضاً. وتأكد أن الاختصار غير مستخدم في اللعبة نفسها."),
        ("التلفزيون لا يظهر", "وصّل التلفزيون بالكمبيوتر كشاشة عرض (HDMI)، وفعّله من إعدادات العرض في ويندوز، ثم افتح صفحة «الشاشة والمنطقة»."),
        ("وضع VR لا يعمل", "شغّل SteamVR والنظارة متصلة أولاً، ثم اضغط «اختبر اللوحة في النظارة». نظارات Quest تعمل عبر Link أو Air Link أو Virtual Desktop."),
    ]

    def __init__(self, ctrl):
        super().__init__(ctrl)
        c, l = card(gold=True); l.addWidget(title("فيديو الشرح", "play"))
        l.addWidget(hint("يعمل وحده كالفيديو من الألف إلى الياء: اختيار اللعبة، وتشغيل الترجمة، وتخصيص شكلها ومكانها، ووضع الشاشة ووضع الواقع الافتراضي."))
        b = QPushButton(icons.icon("play", "#1A1204"), "  إعادة الشرح"); b.setObjectName("Primary"); b.clicked.connect(ctrl.show_tutorial)
        l.addWidget(b, 0, Qt.AlignRight)
        self.v.addWidget(c)
        c2, l2 = card(); l2.addWidget(title("حل المشاكل الشائعة", "help"))
        for q, a in self.FAQ:
            ql = QLabel(f"<b style='color:{theme.GOLD2}'>{q}</b><br>{a}"); ql.setWordWrap(True); ql.setTextFormat(Qt.RichText)
            ql.setContentsMargins(0, 4, 0, 8)
            l2.addWidget(ql)
        self.v.addWidget(c2)
        c3, l3 = card(); l3.addWidget(title("عن البرنامج", "pad"))
        l3.addWidget(QLabel(f"{APP_NAME_AR} | {APP_NAME_EN} — الإصدار {APP_VERSION}"))
        l3.addWidget(hint(f"مجلد الإعدادات والذاكرة: {data_dir()}"))
        ob = QPushButton("فتح مجلد الإعدادات"); ob.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(data_dir()))))
        l3.addWidget(ob, 0, Qt.AlignRight)
        self.v.addWidget(c3)

        c4, l4 = card(); l4.addWidget(title("النسخ الاحتياطي ونقل الإعدادات", "save" if "save" in icons.icons3d.GLYPHS else "download", "emerald"))
        l4.addWidget(hint("ملف واحد فيه كل ألعابك وقوالبك وقواميسك واختصاراتك. انقله لجهاز آخر أو احتفظ به. مفاتيح API لا تُحفظ فيه."))
        bb = QHBoxLayout()
        e = QPushButton(icons.icon("download", theme.GOLD2), "  تصدير الإعدادات"); e.clicked.connect(self._export); bb.addWidget(e)
        i = QPushButton(icons.icon("plus", theme.GOLD2), "  استيراد الإعدادات"); i.clicked.connect(self._import); bb.addWidget(i)
        bb.addStretch(1); l4.addLayout(bb)
        self.v.addWidget(c4)

        c5, l5 = card(); l5.addWidget(title("سجل الأخطاء", "info", "slate"))
        from .. import logs
        l5.addWidget(hint(f"يسجّل البرنامج الأخطاء فقط (بدون صور أو ترجمات أو مفاتيح) في: {logs.log_dir()}"))
        lb = QHBoxLayout()
        o = QPushButton("فتح مجلد السجلات"); o.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(logs.log_dir()))))
        r = QPushButton("نسخ تقرير المشكلة"); r.clicked.connect(self._copy_report)
        lb.addWidget(o); lb.addWidget(r); lb.addStretch(1); l5.addLayout(lb)
        self.v.addWidget(c5); self.v.addStretch(1)

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, "تصدير الإعدادات", "arabize-settings.json", "JSON (*.json)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.ctrl.settings.export_text())
            self.ctrl.toast("صُدّرت الإعدادات")

    def _import(self):
        path, _ = QFileDialog.getOpenFileName(self, "استيراد الإعدادات", "", "JSON (*.json)")
        if not path:
            return
        if QMessageBox.question(self, "استيراد الإعدادات", "ستُستبدل إعداداتك الحالية بإعدادات الملف. متابعة؟") != QMessageBox.Yes:
            return
        try:
            with open(path, encoding="utf-8") as f:
                n = self.ctrl.settings.import_text(f.read())
        except (OSError, ValueError) as e:
            self.ctrl.toast(f"تعذّر الاستيراد: {e}", err=True); return
        self.ctrl.apply_display(); self.ctrl.apply_hotkeys(); self.ctrl.profile_changed.emit()
        self.ctrl.toast(f"استُوردت الإعدادات ({n} من الألعاب)")

    def _copy_report(self):
        from .. import logs
        QGuiApplication.clipboard().setText(logs.report())
        self.ctrl.toast("نُسخ التقرير — الصقه في رسالتك")
