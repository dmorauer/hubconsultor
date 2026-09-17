"use client";

import { signIn } from "next-auth/react";
import { type FormEvent, useState } from "react";

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (!email.trim().toLowerCase().endsWith("@paytrack.com.br")) {
      setError("Use seu e-mail corporativo @paytrack.com.br.");
      return;
    }
    setLoading(true);
    const result = await signIn("credentials", { email, password, redirect: false, callbackUrl: "/" });
    if (result?.error) {
      setError("E-mail ou senha inválidos.");
      setLoading(false);
      return;
    }
    window.location.assign(result?.url || "/");
  }

  return <main className="login-page"><section className="login-card"><span className="brand">PAYTRACK · HUB DO CONSULTOR</span><h1>Boas-vindas</h1><p>Acesse o portal para revisar e preparar cargas. O acesso é restrito a contas corporativas <strong>@paytrack.com.br</strong>.</p><form className="login-form" onSubmit={login}><label>E-mail corporativo<input type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="nome@paytrack.com.br" required /></label><label>Senha de acesso<input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>{error ? <p className="login-error" role="alert">{error}</p> : null}<button className="login-button" type="submit" disabled={loading}>{loading ? "Entrando…" : "Entrar no portal"}</button></form></section></main>;
}
