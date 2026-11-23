"""Translation memory, manual corrections and history in one SQLite file."""
from __future__ import annotations

import hashlib
import sqlite3
import threading
import time
from pathlib import Path

from .config import data_dir
from .textproc import normalize_key

SCHEMA = """
CREATE TABLE IF NOT EXISTS translations(
  key TEXT PRIMARY KEY, src_text TEXT, src_lang TEXT, tgt_lang TEXT, style TEXT,
  engine TEXT, translation TEXT, created REAL, used REAL, hits INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS overrides(
  norm TEXT, tgt_lang TEXT, src_text TEXT, translation TEXT, updated REAL,
  PRIMARY KEY(norm, tgt_lang));
CREATE TABLE IF NOT EXISTS history(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, game TEXT, src_text TEXT, translation TEXT,
  engine TEXT, src_lang TEXT, tgt_lang TEXT);
CREATE INDEX IF NOT EXISTS history_ts ON history(ts);
CREATE INDEX IF NOT EXISTS translations_used ON translations(used);
"""


class Store:
    MAX_TRANSLATIONS = 50_000
    MAX_HISTORY = 5_000

    def __init__(self, path: Path | None = None):
        self.path = path or (data_dir() / "memory.sqlite3")
        self._lock = threading.RLock()
        self.db = sqlite3.connect(str(self.path), check_same_thread=False, timeout=10)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")
        self.db.executescript(SCHEMA)
        self.db.commit()

    @staticmethod
    def make_key(text: str, src: str, tgt: str, style: str) -> str:
        raw = f"{normalize_key(text)}\x1f{src}\x1f{tgt}\x1f{style}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()

    # ---------- translation memory ----------
    def lookup(self, text: str, src: str, tgt: str, style: str) -> tuple[str, str] | None:
        """Manual correction first, then cached engine output. Returns (translation, source)."""
        with self._lock:
            row = self.db.execute("SELECT translation FROM overrides WHERE norm=? AND tgt_lang=?",
                                  (normalize_key(text), tgt)).fetchone()
            if row:
                return row[0], "manual"
            key = self.make_key(text, src, tgt, style)
            row = self.db.execute("SELECT translation, engine FROM translations WHERE key=?", (key,)).fetchone()
            if row:
                self.db.execute("UPDATE translations SET used=?, hits=hits+1 WHERE key=?", (time.time(), key))
                self.db.commit()
                return row[0], "cache:" + row[1]
            return None

    def put(self, text: str, src: str, tgt: str, style: str, engine: str, translation: str) -> None:
        with self._lock:
            now = time.time()
            self.db.execute(
                "INSERT OR REPLACE INTO translations(key,src_text,src_lang,tgt_lang,style,engine,translation,created,used,hits)"
                " VALUES(?,?,?,?,?,?,?,?,?,0)",
                (self.make_key(text, src, tgt, style), text, src, tgt, style, engine, translation, now, now))
            self.db.commit()
            self._trim("translations", "used", self.MAX_TRANSLATIONS)

    def set_override(self, text: str, tgt: str, translation: str) -> None:
        with self._lock:
            self.db.execute("INSERT OR REPLACE INTO overrides VALUES(?,?,?,?,?)",
                            (normalize_key(text), tgt, text, translation, time.time()))
            self.db.commit()

    def clear_memory(self) -> int:
        with self._lock:
            n = self.db.execute("SELECT COUNT(*) FROM translations").fetchone()[0]
            self.db.execute("DELETE FROM translations")
            self.db.commit()
            return n

    def stats(self) -> dict:
        with self._lock:
            q = lambda sql: self.db.execute(sql).fetchone()[0]
            return {"memory": q("SELECT COUNT(*) FROM translations"), "overrides": q("SELECT COUNT(*) FROM overrides"),
                    "history": q("SELECT COUNT(*) FROM history"), "hits": q("SELECT COALESCE(SUM(hits),0) FROM translations")}

    # ---------- history ----------
    def add_history(self, game: str, src_text: str, translation: str, engine: str, src: str, tgt: str) -> int:
        with self._lock:
            cur = self.db.execute("INSERT INTO history(ts,game,src_text,translation,engine,src_lang,tgt_lang) VALUES(?,?,?,?,?,?,?)",
                                  (time.time(), game, src_text, translation, engine, src, tgt))
            self.db.commit()
            self._trim("history", "ts", self.MAX_HISTORY)
            return cur.lastrowid

    def history(self, search: str = "", limit: int = 500) -> list[dict]:
        with self._lock:
            sql = "SELECT id,ts,game,src_text,translation,engine,src_lang,tgt_lang FROM history"
            args: tuple = ()
            if search:
                sql += " WHERE src_text LIKE ? OR translation LIKE ? OR game LIKE ?"
                like = f"%{search}%"
                args = (like, like, like)
            sql += " ORDER BY ts DESC LIMIT ?"
            rows = self.db.execute(sql, args + (limit,)).fetchall()
        keys = ["id", "ts", "game", "src_text", "translation", "engine", "src_lang", "tgt_lang"]
        return [dict(zip(keys, r)) for r in rows]

    def edit_history(self, hid: int, translation: str) -> None:
        """A manual edit fixes the history row and teaches the translation memory."""
        with self._lock:
            row = self.db.execute("SELECT src_text, tgt_lang FROM history WHERE id=?", (hid,)).fetchone()
            if not row:
                return
            self.db.execute("UPDATE history SET translation=?, engine='manual' WHERE id=?", (translation, hid))
            self.db.commit()
        self.set_override(row[0], row[1], translation)

    def clear_history(self) -> None:
        with self._lock:
            self.db.execute("DELETE FROM history")
            self.db.commit()

    def _trim(self, table: str, col: str, keep: int) -> None:
        n = self.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        if n > keep * 1.1:
            self.db.execute(f"DELETE FROM {table} WHERE rowid IN (SELECT rowid FROM {table} ORDER BY {col} ASC LIMIT ?)",
                            (n - keep,))
            self.db.commit()

    def close(self) -> None:
        with self._lock:
            self.db.close()
