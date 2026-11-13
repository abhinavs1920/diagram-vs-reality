# 03 - A timeout is not a deadline

The belief: set `timeout=5` on the HTTP client, and no call can take longer than about 5 seconds.

## Setup

Python stdlib only. No installs, no network beyond localhost. Tested client: Python 3.10 stdlib `http.client` - not requests.

- `server.py` - a toy HTTP server with two endpoints. `/silence` accepts the connection and says nothing for 60 s. `/drip` answers correctly, but slowly: a 100-byte body, one byte every 0.4 s.
- `client.py` - three cases, 5 trials each, all on `127.0.0.1`:
  - **A** - GET `/silence` with `timeout=5`.
  - **B** - GET `/drip` with the same `timeout=5`.
  - **C** - GET `/drip` again, this time over a raw socket (no http.client): the caller budgets the whole operation itself and gives up at 5 s.

Per the http.client docs, the `timeout` parameter applies to blocking operations (https://docs.python.org/3/library/http.client.html#http.client.HTTPConnection) - per connect, per read - not to the call as a whole. The requests library is not used here; its timeout docs state the same semantics more plainly and are cited as the analogous reference: its read timeout is "the number of seconds that the client will wait between bytes sent from the server" (https://requests.readthedocs.io/en/latest/user/advanced/#timeouts).

Case C's deadline is enforced by the caller on a raw socket: the remaining budget is recomputed before connect and before every read (`select` with the remaining time), and the call is abandoned when the budget is spent. It checks between reads; it is not a hard interruption. Anything blocked outside those reads (a DNS lookup, or a TLS handshake inside one blocking call) would not be preempted by this pattern. No DNS was involved here (127.0.0.1 literal).

## Expectation (written before the run)

A raises around 5 s. B runs to completion far past 5 s without any error, because every byte arrives inside its own 5 s budget. C returns at about 5 s.

## Result

| case | trials | elapsed per call | outcome |
|------|--------|------------------|---------|
| A - silent server, timeout=5 | 5 | 5.01 s | raised TimeoutError, every time |
| B - dribbling server, timeout=5 | 5 | 39.67 s | completed, all 100 bytes, no error |
| C - dribbling server, own 5 s deadline | 5 | 5.00 s | gave up at the deadline, 13 bytes read |

The same `timeout=5` that caught a silent server in 5 seconds let a slow one run for 8x that. The timeout never fired in B because it was never exceeded - each single read got its byte in 0.4 s.

Full output: `run1-console.txt`. Numbers: `results.json` (elapsed times rounded to 2 dp; a full-precision probe of one trial per case is in `precision-probe.json`: A 5.0068 s, B 39.6686 s, C 5.0005 s; repeated trials agree to ~10 ms because the 0.4 s server sleeps dominate and localhost scheduling is stable). The chart and a terminal screenshot of the run (`03-timeout-results.png`, `03-terminal.png`) are pending upload to this folder; they are attached to the episode post in the meantime.

## Limits

- One machine, localhost, one client library (Python stdlib http.client). Different clients have different semantics; what matters is which one yours has.
- The server answers correctly the whole time. Nothing here says timeouts are useless - case A shows they catch exactly the failure they measure: silence.
- Case C is one way to enforce a real deadline. It is not the only way; some frameworks offer an overall-timeout option.
- The dribble is deliberate and dramatic so the effect is visible in a toy. Real servers do this by accident: slow proxies, streaming endpoints, chunked responses, backpressure.

## Credit

The everyday belief being tested is "timeout=5 means the call returns within 5 seconds". The docs that say otherwise are the http.client and requests references linked above. Testing one mechanism here, not anyone's whole body of work.
