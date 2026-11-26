# 04 - retries are a load multiplier

Diagram said: if the call fails, just retry, it will go through eventually. Reality: fast instant retries multiplied load on the already-sick server six times per call, and not one of those retries succeeded while the server was still sick.

## Setup

Pure Python 3 standard library, no installs, localhost only.

- `server.py` - threaded HTTP server. Healthy: 50ms 200s. For a 10-second brown-out (seconds 8-18): 1.5s latency, 50% 500s. Logs every request per second to a CSV.
- `client.py aggressive` - 0.6s attempt timeout, 1 try + 5 immediate retries, no backoff, no jitter.
- `client.py patient` - 2.0s attempt timeout, single attempt, no retries.
- `client.py budgeted` - 2.0s total deadline per call, at most 1 retry, jittered 200-400ms backoff.
- Same 20 workers, same 25s, same 100ms think time in all arms (closed loop). Client and server clocks synced via `server_start.txt`; a call belongs to the brown cohort if it STARTED in [8s, 18s).

```
python3 server.py 27 hits.csv & sleep 1
python3 client.py aggressive   # then: patient, then: budgeted
```

## Expectation

Retries help: some failed calls go through on a later attempt, so the retrying client should see a higher success rate during the brown-out.

## Result (two full runs, same direction; run 2 shown)

| policy | calls started in brown-out | succeeded | requests per call | p95 latency |
|---|---|---|---|---|
| 0.6s timeout, 5 instant retries | 60 | 33.3% | 6.0 | 3613ms |
| 2s timeout, no retries | 140 | 47.1% | 1.0 | 1503ms |
| 2s deadline, 1 jittered retry | 120 | 62.5% | 1.5 | 2003ms |

Verified claim: every one of the aggressive policy's brown-cohort successes ended at t=18.5-18.6 - AFTER the brown-out ended at t=18. Zero succeeded while the server was still sick (checked in both runs). The 0.6s timeout abandoned every attempt before the 1.5s-slow server could answer, and each abandonment spawned another request.

Healthy phases were identical across arms (51ms median).

## Limits

Localhost toy. One failure shape (slow + 50% error). Closed-loop clients, so policies produce different numbers of logical calls (latency shapes throughput) - compare per-call ratios and percentages, not absolute call counts. The three arms differ in timeout AND retry count by design: this compares whole policies, and the aggressive-vs-patient pair is the "retry faster vs wait longer" choice, not a single-variable isolation of retries. Two runs agree on direction; treat the exact numbers as this toy's numbers, not production values.

Credit: Hussein Nasser's point that a retry looks benign in a single client until the clients scale (https://www.linkedin.com/posts/hnaser_retrying-a-request-may-look-benign-when-writing-activity-7337847492807376896-Cxa1). Testing one mechanism, not debunking anyone.

Images: `04-retry-load.png` (requests per second per policy, from the hits CSVs) and `04-policy-results.png` (the table above, from `run_*2.txt`).
