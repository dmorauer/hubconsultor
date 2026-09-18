import type { Role } from "@/auth";

declare module "next-auth" {
  interface Session {
    user: {
      role?: Role;
    } & import("next-auth").DefaultSession["user"];
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    role?: Role;
  }
}
