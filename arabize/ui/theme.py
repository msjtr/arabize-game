"""Cinematic dark/gold theme, Arabic fonts and right-to-left defaults."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase

INK = "#070A16"
DEEP = "#0F1430"
PANEL = "#121836"
LINE = "#232A4D"
MIST = "#E3E7F7"
MUTED = "#8A92B6"
GOLD = "#E7B964"
GOLD2 = "#F6DCA0"
ERR = "#FF7A6B"
OK = "#6FE3B0"
WARN = "#FFD166"

FONTS = {"ui": "IBM Plex Sans Arabic", "display": "Alexandria"}


ASSETS = Path(__file__).resolve().parents[1] / "assets"


def app_icon():
    from PySide6.QtGui import QIcon
    return QIcon(str(ASSETS / "app.png"))


_loaded = False


def load_fonts() -> None:
    """Register the bundled Arabic fonts once, so the app looks the same on every PC whatever is installed."""
    global _loaded
    if _loaded:
        return
    d = Path(__file__).resolve().parents[1] / "assets" / "fonts"
    for f in sorted(d.glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(f))
    _loaded = True


def ui_font(size: int = 10, bold: bool = False) -> QFont:
    f = QFont(FONTS["ui"])
    f.setFamilies([FONTS["ui"], "Segoe UI", "Tahoma", "Arial"])
    f.setPointSize(size)
    f.setBold(bold)
    return f


def display_font(px: int) -> QFont:
    f = QFont(FONTS["display"])
    f.setFamilies([FONTS["display"], FONTS["ui"], "Segoe UI"])
    f.setPixelSize(px)
    f.setBold(True)
    f.setLetterSpacing(QFont.AbsoluteSpacing, 0)
    return f


QSS = f"""
* {{ color: {MIST}; outline: none; }}
QMainWindow, QDialog#Tutorial {{ background: {INK}; }}
QWidget#Root {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0B1030, stop:0.55 {INK}, stop:1 #0A0D1E); }}
QWidget#Sidebar {{ background: rgba(255,255,255,0.025); border-left: 1px solid {LINE}; }}
QLabel#Brand {{ color: {GOLD2}; }}
QLabel#BrandEn {{ color: {GOLD}; letter-spacing: 3px; font-size: 10px; }}
QPushButton#Nav {{ text-align: right; padding: 11px 16px; border: none; border-radius: 12px; color: {MUTED}; font-size: 14px; background: transparent; }}
QPushButton#Nav:hover {{ background: rgba(255,255,255,0.05); color: {MIST}; }}
QPushButton#Nav:checked {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {GOLD}, stop:1 {GOLD2}); color: #1A1204; font-weight: bold; }}
QLabel#PageTitle {{ color: {MIST}; }}
QLabel#Muted, QLabel[muted="true"] {{ color: {MUTED}; }}
QLabel#Hint {{ color: {MUTED}; font-size: 12px; }}
QFrame#Card {{ background: rgba(255,255,255,0.035); border: 1px solid {LINE}; border-radius: 18px; }}
QFrame#CardGold {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(231,185,100,0.13), stop:1 rgba(255,255,255,0.02)); border: 1px solid rgba(231,185,100,0.45); border-radius: 18px; }}
QLabel#CardTitle {{ color: {MIST}; font-weight: bold; font-size: 14px; }}
QLabel#Stat {{ color: {GOLD2}; font-size: 20px; font-weight: bold; }}
QPushButton {{ background: rgba(255,255,255,0.05); border: 1px solid {LINE}; border-radius: 12px; padding: 9px 16px; font-size: 13px; }}
QPushButton:hover {{ border-color: {GOLD}; background: rgba(255,255,255,0.08); }}
QPushButton:pressed {{ background: rgba(255,255,255,0.12); }}
QPushButton:disabled {{ color: #5D6488; border-color: #1A2040; }}
QPushButton#Primary {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {GOLD2}, stop:1 {GOLD}); color: #1A1204; border: none; font-weight: bold; }}
QPushButton#Primary:hover {{ background: {GOLD2}; }}
QPushButton#Danger {{ color: {ERR}; border-color: rgba(255,122,107,0.45); background: rgba(255,122,107,0.08); }}
QPushButton#Seg {{ padding: 14px 18px; border-radius: 14px; font-size: 14px; }}
QPushButton#Seg:checked {{ background: rgba(231,185,100,0.16); border: 1px solid {GOLD}; color: {GOLD2}; font-weight: bold; }}
QPushButton#Chip {{ padding: 5px 12px; border-radius: 13px; font-size: 12px; }}
QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QKeySequenceEdit, QFontComboBox {{
  background: rgba(0,0,0,0.28); border: 1px solid {LINE}; border-radius: 10px; padding: 7px 10px; min-height: 20px; selection-background-color: {GOLD}; selection-color: #1A1204; }}
QComboBox:hover, QLineEdit:focus, QKeySequenceEdit:focus {{ border-color: {GOLD}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{ background: {PANEL}; border: 1px solid {LINE}; selection-background-color: rgba(231,185,100,0.25); selection-color: {MIST}; }}
QCheckBox {{ spacing: 10px; font-size: 13px; }}
QCheckBox::indicator {{ width: 40px; height: 22px; border-radius: 11px; background: rgba(255,255,255,0.14); }}
QCheckBox::indicator:checked {{ background: {GOLD}; }}
QSlider::groove:horizontal {{ height: 6px; background: rgba(255,255,255,0.12); border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {GOLD}; border-radius: 3px; }}
QSlider::add-page:horizontal {{ background: rgba(255,255,255,0.12); border-radius: 3px; }}
QSlider::handle:horizontal {{ background: #FFFFFF; width: 16px; height: 16px; margin: -6px 0; border-radius: 8px; }}
QTabWidget::pane {{ border: none; }}
QTabBar::tab {{ background: transparent; color: {MUTED}; padding: 10px 18px; border-bottom: 2px solid transparent; font-size: 13px; }}
QTabBar::tab:selected {{ color: {GOLD2}; border-bottom: 2px solid {GOLD}; }}
QTableWidget, QListWidget {{ background: rgba(255,255,255,0.025); border: 1px solid {LINE}; border-radius: 14px; gridline-color: {LINE}; alternate-background-color: rgba(255,255,255,0.02); }}
QListWidget::item {{ padding: 10px; border-radius: 8px; }}
QListWidget::indicator {{ width: 18px; height: 18px; border-radius: 5px; border: 1px solid {LINE}; background: rgba(255,255,255,0.08); }}
QListWidget::indicator:checked {{ background: {GOLD}; border-color: {GOLD}; image: none; }}
QListWidget::item:selected, QTableWidget::item:selected {{ background: rgba(231,185,100,0.18); color: {MIST}; }}
QHeaderView::section {{ background: {PANEL}; color: {MUTED}; border: none; border-bottom: 1px solid {LINE}; padding: 8px; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar::handle:vertical {{ background: rgba(255,255,255,0.14); border-radius: 5px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QToolTip {{ background: {PANEL}; color: {MIST}; border: 1px solid {LINE}; padding: 6px; }}
QMenu {{ background: {PANEL}; border: 1px solid {LINE}; padding: 6px; }}
QMenu::item {{ padding: 8px 18px; border-radius: 6px; }}
QMenu::item:selected {{ background: rgba(231,185,100,0.2); }}
QMessageBox {{ background: {DEEP}; }}
QFrame#TplCard {{ background: rgba(255,255,255,0.035); border: 1px solid {LINE}; border-radius: 16px; }}
QFrame#TplCard:hover {{ border-color: rgba(231,185,100,0.6); background: rgba(255,255,255,0.06); }}
QFrame#TplCard[sel="true"] {{ border: 2px solid {GOLD}; background: rgba(231,185,100,0.10); }}
QLabel#Badge {{ color: #1A1204; background: {GOLD}; border-radius: 8px; padding: 1px 8px; font-size: 11px; font-weight: bold; }}
QPushButton#FontBtn {{ background: rgba(0,0,0,0.22); border: 1px solid {LINE}; border-radius: 14px; padding: 0; }}
QPushButton#FontBtn:hover {{ border-color: rgba(231,185,100,0.6); }}
QPushButton#FontBtn:checked {{ border: 2px solid {GOLD}; background: rgba(231,185,100,0.12); }}
QPushButton#Opt {{ padding: 8px 12px; border-radius: 11px; font-size: 13px; }}
QPushButton#Opt:checked {{ background: rgba(231,185,100,0.16); border: 1px solid {GOLD}; color: {GOLD2}; font-weight: bold; }}
QFrame#LayerBox {{ background: rgba(0,0,0,0.18); border: 1px solid {LINE}; border-radius: 14px; }}
QPushButton#Nav {{ padding: 8px 12px; }}
"""


def apply(app) -> None:
    load_fonts()
    app.setLayoutDirection(Qt.RightToLeft)
    app.setFont(ui_font(10))
    app.setStyleSheet(QSS)
