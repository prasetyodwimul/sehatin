"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Alert, Button, Input } from "@/components/ui";
import { useAuth } from "@/components/auth-provider";
import { loginAccount, registerAccount } from "@/lib/auth";

function safeReturnPath(value: string | null) {
  if (!value || !value.startsWith("/") || value.startsWith("//")) return "/nutrition/program";
  return value;
}

function validateEmail(value: string) {
  const email = value.trim();
  if (!email) return "Email wajib diisi.";
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return "Masukkan alamat email yang valid.";
  return "";
}

function validatePassword(value: string, mode: "login" | "register") {
  if (!value) return "Password wajib diisi.";
  if (mode === "register" && !/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{10,}$/.test(value)) {
    return "Password minimal 10 karakter dan harus memiliki huruf besar, huruf kecil, serta angka.";
  }
  return "";
}

export function AuthPage({ mode }: { mode: "login" | "register" }) {
  const router = useRouter();
  const { status, refreshAuth } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState({ email: "", password: "" });
  const [returnPath, setReturnPath] = useState("/nutrition/program");

  useEffect(() => {
    const query = new URLSearchParams(window.location.search);
    setReturnPath(safeReturnPath(query.get("next")));
  }, []);

  useEffect(() => {
    if (status === "authenticated") router.replace(returnPath);
  }, [returnPath, router, status]);

  const alternateAuthHref = useMemo(() => {
    const path = mode === "login" ? "/register" : "/login";
    return `${path}?next=${encodeURIComponent(returnPath)}`;
  }, [mode, returnPath]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const nextErrors = {
      email: validateEmail(email),
      password: validatePassword(password, mode),
    };
    setFieldErrors(nextErrors);
    setError("");
    if (nextErrors.email || nextErrors.password) return;

    setLoading(true);
    try {
      if (mode === "login") await loginAccount(email.trim(), password);
      else await registerAccount(email.trim(), password);
      const current = await refreshAuth();
      if (!current) throw new Error("Session belum dapat dipulihkan. Silakan coba lagi.");
      router.replace(returnPath);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Autentikasi belum dapat diproses.");
      setLoading(false);
    }
  }

  return (
    <section className="mx-auto max-w-xl border-y border-line py-10 md:py-14">
      <p className="eyebrow">Akun SEHATIN</p>
      <h1 className="mt-3 text-4xl font-semibold tracking-[-0.045em]">{mode === "login" ? "Masuk ke SEHATIN" : "Buat akun SEHATIN"}</h1>
      <p className="mt-4 text-sm leading-7 text-secondary">Akun diperlukan untuk fitur yang perlu disimpan, seperti Guided Nutrition Program dan Nutrition History. Fitur publik tetap dapat digunakan tanpa login.</p>
      {returnPath !== "/nutrition/program" && <p className="mt-4 rounded-xl bg-primary-light/50 px-4 py-3 text-sm font-medium text-primary-dark">Setelah berhasil masuk, kamu akan kembali ke halaman yang tadi dibuka.</p>}

      <form onSubmit={submit} className="mt-8 space-y-5" noValidate>
        <Input id={`${mode}-email`} label="Email" type="email" autoComplete="email" required value={email} onChange={(e) => { setEmail(e.target.value); setFieldErrors((current) => ({ ...current, email: "" })); }} error={fieldErrors.email} />
        <Input id={`${mode}-password`} label="Password" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} required value={password} onChange={(e) => { setPassword(e.target.value); setFieldErrors((current) => ({ ...current, password: "" })); }} error={fieldErrors.password} helperText={mode === "register" ? "Minimal 10 karakter, dengan huruf besar, huruf kecil, dan angka." : undefined} />
        {error && <Alert variant="error" title="Belum dapat melanjutkan">{error}</Alert>}
        <Button type="submit" size="lg" className="w-full" isLoading={loading} loadingLabel={mode === "login" ? "Sedang masuk..." : "Membuat akun..."}>{mode === "login" ? "Masuk" : "Buat akun"}</Button>
      </form>

      <p className="mt-6 text-sm text-secondary">{mode === "login" ? <>Belum punya akun? <Link href={alternateAuthHref} className="font-semibold text-primary-dark">Buat akun</Link></> : <>Sudah punya akun? <Link href={alternateAuthHref} className="font-semibold text-primary-dark">Masuk</Link></>}</p>
    </section>
  );
}
