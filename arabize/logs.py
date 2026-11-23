"""Error log: a small rotating file in the app folder, so a problem can be found and fixed later.

Nothing personal is written: no screenshots, no API keys. Translations are not logged either."""
from __future__ import annotations

import logging
import logging.handlers
import platform
import sys
import threading
from pathlib import Path

from .config import APP_VERSION, data_dir

log = logging.getLogger("arabize")
_ready = False


def log_dir() -> Path:
    d = data_dir() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def log_file() -> Path:
    return log_dir() / "arabize.log"


def setup() -> Path:
    """Start logging (idempotent): 1 MB per file, 3 old files kept. Also records crashes on any thread."""
    global _ready
    path = log_file()
    if _ready:
        return path
    h = logging.handlers.RotatingFileHandler(path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    log.addHandler(h)
    log.setLevel(logging.INFO)
    log.info("start %s | Python %s | %s %s", APP_VERSION, platform.python_version(), platform.system(), platform.version())

    prev = sys.excepthook

    def hook(t, v, tb):
        log.critical("unhandled error", exc_info=(t, v, tb))
        prev(t, v, tb)
    sys.excepthook = hook

    def thook(args):
        log.critical("unhandled error in thread %s", args.thread.name if args.thread else "?",
                     exc_info=(args.exc_type, args.exc_value, args.exc_traceback))
    threading.excepthook = thook
    _ready = True
    return path


def report(lines: int = 200) -> str:
    """The end of the log plus basic system facts, ready to copy into a bug report."""
    try:
        tail = log_file().read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]
    except OSError:
        tail = []
    head = [f"Arabize Game {APP_VERSION}", f"{platform.system()} {platform.release()} {platform.version()}",
            f"Python {platform.python_version()}", "-" * 40]
    return "\n".join(head + tail)
