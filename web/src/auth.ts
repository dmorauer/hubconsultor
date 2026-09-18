import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";

export type Role = "owner" | "member";

const paytrackEmail = (email?: string | null) => Boolean(email && email.trim().toLowerCase().endsWith("@paytrack.com.br"));
const OWNER_EMAIL = "douglas.morauer@paytrack.com.br";

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Credentials({
      name: "Acesso Paytrack",
      credentials: {
        email: { label: "E-mail corporativo", type: "email" },
        password: { label: "Senha de acesso", type: "password" },
      },
      async authorize(credentials) {
        const email = typeof credentials?.email === "string" ? credentials.email.trim().toLowerCase() : "";
        const password = typeof credentials?.password === "string" ? credentials.password : "";
        if (!paytrackEmail(email)) return null;

        const ownerPassword = process.env.PAYTRACK_OWNER_PASSWORD;
        if (email === OWNER_EMAIL && ownerPassword && password === ownerPassword) {
          return { id: email, email, name: email.split("@")[0], role: "owner" satisfies Role };
        }

        const accessPassword = process.env.PAYTRACK_ACCESS_PASSWORD;
        if (accessPassword && password === accessPassword) {
          return { id: email, email, name: email.split("@")[0], role: "member" satisfies Role };
        }

        return null;
      },
    }),
  ],
  pages: { signIn: "/login", error: "/login" },
  callbacks: {
    jwt({ token, user }) {
      if (user) token.role = (user as { role: Role }).role;
      return token;
    },
    session({ session, token }) {
      if (session.user) session.user.role = token.role as Role;
      return session;
    },
  },
});

export { paytrackEmail };
