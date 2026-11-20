/**
 * Typed API client. Paths and payloads come from FastAPI's OpenAPI schema
 * (`make gen-api` regenerates schema.d.ts). All calls go to same-origin /api/*.
 */
import createClient, { type Middleware } from "openapi-fetch";

import type { components, paths } from "./schema";

export type Schemas = components["schemas"];

export const api = createClient<paths>({ baseUrl: "" });

/** Expired or missing session on a data call: send the user to sign in, then back here. */
const redirectOn401: Middleware = {
  async onResponse({ request, response }) {
    if (response.status === 401 && typeof window !== "undefined") {
      const path = new URL(request.url, window.location.origin).pathname;
      if (!path.startsWith("/api/auth/")) {
        const next = window.location.pathname + window.location.search;
        // Full page load on purpose: drops every cached query from the old session.
        // eslint-disable-next-line @next/next/no-location-assign-relative-destination
        window.location.assign(`/login?expired=1&next=${encodeURIComponent(next)}`);
      }
    }
    return response;
  },
};
api.use(redirectOn401);

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

function messageFrom(error: unknown, status: number): string {
  if (error && typeof error === "object" && "detail" in error) {
    const detail = (error as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: string; loc?: (string | number)[] };
      const field = first.loc?.slice(-1)[0];
      return field ? `${String(field).replace(/_/g, " ")}: ${first.msg}` : (first.msg ?? "Invalid input");
    }
  }
  if (status >= 500) return "Something went wrong on the server. Try again in a moment.";
  return `Request failed (${status}).`;
}

/** Resolve an openapi-fetch call to its data, or throw ApiError with a readable message. */
export async function unwrap<T>(
  call: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  const { data, error, response } = await call;
  if (!response.ok || error !== undefined) {
    throw new ApiError(response.status, messageFrom(error, response.status));
  }
  return data as T;
}
