import assert from "node:assert/strict";
import { writeFileSync } from "node:fs";
import { startProvider } from "./provider.mjs";
import { processOrder } from "./consumer.mjs";

const out = { node: process.version, trials: [] };
const server = await startProvider();
const base = `http://127.0.0.1:${server.address().port}`;

for (let i = 1; i <= 5; i++) {
  // 1. The consumer's unit test: fetch is mocked with the OLD response shape.
  const mockFetch = async () => ({ json: async () => ({ id: "prod_101", priceCents: 5000 }) });
  let testPassed = true;
  try { assert.equal((await processOrder(base, "prod_101", 2, mockFetch)).subtotalCents, 10000); }
  catch { testPassed = false; }

  // 2. The same consumer code against the real provider.
  const raw = await fetch(`${base}/v1/products/prod_101`);
  const body = await raw.json();
  const real = await processOrder(base, "prod_101", 2);

  // 3. Control: read the new field name.
  const fixed = body.unitPriceCents * 2;

  const t = {
    trial: i,
    mocked_test_passed: testPassed,
    provider_status: raw.status,
    provider_fields: Object.keys(body),
    real_subtotal: String(real.subtotalCents),
    real_subtotal_is_nan: Number.isNaN(real.subtotalCents),
    real_subtotal_as_json: JSON.stringify(real),
    control_subtotal_with_unitPriceCents: fixed,
  };
  out.trials.push(t);
  console.log(`trial ${i}: mocked test ${testPassed ? "PASS" : "FAIL"} | real API ${t.provider_status} | subtotal ${t.real_subtotal} | json ${t.real_subtotal_as_json} | control ${fixed}`);
}
server.close();
const all = out.trials.every(t => t.mocked_test_passed && t.provider_status === 200 && t.real_subtotal_is_nan && t.control_subtotal_with_unitPriceCents === 199800);
console.log(all ? "RESULT: 5/5 trials, mocked test green, real call 200, subtotal NaN" : "RESULT: unexpected");
writeFileSync(new URL("./results.json", import.meta.url), JSON.stringify(out, null, 2));
process.exit(all ? 0 : 1);
