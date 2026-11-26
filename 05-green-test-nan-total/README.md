# 05 - My test passed. The total was NaN.

**Setup.** A catalog API renamed `priceCents` to `unitPriceCents`. An order consumer still reads `priceCents`. The consumer's unit test mocks `fetch` with the old response shape.

**Expectation (written before the run).** The unit test stays green. Against the real API the consumer gets `undefined * 2`, so the subtotal is `NaN` while the API itself still answers 200.

**Result.** 5 of 5 trials, local run, Node 22:

- Mocked consumer test: pass.
- Real provider: `200`, fields `id, name, unitPriceCents`.
- Same consumer code against it: `subtotalCents` is `NaN` (serialises to `null` in JSON).
- Control, reading `unitPriceCents`: `199800`.

Raw output: `run-console.txt`, `results.json`.

**Run it.** `node run.mjs` (Node 18+, no installs, localhost only).

**Where this comes from.** The shapes are copied from my own lab services: the catalog API (`impact-gate/ig-lab-catalog-api`, commit `2167e95`) and the order consumer (`impact-gate/ig-lab-consumer-ts-1`). I also ran the real lab code on 26 Nov: the same 200 and the same `NaN`. `run.mjs` is a reduced plain-JS copy so you can run it without installing Fastify or Vitest.

**Limits.**

- A lab setup, not a customer incident.
- The provider's own test for `priceCents` fails in the lab repo, so the provider side did go red here. The consumer test is the one that stayed green.
- One field rename in a toy system. It says nothing about how often this happens.
- Does not claim any tool would have caught it.
