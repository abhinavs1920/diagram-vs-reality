# Diagram vs Reality

The diagram says one thing. The system does another. This repo is where I test the difference.

Each episode takes one claim, mechanism, or mental model - from a talk, a doc, or a belief everyone repeats - and checks it against a small experiment you can run yourself.

## How every episode works

- Runnable with nothing but a language runtime. No installs, no credentials, no network beyond localhost unless the episode says so.
- The hypothesis is written down before the run. Results get published whether they match or not.
- The source that inspired the episode is always credited. Testing one mechanism is not "debunking" anyone.
- Limits are stated in plain words. A toy test is a toy test.

## Episodes

| # | Episode | What it tests |
|---|---------|---------------|
| 01 | [Abort is not a rollback](01-abort-is-not-a-rollback/) | Does aborting fetch cancel the server-side write? |
| 02 | [I nearly blamed the handshake](02-one-request-is-not-one-round-trip/) | Is an HTTPS request just one round trip - and was it even the handshake? |

## Episode 01 in one paragraph

Local Node fetch to a Python HTTP handler writing to SQLite. 100 ms abort timer, 400 ms handler delay, no cancellation propagation in the handler. The client aborted at ~101 ms; the handler committed the order anyway at ~426 ms. An unkeyed retry created a second order; a retry with the same idempotency key did not (SQLite UNIQUE constraint). 5 trials per case, same result every time. Inspired by Hussein Nasser's "why it is very hard to cancel an HTTP request" (2021) - this tests one small mechanism, not his whole video.

## Episode 02 in one paragraph

Real HTTPS requests to example.com with raw Python sockets, HTTP/1.1, TLS 1.3, DNS excluded, 5 paired runs per variant on one cloud machine. A fresh connection's first full response took ~60 ms with a default socket; with TCP_NODELAY set on the client socket the same took ~17 ms; a request on an already-open connection took ~9-10 ms; measured TCP + TLS setup was ~7-8 ms. The client socket's TCP_NODELAY setting accounted for the remaining difference in this setup; the packet-level mechanism was not traced. Concept credit: Hussein Nasser's "Persistent Connections" (the TCP_NODELAY control is this repo's own follow-up, not from that article). One host, one network - an observation, not a law.

## Disagree? Good.

If you ran one of these and got a different result, open an issue with your setup and your trace. That's the whole reason for doing this in public.

## License

MIT. Take the code, run it, break it, tell me what you found.
