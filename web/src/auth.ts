import NextAuth from "next-auth";
import Google from "next-auth/providers/google";

const paytrackEmail = (email?: string | null) => Boolean(email && email.trim().toLowerCase().endsWith("@paytrack.com.br"));

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [Google],
  pages: { signIn: "/login", error: "/login" },
  callbacks: {
    async signIn({ profile }) {
      const email = typeof profile?.email === "string" ? profile.email : null;
      return paytrackEmail(email);
    },
  },
});

export { paytrackEmail };
