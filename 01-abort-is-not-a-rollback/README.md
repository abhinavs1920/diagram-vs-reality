# Diagram vs Reality 01: Abort is not a rollback

A deliberately small local HTTP experiment inspired by Hussein Nasser's video, "why it is very hard to cancel an HTTP request" (2 June 2021):
https://www.youtube.com/watch?v=WmPKzFYKijM

Author's own about page identifies his socials as @hnasr:
https://www.husseinnasser.com/p/about-hussein.html

## Reproduce

Requirements: Python 3.10+ and Node 18+ (built-in fetch). No package installs, credentials or internet needed for the experiment.

    python run.py

The script binds only to 127.0.0.1 on a temporary port, creates a fresh local `orders.sqlite`, runs 20 bounded trial scenarios, checks assertions, saves `results.json`, then stops the server. It DELETES an existing `orders.sqlite` in this folder on each run. Run in a dedicated directory. Included results are from the recorded original run, not a forecast of exact timings on your machine. Re-running replaces them.

## What it does

- A real Node fetch request sends a synthetic order to a local Python HTTP handler.
- The handler waits 400ms before writing to SQLite. It deliberately implements no disconnect or cancellation propagation.
- In aborted cases, AbortController is triggered by a 100ms client timer.
- Each of four scenarios runs five times: no abort, abort only, abort followed by one unkeyed retry, abort followed by one same-key retry.
- Only the same-key case uses the SQLite UNIQUE idempotency-key constraint.
- The server finishes after the client abort and sees a broken/closed connection when writing its response in the representative trial.
- `results.json` contains every trial count and event trace. The two summary visuals (being added to this folder) summarize these measured records; they are not invented sample output.

## Expected hypothesis recorded before running

When a handler does not propagate cancellation, aborting fetch will not cancel its write. Retrying that write without deduplication can create another order. A same-key UNIQUE constraint should suppress this particular duplicate.

## Result in the included run

All five trials per case matched: control 1 order; abort only 1 order; unkeyed retry 2 orders; same-key retry 1 order. All aborted cases produced client AbortError before a database commit. Exact representative timings are in the raw trace (and in the summary visual being added).

## Limits

This is not a performance benchmark, a sample of different frameworks or evidence that cancellation is impossible. The handler is intentionally written to keep going. Cancellation-aware code can behave differently, and cancellation after a commit cannot retroactively undo it without a separate operation. The test has no proxy, TLS, remote database, third-party side effect, authentication or payments. It uses one synthetic effect in SQLite. A UNIQUE key here is not a full production idempotency protocol or an exactly-once guarantee. Wall-clock milliseconds from the same machine provide event timing; exact values vary by scheduling.

The original speaker explains a broader HTTP cancellation problem. This toy experiment tests one mechanism, not his entire video. It is an old fundamental concept, not a newly released video or a contradiction of the speaker. Auto-caption opening and video metadata were checked; no claim that the user watched the full video is made.

No Impact Gate, private product code, employer information or production system was used. Nothing was posted to X. Post text is a draft for user review.
