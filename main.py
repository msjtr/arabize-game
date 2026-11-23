"""عرب لعبتك | Arabize Game — entry point.

Usage:
  python main.py              start normally
  python main.py --minimized  start in the system tray
  python main.py --tutorial   show the tutorial again
"""
from __future__ import annotations

import os
import sys


def main() -> int:
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    from PySide6.QtCore import QLockFile, QDir
    from PySide6.QtWidgets import QApplication, QMessageBox

    from arabize.app import Controller
    from arabize.config import APP_NAME_EN, data_dir
    from arabize.ui import theme
    from arabize.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME_EN)
    app.setOrganizationName("ArabizeGame")
    app.setQuitOnLastWindowClosed(False)
    theme.apply(app)

    lock = QLockFile(str(data_dir() / "running.lock"))
    if not lock.tryLock(100):
        QMessageBox.information(None, "عرب لعبتك", "البرنامج يعمل بالفعل — تجده بجانب الساعة في شريط المهام.")
        return 0

    from arabize import logs
    logs.setup()
    ctrl = Controller()
    win = MainWindow(ctrl)
    ctrl.window = win
    ctrl.setup_tray()
    bad = ctrl.apply_hotkeys()
    if bad and len(bad) < 5:
        ctrl.toast("بعض الاختصارات لم تُفعّل — راجع صفحة الاختصارات", err=True)
    if "--minimized" not in sys.argv:
        win.show()
    if ctrl.settings.data.get("first_run") or "--tutorial" in sys.argv:
        ctrl.show_tutorial()
    app.aboutToQuit.connect(lambda: (ctrl.quit() if not ctrl.quitting else None))
    if not ctrl.tray_available():
        app.setQuitOnLastWindowClosed(True)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
