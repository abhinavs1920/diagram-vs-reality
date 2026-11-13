"""Toy server for episode 03. Python stdlib only.

Two endpoints:
  /silence - accepts the connection, sends nothing for 60 s.
  /drip    - sends a 100-byte body, one byte every 0.4 s (~40 s total).

Nothing is broken. The server answers every request correctly.
It just answers /drip slowly.
"""
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DRIP_BYTES = 100
DRIP_INTERVAL = 0.4  # seconds between bytes - always under the client's 5 s read timeout


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == "/silence":
            time.sleep(60)
            body = b"late answer\n"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/drip":
            self.send_response(200)
            self.send_header("Content-Length", str(DRIP_BYTES))
            self.end_headers()
            for _ in range(DRIP_BYTES):
                self.wfile.write(b"x")
                self.wfile.flush()
                time.sleep(DRIP_INTERVAL)
        else:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8734), Handler)
    print("listening on 127.0.0.1:8734 (/silence, /drip)")
    server.serve_forever()
