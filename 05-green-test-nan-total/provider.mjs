// Catalog API after the rename (priceCents -> unitPriceCents), as in
// impact-gate/ig-lab-catalog-api commit 2167e95. Plain node:http, same response shape.
import { createServer } from "node:http";
const product = { id: "prod_101", name: "Standard Laptop", unitPriceCents: 99900 };
export function startProvider() {
  return new Promise((resolve) => {
    const server = createServer((req, res) => {
      if (req.url === "/v1/products/prod_101") {
        res.writeHead(200, { "content-type": "application/json" });
        res.end(JSON.stringify(product));
      } else { res.writeHead(404); res.end("{}"); }
    });
    server.listen(0, "127.0.0.1", () => resolve(server));
  });
}
