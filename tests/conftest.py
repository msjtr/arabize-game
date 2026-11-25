import json
import os
import sys
import tempfile
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("ARABIZE_HOME", tempfile.mkdtemp(prefix="arabize-test-"))

FAKE_AR = {"Press any button to continue your adventure.": "اضغط أي زر لمتابعة مغامرتك.",
           "Halt! Who goes there?": "قف! من هناك؟"}


class Fake(BaseHTTPRequestHandler):
    """Mimics the real response formats of Google, MyMemory, Anthropic and DeepL."""
    mode = {"google": "ok", "mymemory": "ok", "claude": "ok", "deepl": "ok"}
    calls = {"google": 0, "mymemory": 0, "claude": 0, "deepl": 0}

    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _fail(self, eng):
        m = Fake.mode[eng]
        if m == "500":
            self._send(500, {"error": "boom"}); return True
        if m == "401":
            self._send(401, {"error": "bad key"}); return True
        if m == "flaky":
            Fake.mode[eng] = "ok"; self._send(503, {"error": "busy"}); return True
        if m == "drop":
            self.connection.close(); return True
        if m == "slow":                     # a real server across the internet
            import time
            time.sleep(0.35)
        return False

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = dict(urllib.parse.parse_qsl(u.query))
        if u.path.startswith("/google"):
            Fake.calls["google"] += 1
            if self._fail("google"): return
            t = FAKE_AR.get(q["q"], "ع:" + q["q"])
            self._send(200, [[[t, q["q"], None, None, 10]], None, "en", None, None, None, 1.0, [], [["en"], None, [1.0], ["en"]]])
        elif u.path.startswith("/mymemory"):
            Fake.calls["mymemory"] += 1
            if self._fail("mymemory"): return
            t = FAKE_AR.get(q["q"], "م:" + q["q"])
            self._send(200, {"responseData": {"translatedText": t, "match": 0.9, "detectedLanguage": "en"},
                             "responseStatus": 200, "responseDetails": "", "matches": []})

    def do_POST(self):
        n = int(self.headers.get("content-length", 0))
        body = self.rfile.read(n)
        if self.path.startswith("/claude"):
            Fake.calls["claude"] += 1
            if self._fail("claude"): return
            assert self.headers.get("x-api-key") and self.headers.get("anthropic-version")
            req = json.loads(body)
            src = req["messages"][0]["content"].split("<source>\n")[1].split("\n</source>")[0]
            self._send(200, {"id": "msg_1", "type": "message", "role": "assistant", "model": req["model"],
                             "content": [{"type": "text", "text": f"<lang>en</lang><translation>{FAKE_AR.get(src, 'ذ:' + src)}</translation>"}],
                             "stop_reason": "end_turn", "usage": {"input_tokens": 10, "output_tokens": 10}})
        elif self.path.startswith("/deepl"):
            Fake.calls["deepl"] += 1
            if self._fail("deepl"): return
            q = dict(urllib.parse.parse_qsl(body.decode()))
            self._send(200, {"translations": [{"detected_source_language": "EN", "text": "د:" + q["text"]}]})


@pytest.fixture(scope="session")
def fake_server():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    yield base
    srv.shutdown()


@pytest.fixture
def env(tmp_path, fake_server):
    from arabize.config import Settings
    from arabize.cache import Store
    from arabize.engines import Manager
    for k in Fake.mode:
        Fake.mode[k] = "ok"; Fake.calls[k] = 0
    s = Settings(tmp_path / "s.json")
    st = Store(tmp_path / "m.sqlite3")
    m = Manager(s, st, sleep=lambda x: None)
    m.overrides_endpoint = {e: f"{fake_server}/{e}" for e in ("google", "mymemory", "claude", "deepl")}
    return s, st, m


@pytest.fixture
def env_ctrl(tmp_path):
    """A real controller on throw-away settings (no live translation started)."""
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from arabize.app import Controller
    from arabize.cache import Store
    from arabize.config import Settings
    c = Controller(Settings(tmp_path / "s.json"), Store(tmp_path / "m.sqlite3"))
    yield c
    c.game_timer.stop()
    c.overlay.clear(animate=False)
