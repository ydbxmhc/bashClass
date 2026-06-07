#!/usr/bin/env python
"""Minimal HTTP test server for the `probe` tool tests.

Binds to 127.0.0.1 on an ephemeral port (loopback only -- never exposed).
Writes the chosen port to the file named by argv[1] so the bash test can
discover it, then serves until killed.

Routes:
  GET  /              -> 200 text body "hello from test server"
  GET  /json          -> 200 application/json {"ok": true, "n": 42}
  GET  /status/<n>    -> responds with status code <n>, short text body
  GET  /redirect      -> 302 Location: /target
  GET  /target        -> 200 text body "redirected ok"
  GET  /headers       -> 200 body echoing the request headers it received
  POST /echo          -> 200 body echoing the posted request body
  (anything else)     -> 404
"""
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    # Silence the default stderr request logging -- keeps test output clean.
    def log_message(self, *args):
        pass

    def _send(self, code, body=b"", ctype="text/plain", extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        for key, val in (extra or {}).items():
            self.send_header(key, val)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            self._send(200, b"hello from test server")
        elif self.path == "/json":
            self._send(200, b'{"ok": true, "n": 42}', "application/json")
        elif self.path.startswith("/status/"):
            try:
                code = int(self.path.rsplit("/", 1)[1])
            except ValueError:
                code = 400
            self._send(code, ("status %d" % code).encode())
        elif self.path == "/redirect":
            self._send(302, b"", extra={"Location": "/target"})
        elif self.path == "/target":
            self._send(200, b"redirected ok")
        elif self.path == "/headers":
            lines = ["%s: %s" % (k, v) for k, v in self.headers.items()]
            self._send(200, ("\n".join(lines)).encode())
        else:
            self._send(404, b"not found")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        if self.path == "/echo":
            self._send(200, body)
        else:
            self._send(404, b"not found")


def main():
    port_file = sys.argv[1] if len(sys.argv) > 1 else None
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    actual_port = server.server_address[1]
    if port_file:
        with open(port_file, "w") as fh:
            fh.write(str(actual_port))
    else:
        sys.stdout.write(str(actual_port) + "\n")
        sys.stdout.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
