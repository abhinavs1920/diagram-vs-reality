// Same logic as OrderProcessor in impact-gate/ig-lab-consumer-ts-1 (src/order-service.ts),
// reduced to plain JS so this runs with only Node. It still reads `priceCents`.
export async function processOrder(baseUrl, productId, quantity, fetchFn = fetch) {
  const res = await fetchFn(`${baseUrl}/v1/products/${productId}`);
  const product = await res.json();
  return { subtotalCents: product.priceCents * quantity };
}
