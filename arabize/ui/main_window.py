"""Main window: sidebar navigation, header with game profile and simple/advanced mode, page stack."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QHBoxLayout, QLabel, QMainWindow, QPushButton,
                               QStackedWidget, QVBoxLayout, QWidget)

from ..config import APP_NAME_AR, APP_NAME_EN, APP_VERSION
from . import icons, theme
from .pages import DevicePage, EnginesPage, GamesPage, HelpPage, HistoryPage, HomePage, HotkeysPage, LookPage, ScreensPage
from .widgets import Toast

NAV = [("power", "التشغيل", HomePage, "gold"), ("monitor", "الشاشة والمنطقة", ScreensPage, "blue"),
       ("palette", "المظهر والقوالب", LookPage, "rose"), ("lang", "المحركات واللغة", EnginesPage, "cyan"),
       ("games", "الألعاب", GamesPage, "violet"), ("hist", "السجل", HistoryPage, "emerald"),
       ("keyboard", "الاختصارات", HotkeysPage, "slate"), ("cpu", "الجهاز والأداء", DevicePage, "cyan"),
       ("help", "المساعدة", HelpPage, "coral")]


class MainWindow(QMainWindow):
    def __init__(self, ctrl):
        super().__init__()
        self.ctrl = ctrl
        self.setWindowTitle(f"{APP_NAME_AR} | {APP_NAME_EN}")
        self.setWindowIcon(theme.app_icon())
        self.resize(1240, 820)
        self.setMinimumSize(980, 680)
        root = QWidget(); root.setObjectName("Root"); self.setCentralWidget(root)
        h = QHBoxLayout(root); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(0)

        side = QWidget(); side.setObjectName("Sidebar"); side.setFixedWidth(236)
        sv = QVBoxLayout(side); sv.setContentsMargins(16, 22, 16, 16); sv.setSpacing(4)
        brand = QHBoxLayout()
        logo = QLabel(); logo.setPixmap(icons.tile("pad", "gold", 46)); brand.addWidget(logo)
        names = QVBoxLayout(); names.setSpacing(0)
        b1 = QLabel(APP_NAME_AR); b1.setObjectName("Brand"); b1.setFont(theme.display_font(22)); names.addWidget(b1)
        b2 = QLabel(APP_NAME_EN.upper()); b2.setObjectName("BrandEn"); names.addWidget(b2)
        brand.addLayout(names); brand.addStretch(1)
        sv.addLayout(brand); sv.addSpacing(22)
        self.stack = QStackedWidget()
        self.navgroup = QButtonGroup(self)
        self.pages = []
        for i, (ic, text, cls, hue) in enumerate(NAV):
            b = QPushButton(icons.tile_icon(ic, hue, 32), "  " + text)
            b.setObjectName("Nav"); b.setCheckable(True); b.setIconSize(QSize(32, 32))
            b.clicked.connect(lambda _=False, i=i: self.go(i))
            self.navgroup.addButton(b, i); sv.addWidget(b)
            page = cls(ctrl); self.pages.append(page); self.stack.addWidget(page)
        sv.addStretch(1)
        self.run_dot = QLabel(); sv.addWidget(self.run_dot)
        ver = QLabel(f"الإصدار {APP_VERSION}"); ver.setObjectName("Hint"); sv.addWidget(ver)
        h.addWidget(side)

        main = QWidget(); mv = QVBoxLayout(main); mv.setContentsMargins(0, 18, 0, 0); mv.setSpacing(6)
        hdr = QHBoxLayout(); hdr.setContentsMargins(26, 0, 26, 0)
        self.page_title = QLabel(); self.page_title.setObjectName("PageTitle"); self.page_title.setFont(theme.display_font(26))
        hdr.addWidget(self.page_title); hdr.addStretch(1)
        hdr.addWidget(QLabel("إعدادات اللعبة:"))
        self.profile = QComboBox(); self.profile.setMinimumWidth(200)
        self.profile.activated.connect(lambda _: ctrl.switch_profile(self.profile.currentData()))
        hdr.addWidget(self.profile)
        self.adv = QCheckBox("الوضع المتقدم"); self.adv.setToolTip("إظهار الإعدادات المتقدمة")
        self.adv.setChecked(ctrl.settings.data["ui_mode"] == "advanced")
        self.adv.toggled.connect(self._set_adv)
        hdr.addSpacing(14); hdr.addWidget(self.adv)
        mv.addLayout(hdr)
        mv.addWidget(self.stack, 1)
        h.addWidget(main, 1)

        self.toast_w = Toast(self)
        ctrl.toast_signal.connect(lambda t, e: self.toast_w.show_msg(t, err=e))
        ctrl.profile_changed.connect(self._profiles)
        ctrl.running_changed.connect(self._running)
        self._profiles(); self._running(False)
        self._set_adv(self.adv.isChecked())
        self.go(0)

    def go(self, i: int):
        self.navgroup.button(i).setChecked(True)
        self.stack.setCurrentIndex(i)
        self.page_title.setText(NAV[i][1])
        self.pages[i].refresh()

    def go_name(self, name: str):
        idx = {"screens": 1, "look": 2, "engines": 3, "games": 4, "history": 5, "hotkeys": 6, "device": 7, "help": 8, "home": 0}.get(name, 0)
        self.go(idx)

    def _set_adv(self, on: bool):
        self.ctrl.settings.set("ui_mode", "advanced" if on else "simple")
        for p in self.pages:
            p.set_advanced(on)

    def _profiles(self):
        s = self.ctrl.settings
        self.profile.blockSignals(True); self.profile.clear()
        for pid, p in s.data["profiles"].items():
            self.profile.addItem(p["name"], pid)
        self.profile.setCurrentIndex(max(0, self.profile.findData(s.profile_id)))
        self.profile.blockSignals(False)

    def _running(self, on: bool):
        c = theme.OK if on else theme.MUTED
        self.run_dot.setText(f"<span style='color:{c}'>●</span>  {'الترجمة تعمل' if on else 'الترجمة متوقفة'}")

    def closeEvent(self, e):
        if self.ctrl.settings.data.get("minimize_to_tray") and self.ctrl.tray_available() and not self.ctrl.quitting:
            e.ignore(); self.hide()
            self.ctrl.toast_tray("عرب لعبتك ما زال يعمل بجانب الساعة. انقر الأيقونة لفتحه.")
        else:
            e.accept()
