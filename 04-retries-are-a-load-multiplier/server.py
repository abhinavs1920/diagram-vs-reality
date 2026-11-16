#!/usr/bin/env python3
"""EP04 toy server: healthy, then a 10s brown-out window (slow + 50% 500s), then healthy.
Counts every request it sees per second into hits.csv."""
import http.server, threading, time, random, csv, sys

START = time.monotonic()
open('server_start.txt','w').write(str(START))
BROWN_START, BROWN_END = 8.0, 18.0
lock = threading.Lock()
hits = {}  # second -> count

def record_hit():
    s = int(time.monotonic() - START)
    with lock:
        hits[s] = hits.get(s, 0) + 1

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        record_hit()
        t = time.monotonic() - START
        if BROWN_START <= t < BROWN_END:
            time.sleep(1.5)  # sick dependency
            if random.random() < 0.5:
                self.send_response(500); self.end_headers(); self.wfile.write(b"sick")
                return
        else:
            time.sleep(0.05)  # healthy
        self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
    def log_message(self, *a): pass

class S(http.server.ThreadingHTTPServer):
    daemon_threads = True
    def handle_error(self, request, client_address): pass  # client abandoned conn during brown-out

srv = S(("127.0.0.1", 8404), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
time.sleep(float(sys.argv[1]) if len(sys.argv) > 1 else 26)
with open(sys.argv[2], "w", newline="") as f:
    w = csv.writer(f); w.writerow(["second", "requests"])
    for s in sorted(hits): w.writerow([s, hits[s]])
print("total requests seen:", sum(hits.values()))
