# Diagram vs Reality 02: One request is not one round trip

A small experiment inspired by Hussein Nasser's article "Persistent Connections":
https://www.husseinnasser.com/2016/07/persistant-connections.html

His own about page lists his socials as @hnasr:
https://www.husseinnasser.com/p/about-hussein.html

## Reproduce

Requirements: Python 3.10+. No package installs or credentials. This episode
needs internet access - it makes real HTTPS requests to example.com.

    python run.py

The script resolves example.com once (DNS timed separately, excluded from all
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

## Limits

One host, one network, 5 runs. An observation, not a law. A toy test is a toy
test - run it yourself and compare.
