"""Local HTTP server that lets a browser extension push URLs into the app.

The "Send to Downie" browser extension POSTs {"url": "..."} to
http://127.0.0.1:<port>/add and the running app adds it to the queue.
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from PySide6.QtCore import QObject, Signal

# 浏览器扩展只会发一个小 JSON；限制体积避免任何本地页面用它做内存耗尽。
MAX_BODY_BYTES = 64 * 1024


def _is_fetchable_url(url: str) -> bool:
    """只接受 http/https 绝对地址。

    没有这个校验时，任何本地网页都能往队列里塞 ``file://`` / ``javascript:``
    之类的链接，交给 yt-dlp 处理是不可预期的输入。
    """
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


class _Handler(BaseHTTPRequestHandler):
    server_version = "DownieWin/1.0"

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("DownieWin browser server running".encode("utf-8"))

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/add":
            self.send_response(404)
            self._cors()
            self.end_headers()
            return
        try:
            length = int(self.headers.get("Content-Length", 0) or 0)
        except ValueError:
            length = 0
        if length < 0 or length > MAX_BODY_BYTES:
            self.send_response(413)
            self._cors()
            self.end_headers()
            return
        try:
            raw = self.rfile.read(length) if length else b"{}"
            data = json.loads(raw or b"{}")
            if not isinstance(data, dict):
                raise ValueError("payload 必须是 JSON 对象")
            url = (data.get("url") or "")
            url = url.strip() if isinstance(url, str) else ""
            if not _is_fetchable_url(url):
                self.send_response(400)
                self._cors()
                self.end_headers()
                self.wfile.write(b'{"ok":false,"error":"invalid url"}')
                return
            if callable(getattr(self.server, "on_add", None)):
                # Hand off to the Qt thread via the server's callback.
                self.server.on_add(url)
            self.send_response(200)
            self._cors()
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
        except Exception:
            self.send_response(400)
            self._cors()
            self.end_headers()

    def log_message(self, *args):  # silence default logging
        pass


class BrowserServer(QObject):
    """Runs the HTTP listener on a background thread.

    `on_add` is invoked with the received URL string; the caller should
    marshal it onto the GUI thread.
    """

    url_received = Signal(str)

    def __init__(self, port: int = 7654, parent=None) -> None:
        super().__init__(parent)
        self.port = port
        self._httpd = None
        self._thread = None

    def start(self) -> bool:
        try:
            self._httpd = ThreadingHTTPServer(("127.0.0.1", self.port), _Handler)
            self._httpd.on_add = lambda u: self.url_received.emit(u)
            self._thread = threading.Thread(
                target=self._httpd.serve_forever, daemon=True
            )
            self._thread.start()
            return True
        except OSError as exc:  # port in use etc.
            print(f"[browser-server] failed to start: {exc}")
            return False

    def stop(self) -> None:
        if self._httpd:
            try:
                self._httpd.shutdown()
                self._httpd.server_close()
            except Exception:
                pass
            self._httpd = None
        if self._thread is not None:
            # shutdown() 之后线程会在 serve_forever 返回时退出，join 一下避免
            # 重启服务时端口仍被上一个监听占用。
            try:
                self._thread.join(timeout=2)
            except RuntimeError:
                pass
            self._thread = None
