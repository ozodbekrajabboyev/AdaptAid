/**
 * Same-origin forwarder: the browser calls /api/*, this handler relays the request to the
 * FastAPI backend at BACKEND_URL (read at request time, so one build works in every
 * environment). Keeping everything same-origin lets the session live in an httpOnly cookie
 * without CORS.
 *
 * Handles the cases a naive proxy gets wrong:
 *  - several Set-Cookie headers (copied one by one with getSetCookie + append)
 *  - compressed upstream bodies (fetch decompresses, so encoding/length headers are dropped)
 *  - 204/304 responses (no body allowed)
 *  - binary and multipart request bodies (forwarded as raw bytes with the original boundary)
 *  - redirects (never followed; Location is rewritten so the backend origin never leaks)
 */
import type { NextRequest } from "next/server";

const DROP_REQUEST_HEADERS = new Set([
  "host",
  "connection",
  "keep-alive",
  "content-length",
  "transfer-encoding",
  "upgrade",
  "te",
  "trailer",
  "proxy-authorization",
  "proxy-authenticate",
]);

const DROP_RESPONSE_HEADERS = new Set([
  "content-encoding",
  "content-length",
  "transfer-encoding",
  "connection",
  "keep-alive",
  "set-cookie",
]);

function backendOrigin(): string {
  return (process.env.BACKEND_URL ?? "http://localhost:8000").replace(/\/+$/, "");
}

async function forward(request: NextRequest): Promise<Response> {
  const origin = backendOrigin();
  const target = `${origin}${request.nextUrl.pathname}${request.nextUrl.search}`;

  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (!DROP_REQUEST_HEADERS.has(key.toLowerCase())) headers.set(key, value);
  });
  headers.set("x-forwarded-host", request.headers.get("host") ?? "");
  headers.set("x-forwarded-proto", request.nextUrl.protocol.replace(":", ""));

  const hasBody = !["GET", "HEAD"].includes(request.method);
  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: request.method,
      headers,
      body: hasBody ? await request.arrayBuffer() : undefined,
      redirect: "manual",
      cache: "no-store",
    });
  } catch {
    return Response.json(
      { detail: "The AdaptAid server is not reachable. Check that the backend is running." },
      { status: 502 },
    );
  }

  const outHeaders = new Headers();
  upstream.headers.forEach((value, key) => {
    if (DROP_RESPONSE_HEADERS.has(key.toLowerCase())) return;
    if (key.toLowerCase() === "location" && value.startsWith(origin)) {
      outHeaders.set(key, value.slice(origin.length) || "/");
      return;
    }
    outHeaders.set(key, value);
  });
  for (const cookie of upstream.headers.getSetCookie()) {
    outHeaders.append("set-cookie", cookie);
  }

  const noBody = upstream.status === 204 || upstream.status === 304 || request.method === "HEAD";
  return new Response(noBody ? null : upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: outHeaders,
  });
}

export const GET = forward;
export const POST = forward;
export const PUT = forward;
export const PATCH = forward;
export const DELETE = forward;
export const HEAD = forward;
export const OPTIONS = forward;
