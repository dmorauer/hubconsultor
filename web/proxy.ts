import { auth, paytrackEmail } from "@/auth";
import { NextResponse } from "next/server";

export default auth((request) => {
  const path = request.nextUrl.pathname;
  const allowed = paytrackEmail(request.auth?.user?.email);
  if (path === "/login") return allowed ? NextResponse.redirect(new URL("/", request.url)) : NextResponse.next();
  if (allowed) return NextResponse.next();
  const url = new URL("/login", request.url);
  url.searchParams.set("callbackUrl", request.nextUrl.pathname);
  return NextResponse.redirect(url);
});

export const config = { matcher: ["/((?!api/auth|_next/static|_next/image|icon.png|favicon.ico).*)"] };
