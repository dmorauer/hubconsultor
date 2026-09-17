import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";

const paytrackEmail = (email?: string | null) => Boolean(email && email.trim().toLowerCase().endsWith("@paytrack.com.br"));

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
        const accessPassword = process.env.PAYTRACK_ACCESS_PASSWORD;

        if (!paytrackEmail(email) || !accessPassword || password !== accessPassword) return null;
        return { id: email, email, name: email.split("@")[0] };
      },
    }),
  ],
  pages: { signIn: "/login", error: "/login" },
});

export { paytrackEmail };
