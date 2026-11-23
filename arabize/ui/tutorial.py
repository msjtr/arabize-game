"""First-run interactive tutorial: 10 animated steps, replayable from the Help page."""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .. import render
from . import icons, theme
from .widgets import paint_game_scene

STEPS = [
    ("ما هو «عرب لعبتك»؟",
     "برنامج يقرأ النصوص التي تظهر في لعبتك — الحوارات والمهام والقوائم — ويترجمها إلى العربية مباشرة أثناء اللعب، "
     "ويعرضها فوق اللعبة بدون أن تنسخ أي شيء. لا يحتاج أن تدعم اللعبة العربية.", None),
    ("اختر الشاشة أو التلفزيون",
     "من صفحة «الشاشة والمنطقة» اختر الشاشة التي تعمل عليها اللعبة، والشاشة التي تظهر عليها الترجمة. "
     "أي تلفزيون LG أو Samsung أو غيره موصول بالكمبيوتر يظهر هنا كشاشة.", ("افتح صفحة الشاشات", "screens")),
    ("شغّل الترجمة",
     "اضغط الزر الذهبي الكبير في صفحة «التشغيل»، أو اضغط Ctrl+Shift+T من داخل اللعبة. "
     "يقرأ البرنامج الشاشة فقط عندما يظهر نص جديد، فلا يثقل جهازك.", None),
    ("حدّد منطقة النص",
     "الأفضل أن تحدد مكان الحوار فقط بدل الشاشة كاملة: أسرع وأدق. اضغط «تحديد منطقة» أو Ctrl+Shift+R، "
     "ثم اسحب مستطيلاً حول صندوق الحوار في اللعبة.", ("جرّب تحديد منطقة الآن", "region")),
    ("اضبط شكل الترجمة",
     "من صفحة «المظهر» تتحكم بالخط وحجمه ولونه ولون الخلفية وشفافيتها ومكان الترجمة. "
     "تقدر أيضاً تسحب الترجمة بالماوس إلى أي مكان. التغييرات تظهر في المعاينة فوراً.", ("افتح صفحة المظهر", "look")),
    ("اختر محرك الترجمة واللغة",
     "يعمل البرنامج مجاناً مع Google وMyMemory، ويمكنك إضافة Claude (الأذكى في فهم السياق) أو DeepL بمفتاحك. "
     "إن تعطل محرك ينتقل البرنامج تلقائياً للذي بعده.", ("اختبر المحركات", "engines")),
    ("الشاشة أو الواقع الافتراضي",
     "زر واضح في صفحة «التشغيل» يبدّل بين عرض الترجمة على الشاشة، وعرضها كلوحة داخل نظارة VR عبر SteamVR. "
     "لكل وضع إعداداته المستقلة. الاختصار: Ctrl+Shift+V.", None),
    ("أثناء اللعب",
     "شغّل لعبتك بوضع «نافذة بلا حواف» (Borderless) حتى تظهر الترجمة فوقها. يبقى البرنامج في شريط المهام بجانب الساعة، "
     "ويحفظ إعدادات كل لعبة على حدة ويبدّلها تلقائياً عند فتحها.", None),
    ("الإيقاف وإعادة التشغيل",
     "Ctrl+Shift+T يوقف الترجمة ويعيد تشغيلها، وCtrl+Shift+H يخفي الترجمة ويظهرها، وCtrl+Shift+E يترجم الشاشة فوراً. "
     "تقدر تغيّر كل الاختصارات من صفحة «الاختصارات».", None),
    ("حل المشاكل الشائعة",
     "الترجمة لا تظهر؟ استخدم وضع النافذة بلا حواف. لا يقرأ النص؟ حدّد منطقة أصغر. الترجمة متوقفة؟ اضغط «اختبر المحركات». "
     "تجد كل الحلول ويمكنك إعادة هذا الدرس من صفحة «المساعدة».", ("افتح المساعدة", "help")),
]


class Illustration(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(330)
        self.step = 0
        self.t = 0.0
        self.timer = QTimer(self); self.timer.timeout.connect(self._tick); self.timer.start(33)

    def set_step(self, i):
        self.step, self.t = i, 0.0
        self.update()

    def _tick(self):
        self.t += 0.033
        self.update()

    # ---- helpers
    def _sub(self, p, area, text, size=20, label="", color="#FFFFFF", opacity=72, alpha=1.0, width_frac=0.7):
        st = {"font_size": size, "color": color, "bg": "#05080F", "bg_opacity": opacity, "bold": True, "font_family": theme.FONTS["ui"]}
        items = [{"label": "x" if label else "", "label_tr": label, "tr": text}]
        w = area.width() * width_frac
        ops, h = render.layout(items, st, w)
        r = QRectF(area.x() + (area.width() - w) / 2, area.bottom() - h - area.height() * 0.08, w, h)
        render.paint(p, r, items, st, alpha, ops)
        return r

    def _key(self, p, x, y, text, glow=0.0):
        f = QFont("Segoe UI"); f.setPixelSize(16); f.setBold(True); p.setFont(f)
        w = p.fontMetrics().horizontalAdvance(text) + 26
        r = QRectF(x - w / 2, y, w, 38)
        c = QColor(theme.GOLD); c.setAlphaF(0.25 + 0.6 * glow)
        p.setPen(QPen(c, 2)); p.setBrush(QColor("#141A3A")); p.drawRoundedRect(r, 9, 9)
        p.setPen(QColor(theme.GOLD2)); p.drawText(r, Qt.AlignCenter, text)

    def _monitor(self, p, r, label, on, tv=False):
        p.setPen(QPen(QColor(theme.GOLD) if on else QColor(theme.LINE), 3 if on else 2))
        p.setBrush(QColor("#0E1330")); p.drawRoundedRect(r, 8, 8)
        inner = r.adjusted(8, 8, -8, -8)
        p.save(); clip = QPainterPath(); clip.addRoundedRect(inner, 4, 4); p.setClipPath(clip)
        paint_game_scene(p, inner, self.t * 3); p.restore()
        p.setPen(QPen(QColor(theme.LINE), 4))
        if tv:
            p.drawLine(QPointF(r.center().x() - r.width() * 0.3, r.bottom() + 14), QPointF(r.center().x() + r.width() * 0.3, r.bottom() + 14))
        else:
            p.drawLine(QPointF(r.center().x(), r.bottom()), QPointF(r.center().x(), r.bottom() + 14))
            p.drawLine(QPointF(r.center().x() - 30, r.bottom() + 14), QPointF(r.center().x() + 30, r.bottom() + 14))
        p.setPen(QColor(theme.GOLD2 if on else theme.MUTED)); f = theme.ui_font(10, True); p.setFont(f)
        p.drawText(QRectF(r.x(), r.bottom() + 18, r.width(), 24), Qt.AlignCenter, label)

    # ---- painting
    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        R = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        clip = QPainterPath(); clip.addRoundedRect(R, 20, 20); p.setClipPath(clip)
        p.fillRect(R, QColor("#0A0E24"))
        t, s = self.t, self.step
        getattr(self, f"_s{s}")(p, R, t)
        p.end()

    def _s0(self, p, R, t):
        paint_game_scene(p, R, t * 6)
        a = min(1.0, max(0.0, (t - 0.6) / 0.8))
        self._sub(p, R, "سننطلق عند الفجر. أحضر سيفك والحقني إلى الميناء.", 22, "القائدة مارا", alpha=a)
        f = theme.display_font(34); p.setFont(f); p.setPen(QColor(246, 220, 160, int(255 * min(1, t / 0.6))))
        p.drawText(R.adjusted(0, 28, 0, 0), Qt.AlignHCenter | Qt.AlignTop, "عرب لعبتك")
        f2 = QFont("Segoe UI"); f2.setPixelSize(13); f2.setLetterSpacing(QFont.AbsoluteSpacing, 3); p.setFont(f2)
        p.setPen(QColor(theme.GOLD)); p.drawText(R.adjusted(0, 82, 0, 0), Qt.AlignHCenter | Qt.AlignTop, "ARABIZE GAME")

    def _s1(self, p, R, t):
        sel = int(t / 1.6) % 3
        w = R.width() / 3.6
        specs = [(QRectF(R.x() + R.width() * 0.06, R.y() + 70, w * 0.9, w * 0.55), "شاشة الكمبيوتر", False),
                 (QRectF(R.x() + R.width() * 0.35, R.y() + 50, w * 1.15, w * 0.66), "تلفزيون LG", True),
                 (QRectF(R.x() + R.width() * 0.68, R.y() + 60, w, w * 0.6), "تلفزيون Samsung", True)]
        for i, (r, label, tv) in enumerate(specs):
            self._monitor(p, r, label, i == sel, tv)
        self._sub(p, R.adjusted(0, 0, 0, -6), "اختر الشاشة التي تعمل عليها اللعبة", 16, width_frac=0.5, opacity=60)

    def _s2(self, p, R, t):
        c = QPointF(R.center().x(), R.center().y() - 30)
        on = (t % 3) > 1.2
        pulse = (math.sin(t * 5) + 1) / 2 if on else 0
        for k in range(3):
            col = QColor(theme.GOLD); col.setAlphaF((0.25 - k * 0.07) * (0.5 + pulse) if on else 0.05)
            p.setBrush(col); p.setPen(Qt.NoPen); p.drawEllipse(c, 70 + k * 16 + pulse * 6, 70 + k * 16 + pulse * 6)
        p.setBrush(QColor(theme.GOLD) if on else QColor("#141A3A")); p.setPen(QPen(QColor(theme.GOLD), 2)); p.drawEllipse(c, 56, 56)
        p.drawPixmap(int(c.x() - 22), int(c.y() - 22), icons.pixmap("power", "#1A1204" if on else theme.GOLD2, 44, 2.4))
        self._key(p, R.center().x(), R.bottom() - 70, "Ctrl + Shift + T", pulse if on else 0.2)

    def _s3(self, p, R, t):
        paint_game_scene(p, R, 0)
        box = QRectF(R.x() + R.width() * 0.15, R.bottom() - R.height() * 0.32, R.width() * 0.7, R.height() * 0.22)
        p.setBrush(QColor(0, 0, 0, 170)); p.setPen(Qt.NoPen); p.drawRoundedRect(box, 10, 10)
        f = QFont("Segoe UI"); f.setPixelSize(15); p.setFont(f); p.setPen(QColor("#F0F0F0"))
        p.drawText(box.adjusted(18, 10, -18, -10), Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap,
                   "Captain Mara: We leave at dawn. Bring your sword\nand meet me at the docks.")
        k = min(1.0, (t % 3.2) / 1.6)
        sel = QRectF(box.x() - 8, box.y() - 8, (box.width() + 16) * k, (box.height() + 16) * k)
        p.fillRect(R, QColor(3, 5, 12, int(120 * k)))
        p.setPen(QPen(QColor(theme.GOLD), 2.5, Qt.DashLine)); p.setBrush(Qt.NoBrush); p.drawRect(sel)
        p.drawPixmap(int(sel.right() - 6), int(sel.bottom() - 6), icons.pixmap("move", theme.GOLD2, 20))

    def _s4(self, p, R, t):
        paint_game_scene(p, R, t * 4)
        i = int(t / 1.2) % 4
        sizes, colors, opas = [18, 24, 30, 22], ["#FFFFFF", "#FFE14D", "#F6DCA0", "#9FE8FF"], [72, 40, 90, 0]
        self._sub(p, R, "استعد أيها المحارب، فالمعركة الأخيرة بدأت.", sizes[i], color=colors[i], opacity=opas[i])

    def _s5(self, p, R, t):
        names = ["Google", "MyMemory", "Claude", "DeepL"]
        n = len(names); w = R.width() / (n + 1)
        fail = int(t / 2.4) % 2 == 1
        pos = (t % 2.4) / 2.4 * (2 if fail else 1)
        f = theme.ui_font(12, True); p.setFont(f)
        for i, nm in enumerate(names):
            r = QRectF(R.right() - (i + 1) * w - w * 0.25 + w * 0.5 - 60, R.center().y() - 30, 120, 56)
            active = (i == 0 and not fail) or (i == 1 and fail)
            p.setBrush(QColor(231, 185, 100, 60) if active else QColor("#141A3A"))
            p.setPen(QPen(QColor(theme.GOLD) if active else QColor(theme.LINE), 2)); p.drawRoundedRect(r, 14, 14)
            p.setPen(QColor(theme.GOLD2 if active else theme.MUTED)); p.drawText(r, Qt.AlignCenter, nm)
            if fail and i == 0:
                p.setPen(QPen(QColor(theme.ERR), 3)); p.drawLine(r.topLeft() + QPointF(14, 10), r.bottomRight() - QPointF(14, 10))
        x = R.right() - w * 0.25 - pos * w
        p.setBrush(QColor(theme.GOLD2)); p.setPen(Qt.NoPen); p.drawEllipse(QPointF(x, R.center().y() + 48), 6, 6)
        p.setPen(QColor(theme.MUTED)); p.drawText(R.adjusted(0, 0, 0, -30), Qt.AlignHCenter | Qt.AlignBottom,
                                                  "تعطل المحرك؟ ينتقل للتالي تلقائياً" if fail else "يبدأ بالمحرك الأول في قائمتك")

    def _s6(self, p, R, t):
        vr = int(t / 2) % 2 == 1
        left = QRectF(R.x() + R.width() * 0.08, R.y() + 50, R.width() * 0.38, R.height() * 0.5)
        self._monitor(p, left, "وضع الشاشة", not vr)
        if not vr:
            self._sub(p, left.adjusted(8, 8, -8, -20), "ترجمة فوق اللعبة", 12, width_frac=0.8)
        hx, hy = R.x() + R.width() * 0.72, R.y() + R.height() * 0.42
        p.setPen(QPen(QColor(theme.GOLD) if vr else QColor(theme.LINE), 4)); p.setBrush(QColor("#141A3A"))
        p.drawRoundedRect(QRectF(hx - 110, hy - 45, 220, 90), 34, 34)
        for dx in (-50, 50):
            p.setBrush(QColor(42, 33, 86) if vr else QColor("#0E1330")); p.drawEllipse(QPointF(hx + dx, hy), 34, 30)
            if vr:
                f = theme.ui_font(8, True); p.setFont(f); p.setPen(QColor("#FFFFFF"))
                p.drawText(QRectF(hx + dx - 30, hy - 8, 60, 18), Qt.AlignCenter, "ترجمة"); p.setPen(QPen(QColor(theme.GOLD), 4))
        p.setPen(QColor(theme.GOLD2 if vr else theme.MUTED)); f = theme.ui_font(10, True); p.setFont(f)
        p.drawText(QRectF(hx - 110, hy + 60, 220, 24), Qt.AlignCenter, "وضع الواقع الافتراضي")
        self._key(p, R.center().x(), R.bottom() - 58, "Ctrl + Shift + V", 1.0 if int(t * 2) % 4 == 0 else 0.2)

    def _s7(self, p, R, t):
        paint_game_scene(p, R, t * 8)
        self._sub(p, R, "عبر الجسر بسرعة، لن يصمد طويلاً!", 20)
        bar = QRectF(R.x(), R.bottom() - 30, R.width(), 30)
        p.fillRect(bar, QColor(10, 12, 26, 230))
        p.drawPixmap(int(R.x() + 16), int(bar.y() + 4), icons.pixmap("pad", theme.GOLD, 22))
        p.setPen(QColor(theme.MUTED)); f = theme.ui_font(9); p.setFont(f)
        p.drawText(bar.adjusted(50, 0, 0, 0), Qt.AlignVCenter | Qt.AlignLeft, "عرب لعبتك يعمل في الخلفية")
        tip = QRectF(R.x() + 24, R.y() + 22, 300, 40)
        p.setBrush(QColor(231, 185, 100, 40)); p.setPen(QPen(QColor(theme.GOLD), 1.5)); p.drawRoundedRect(tip, 10, 10)
        p.setPen(QColor(theme.GOLD2)); p.drawText(tip, Qt.AlignCenter, "إعدادات اللعبة: نافذة بلا حواف ✓")

    def _s8(self, p, R, t):
        paint_game_scene(p, R, t * 4)
        phase = int(t / 1.5) % 3
        if phase != 1:
            self._sub(p, R, "المهمة: اعثر على مفتاح البرج قبل الغروب", 20)
        self._key(p, R.center().x() + 130, R.y() + 40, "Ctrl + Shift + T", 1.0 if phase == 0 else 0.2)
        self._key(p, R.center().x() - 130, R.y() + 40, "Ctrl + Shift + H", 1.0 if phase == 1 else 0.2)

    def _s9(self, p, R, t):
        items = ["وضع النافذة بلا حواف", "منطقة نص أصغر وأدق", "اختبار المحركات", "تشغيل البرنامج كمسؤول للاختصارات"]
        f = theme.ui_font(14, True); p.setFont(f)
        for i, it in enumerate(items):
            a = min(1.0, max(0.0, t - i * 0.5) / 0.4)
            y = R.y() + 60 + i * 58
            r = QRectF(R.center().x() - 230, y, 460, 44)
            p.setOpacity(a)
            p.setBrush(QColor("#141A3A")); p.setPen(QPen(QColor(theme.LINE), 1.5)); p.drawRoundedRect(r, 12, 12)
            p.drawPixmap(int(r.right() - 36), int(r.y() + 11), icons.pixmap("check", theme.OK, 22))
            p.setPen(QColor(theme.MIST)); p.drawText(r.adjusted(16, 0, -46, 0), Qt.AlignVCenter | Qt.AlignRight, it)
            p.setOpacity(1.0)


class Tutorial(QDialog):
    action = Signal(str)
    finished_tutorial = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Tutorial")
        self.setWindowTitle("الدرس التعليمي — عرب لعبتك")
        self.setMinimumSize(900, 660)
        self.setLayoutDirection(Qt.RightToLeft)
        v = QVBoxLayout(self); v.setContentsMargins(26, 22, 26, 20); v.setSpacing(12)
        self.ill = Illustration(); v.addWidget(self.ill)
        self.count = QLabel(); self.count.setObjectName("Muted"); v.addWidget(self.count)
        self.title = QLabel(); self.title.setFont(theme.display_font(24)); v.addWidget(self.title)
        self.body = QLabel(); self.body.setWordWrap(True); self.body.setFont(theme.ui_font(12)); self.body.setMinimumHeight(64)
        v.addWidget(self.body)
        self.act = QPushButton(); self.act.clicked.connect(lambda: self.action.emit(STEPS[self.i][2][1]))
        v.addWidget(self.act, 0, Qt.AlignRight)
        v.addStretch(1)
        bottom = QHBoxLayout()
        self.dots = QLabel(); bottom.addWidget(self.dots)
        bottom.addStretch(1)
        skip = QPushButton("تخطي"); skip.clicked.connect(self._finish); bottom.addWidget(skip)
        self.prev = QPushButton("السابق"); self.prev.clicked.connect(lambda: self.go(self.i - 1)); bottom.addWidget(self.prev)
        self.next = QPushButton(); self.next.setObjectName("Primary"); self.next.clicked.connect(self._next); bottom.addWidget(self.next)
        v.addLayout(bottom)
        self.i = 0
        self.go(0)

    def go(self, i):
        self.i = max(0, min(len(STEPS) - 1, i))
        t, b, a = STEPS[self.i]
        self.ill.set_step(self.i)
        self.count.setText(f"الخطوة {self.i + 1} من {len(STEPS)}")
        self.title.setText(t); self.body.setText(b)
        self.act.setVisible(bool(a)); self.act.setText(("  " + a[0]) if a else "")
        if a:
            self.act.setIcon(icons.icon("play", theme.GOLD2))
        self.prev.setEnabled(self.i > 0)
        self.next.setText("ابدأ الاستخدام" if self.i == len(STEPS) - 1 else "التالي")
        self.dots.setText(" ".join(f"<span style='color:{theme.GOLD if k == self.i else theme.LINE}; font-size:18px'>●</span>" for k in range(len(STEPS))))

    def _next(self):
        if self.i == len(STEPS) - 1:
            self._finish()
        else:
            self.go(self.i + 1)

    def _finish(self):
        self.finished_tutorial.emit()
        self.close()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Left,):
            self._next()
        elif e.key() in (Qt.Key_Right,):
            self.go(self.i - 1)
        else:
            super().keyPressEvent(e)
