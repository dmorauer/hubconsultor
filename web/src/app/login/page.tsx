"use client";

import { signIn } from "next-auth/react";
import { useState } from "react";

export default function LoginPage() {
  const [loading, setLoading] = useState(false);

  async function login() {
    setLoading(true);
    await signIn("google", { callbackUrl: "/" });
  }

  return <main className="login-page"><section className="login-card"><span className="brand">PAYTRACK</span><h1>Validador de cargas</h1><p>Acesso restrito a contas corporativas <strong>@paytrack.com.br</strong>.</p><button className="google-button" onClick={login} disabled={loading}>{loading ? "Redirecionando…" : "Entrar com Google"}</button></section></main>;
}
