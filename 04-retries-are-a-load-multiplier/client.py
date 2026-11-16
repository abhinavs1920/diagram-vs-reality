#!/usr/bin/env python3
"""EP04 client v2. Three arms, same load shape: 20 workers, 25s, 100ms think time.
aggressive: 0.6s attempt timeout, 1 try + 5 immediate retries (no backoff, no jitter)
patient:    2.0s attempt timeout, single attempt, no retries
budgeted:   2.0s total deadline, at most 1 retry, jittered 200-400ms backoff
Every logical call records (ok, latency, attempts, t_start, t_end); brown cohort = t_start in [8,18).
"""
import http.client, threading, time, random, sys, statistics

MODE = sys.argv[1]
DURATION = 25.0
WORKERS = 20
THINK = 0.1
START = float(open('server_start.txt').read())
results = []  # (ok, latency, attempts, t_start, t_end)
rlock = threading.Lock()

def one_attempt(timeout_s):
    c = http.client.HTTPConnection("127.0.0.1", 8404, timeout=timeout_s)
    t0 = time.monotonic()
    try:
        c.request("GET", "/work")
        r = c.getresponse(); r.read()
        return r.status == 200, time.monotonic() - t0
    except Exception:
        return False, time.monotonic() - t0
    finally:
        c.close()

def call_aggressive():
    attempts = 0
    for _ in range(6):
        attempts += 1
        ok, _ = one_attempt(0.6)
        if ok:
            return True, attempts
    return False, attempts

def call_patient():
    ok, _ = one_attempt(2.0)
    return ok, 1

def call_budgeted():
    t0 = time.monotonic()
    attempts = 0
    for i in range(2):
        remaining = 2.0 - (time.monotonic() - t0)
        if remaining <= 0.05:
            break
        attempts += 1
        ok, _ = one_attempt(remaining)
        if ok:
            return True, attempts
        if i == 0:
            time.sleep(random.uniform(0.2, 0.4))
    return False, attempts

def worker(end):
    fn = {"aggressive": call_aggressive, "patient": call_patient, "budgeted": call_budgeted}[MODE]
    while time.monotonic() < end:
        ts = time.monotonic() - START
        ok, attempts = fn()
        te = time.monotonic() - START
        with rlock:
            results.append((ok, te - ts, attempts, ts, te))
        time.sleep(THINK)

end = time.monotonic() + DURATION
threads = [threading.Thread(target=worker, args=(end,)) for _ in range(WORKERS)]
for t in threads: t.start()
for t in threads: t.join()

brown = [r for r in results if 8.0 <= r[3] < 18.0]
b_ok = sum(1 for r in brown if r[0])
b_req = sum(r[2] for r in brown)
blats = sorted(r[1] for r in brown)
all_lats = sorted(r[1] for r in results)
print(f"mode={MODE}")
print(f"logical calls={len(results)} succeeded={sum(1 for r in results if r[0])} failed={sum(1 for r in results if not r[0])}")
print(f"median latency={statistics.median(all_lats)*1000:.0f}ms")
print(f"brown cohort (calls STARTED in window): calls={len(brown)} succeeded={b_ok} ({(b_ok/len(brown)*100 if brown else 0):.1f}%) requests={b_req} req/call={(b_req/len(brown) if brown else 0):.1f} p95={((blats[int(len(blats)*0.95)]*1000) if blats else 0):.0f}ms")
if MODE == "aggressive":
    succ = [r for r in brown if r[0]]
    ends = [f"{r[4]:.1f}" for r in succ]
    print(f"aggressive brown successes end-times: {','.join(ends) if ends else 'none'}")
    pre = [r for r in succ if r[4] < 18.0]
    print(f"brown successes that ended BEFORE t=18 (would contradict all-abandon): {len(pre)}")
