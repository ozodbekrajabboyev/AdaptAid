/**
 * Optimistic route gating (Next.js 16 "proxy", formerly middleware).
 * It only reads the session cookie's role claim to redirect early. Real authorization
 * happens in FastAPI on every API call; an expired session there returns 401 and the
 * client redirects to /login.
 */
import { NextResponse, type NextRequest } from "next/server";

const COOKIE = "adaptaid_session";
const STUDENT_PREFIXES = ["/home", "/path", "/learn", "/library", "/progress", "/profile", "/onboarding", "/study"];

type Role = "student" | "teacher" | "admin";

function roleFromToken(token: string): Role | null {
  try {
    const payload = token.split(".")[1];
    const json = JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
    if (typeof json.exp === "number" && json.exp * 1000 < Date.now()) return null;
    return json.role === "student" || json.role === "teacher" || json.role === "admin" ? json.role : null;
  } catch {
    return null;
  }
}

function home(role: Role): string {
  return role === "teacher" ? "/teacher" : role === "admin" ? "/admin" : "/home";
}

function matches(pathname: string, prefix: string): boolean {
  return pathname === prefix || pathname.startsWith(`${prefix}/`);
}

export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const token = request.cookies.get(COOKIE)?.value;
  const role = token ? roleFromToken(token) : null;

  if (pathname === "/login" || pathname === "/register") {
    return role ? NextResponse.redirect(new URL(home(role), request.url)) : NextResponse.next();
  }

  let allowed: Role[] | null = null;
  if (matches(pathname, "/teacher")) allowed = ["teacher", "admin"];
  else if (matches(pathname, "/admin")) allowed = ["admin"];
  else if (STUDENT_PREFIXES.some((p) => matches(pathname, p))) allowed = ["student"];
  if (!allowed) return NextResponse.next();

  if (!role) {
    const login = new URL("/login", request.url);
    login.searchParams.set("next", pathname + search);
    return NextResponse.redirect(login);
  }
  if (!allowed.includes(role)) return NextResponse.redirect(new URL(home(role), request.url));
  return NextResponse.next();
}

export const config = {
  // Skip API calls, Next internals and files with an extension (images, fonts, ...).
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|.*\\..*).*)"],
};
