# Diagram vs Reality 02: I nearly blamed the handshake

(The folder keeps the original slug - "one request is not one round trip" was the
hypothesis going in. What the runs actually showed is below.)

A small experiment inspired by Hussein Nasser's article "Persistent Connections":
https://www.husseinnasser.com/2016/07/persistant-connections.html

His own about page lists his socials as @hnasr:
https://www.husseinnasser.com/p/about-hussein.html

## Reproduce

Requirements: Python 3.10+. No package installs or credentials. This episode
needs internet access - it makes real HTTPS requests to example.com.

    python run.py              # original experiment, writes results.json
    python control_nodelay.py  # follow-up control, writes results_control.json

run.py resolves example.com once (DNS timed separately, excluded from all
timings), then runs 5 interleaved pairs: a cold request on a fresh connection,
and two sequential requests on one fresh connection. Every HTTP/1.1 response
is validated (status 200, Content-Length or chunked framing) before its time
is recorded. Results are written to results.json. The included results.json is
the recorded run from 12 Nov 2026 (IST), not a forecast - your timings will
differ with your network.

## Setup

Raw sockets + ssl, HTTP/1.1, host example.com, 5 paired runs, medians.
DNS resolved once up front and excluded. Each timing starts at its own t0:
handshake = TCP connect + TLS wrap; request = send to full validated response;
total = handshake + request.

## Expectation

The diagram: one HTTPS request = one round trip.

## Result (recorded run, medians)

- Cold request, fresh connection (Connection: close): 75.1 ms total
  (16.3 ms handshake + 58.2 ms request)
- Fresh keep-alive connection, first request: 76.7 ms total
  (19.4 ms handshake) - consistent with the cold case
- Second request on that same connection: 12.6 ms

The measured handshake does not explain the whole gap. The remaining
difference was not isolated; no cause is claimed here.

Update (same evening): the follow-up control below shows the client
socket's TCP_NODELAY setting accounts for the remaining difference in this
setup.

## Limits

One host, one network, 5 runs. An observation, not a law. A toy test is a toy
test - run it yourself and compare.

## Follow-up (same evening): TCP_NODELAY control

The original run above is kept as the dated baseline. A matched control
(control_nodelay.py, results in results_control.json) re-ran the same paired
design with one change: TCP_NODELAY set on the client socket before connect.

Recorded control run (12 Nov 2026, ~21:51 IST, medians, 5 pairs per variant):

- Default socket (same as the original run): cold request 52.4 ms,
  cold total 60.0 ms; reused-connection request 9.8 ms
- TCP_NODELAY: cold request 9.2 ms, cold total 16.9 ms;
  reused-connection request 9.0 ms

What changed: the client socket setting alone moved the fresh-request time by
~43 ms in this setup. With it set, the first request on a fresh connection
took about the same time as one on a reused connection (9.2 vs 9.0 ms), and
the remaining cost of a fresh connection was the handshake itself
(16.9 total - 9.2 request = ~7.7 ms, matching the measured 7.7 ms handshake).

What did not change: the exact mechanism behind the setting's effect (for
example, interaction with delayed acknowledgements) was not packet-traced
here. This is reported as the controlled effect of the socket setting, not a
proven cause chain.

TLS version on these connections: TLSv1.3.

Credit note: the episode concept (persistent connections) is from Hussein
Nasser's article linked above. The TCP_NODELAY control and its result are
this repo's own follow-up, not from that article.
