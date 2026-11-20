/**
 * Contract test for src/app/api/[...path]/route.ts: everything the browser sends to /api/*
 * must reach FastAPI intact, and everything FastAPI returns must reach the browser intact.
 */
import { expect, test } from "@playwright/test";

test("forwards several Set-Cookie headers and sends the cookies back", async ({ request }) => {
  const res = await request.get("/api/_contract/cookies");
  expect(res.status()).toBe(200);
  const setCookies = res
    .headersArray()
    .filter((h) => h.name.toLowerCase() === "set-cookie")
    .map((h) => h.value);
  expect(setCookies.some((c) => c.startsWith("contract_a=1"))).toBe(true);
  expect(setCookies.some((c) => c.startsWith("contract_b=2"))).toBe(true);

  const echo = await (await request.get("/api/_contract/echo")).json();
  expect(echo.cookies).toMatchObject({ contract_a: "1", contract_b: "2" });
});

test("keeps the query string and the JSON body", async ({ request }) => {
  const get = await (await request.get("/api/_contract/echo?x=1&y=two%20words")).json();
  expect(get.query).toEqual({ x: "1", y: "two words" });

  const post = await request.post("/api/_contract/echo?z=3", { data: { hello: "world", n: [1, 2] } });
  expect(post.status()).toBe(200);
  expect(await post.json()).toMatchObject({ method: "POST", body: { hello: "world", n: [1, 2] }, query: { z: "3" } });
});

test("decodes gzip-compressed backend responses", async ({ request }) => {
  const res = await request.get("/api/_contract/big", { headers: { "accept-encoding": "gzip" } });
  expect(res.status()).toBe(200);
  const body = await res.json();
  expect(body.items).toHaveLength(300);
});

test("passes 204 through with an empty body", async ({ request }) => {
  const res = await request.delete("/api/_contract/nothing");
  expect(res.status()).toBe(204);
  expect((await res.body()).length).toBe(0);
});

test("passes error statuses and bodies through", async ({ request }) => {
  const res = await request.get("/api/_contract/error");
  expect(res.status()).toBe(418);
  expect(await res.json()).toEqual({ detail: "Teapot says no" });
});

test("forwards multipart uploads with their boundary", async ({ request }) => {
  const res = await request.post("/api/_contract/upload", {
    multipart: {
      note: "hello",
      file: { name: "notes.txt", mimeType: "text/plain", buffer: Buffer.from("hello world") },
    },
  });
  expect(res.status()).toBe(200);
  expect(await res.json()).toEqual({ filename: "notes.txt", size: 11, note: "hello" });
});

test("keeps Content-Disposition on file downloads", async ({ request }) => {
  const res = await request.get("/api/_contract/csv");
  expect(res.status()).toBe(200);
  expect(res.headers()["content-disposition"]).toContain('filename="contract.csv"');
  expect(await res.text()).toBe("a,b\n1,2\n");
});

test("does not follow redirects or leak the backend origin", async ({ request }) => {
  const res = await request.get("/api/_contract/redirect", { maxRedirects: 0 });
  expect(res.status()).toBe(307);
  const location = res.headers()["location"];
  expect(location.startsWith("/api/_contract/echo")).toBe(true);
  expect(location).not.toContain("8100");
});
