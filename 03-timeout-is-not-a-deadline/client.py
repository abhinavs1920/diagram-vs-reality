"""Client for episode 03. Python stdlib only.

Hypothesis (written before the run):
  "The client sets timeout=5, so no call can take longer than about 5 seconds."

Three cases, 5 trials each:
  A. /silence  + timeout=5           -> server is silent; expect the timeout to fire.
  B. /drip     + timeout=5           -> server dribbles bytes; what happens?
  C. /drip     + total deadline (5s) -> same server, but the caller budgets the
                                        whole operation and gives up at 5 s.

http.client passes `timeout` to the socket, where it is a per-operation
timeout (per connect, per read), not a budget for the whole call.
"""
import http.client
import json
import select
import socket
import time

HOST, PORT = "127.0.0.1", 8734
TIMEOUT = 5
TRIALS = 5


def case_silence():
    start = time.monotonic()
    try:
        conn = http.client.HTTPConnection(HOST, PORT, timeout=TIMEOUT)
        conn.request("GET", "/silence")
        resp = conn.getresponse()
        resp.read()
        outcome = "completed"
    except (TimeoutError, socket.timeout, OSError) as e:
        outcome = f"raised {type(e).__name__}"
    finally:
        conn.close()
    return time.monotonic() - start, outcome


def case_drip():
    start = time.monotonic()
    try:
        conn = http.client.HTTPConnection(HOST, PORT, timeout=TIMEOUT)
        conn.request("GET", "/drip")
        resp = conn.getresponse()
        n = len(resp.read())
        outcome = f"completed, {n} bytes"
    except (TimeoutError, socket.timeout, OSError) as e:
        outcome = f"raised {type(e).__name__}"
    finally:
        conn.close()
    return time.monotonic() - start, outcome


def case_deadline():
    """Same /drip server, but the caller enforces a total budget itself."""
    deadline = time.monotonic() + TIMEOUT
    start = time.monotonic()
    received = 0
    outcome = "completed"
    sock = socket.create_connection((HOST, PORT), timeout=max(0.1, deadline - time.monotonic()))
    try:
        sock.sendall(b"GET /drip HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n")
        buf = b""
        while b"\r\n\r\n" not in buf:  # headers first
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                outcome = "gave up: total deadline hit (in headers)"
                break
            r, _, _ = select.select([sock], [], [], remaining)
            if not r:
                outcome = "gave up: total deadline hit (in headers)"
                break
            buf += sock.recv(4096)
        body_start = buf.find(b"\r\n\r\n") + 4
        received = len(buf) - body_start if body_start >= 4 else 0
        while outcome == "completed":
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                outcome = "gave up: total deadline hit (body)"
                break
            r, _, _ = select.select([sock], [], [], remaining)
            if not r:
                outcome = "gave up: total deadline hit (body)"
                break
            chunk = sock.recv(4096)
            if not chunk:
                break  # server finished in time
            received += len(chunk)
    finally:
        sock.close()
    return time.monotonic() - start, f"{outcome}, {received} bytes read"


def run(label, fn):
    # trials run concurrently; the server is threaded and the per-call load is
    # one byte per 0.4 s, so calls do not meaningfully affect each other
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=TRIALS) as pool:
        results = list(pool.map(lambda _: fn(), range(TRIALS)))
    rows = []
    for t, (elapsed, outcome) in enumerate(results, 1):
        rows.append({"trial": t, "elapsed_s": round(elapsed, 2), "outcome": outcome})
        print(f"  {label} trial {t}: {elapsed:6.2f}s  {outcome}", flush=True)
    return rows


if __name__ == "__main__":
    print(f"A,B: http.client timeout={TIMEOUT} (per blocking op); C: raw socket, caller deadline {TIMEOUT}s; /drip dribbles 1 byte / 0.4s")
    results = {
        "A_silence_timeout5": run("A silence ", case_silence),
        "B_drip_timeout5": run("B drip    ", case_drip),
        "C_drip_deadline5": run("C deadline", case_deadline),
    }
    with open("results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("wrote results.json")
