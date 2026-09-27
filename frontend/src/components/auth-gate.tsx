"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { X } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { Alert, Button, Input } from "@/components/ui";
import { loginAccount, registerAccount, type AuthUser } from "@/lib/auth";

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

export function AuthGate({
  open,
  onClose,
  onAuthenticated,
  requireSaveConsent = false,
  contextLabel,
}: {
  open: boolean;
  onClose: () => void;
  onAuthenticated: (user: AuthUser) => void | Promise<void>;
  requireSaveConsent?: boolean;
  contextLabel?: string;
}) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [consent, setConsent] = useState(!requireSaveConsent);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState({ email: "", password: "" });
  const { refreshAuth } = useAuth();
  const dialogRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;
    setError("");
    setFieldErrors({ email: "", password: "" });
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") { onClose(); return; }
      if (event.key !== "Tab" || !dialogRef.current) return;
      const focusable = Array.from(dialogRef.current.querySelectorAll<HTMLElement>('button:not([disabled]), a[href], input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'));
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", onKeyDown);
    const timer = window.setTimeout(() => document.getElementById("auth-email")?.focus(), 0);
    return () => {
      window.clearTimeout(timer);
      document.removeEventListener("keydown", onKeyDown);
      previousFocus?.focus();
    };
  }, [onClose, open]);

  if (!open) return null;

  function switchMode(nextMode: "login" | "register") {
    setMode(nextMode);
    setError("");
    setFieldErrors({ email: "", password: "" });
  }

  async function submit(event: FormEvent) {
    event.preventDefault();

    const nextErrors = {
      email: validateEmail(email),
      password: validatePassword(password, mode),
    };
    setFieldErrors(nextErrors);
    setError("");

    if (nextErrors.email || nextErrors.password) return;
    if (requireSaveConsent && !consent) {
      setError("Konfirmasi penyimpanan data diperlukan untuk memulai Guided Program.");
      return;
    }

    setLoading(true);
    try {
      const response = mode === "login"
        ? await loginAccount(email.trim(), password)
        : await registerAccount(email.trim(), password);
      const current = await refreshAuth();
      if (!current) throw new Error("Session belum dapat dipulihkan. Silakan coba login kembali.");
      await onAuthenticated(current ?? response.user);
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Autentikasi belum dapat diproses.");
      setLoading(false);
    }
  }

  const title = contextLabel ?? "Lanjutkan perjalanan nutrisi kamu.";

  return (
    <div className="fixed inset-0 z-[80] flex items-end justify-center bg-text/45 p-0 backdrop-blur-sm sm:items-center sm:p-5" role="presentation">
      <section ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby="auth-gate-title" className="max-h-[92vh] w-full max-w-lg overflow-y-auto rounded-t-xl bg-surface p-6 shadow-2xl sm:rounded-xl sm:p-8">
        <div className="flex items-start justify-between gap-5">
          <div>
            <p className="eyebrow">Akun SEHATIN</p>
            <h2 id="auth-gate-title" className="mt-3 text-3xl font-semibold tracking-[-0.04em]">{title}</h2>
          </div>
          <button type="button" onClick={onClose} className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-line" aria-label="Tutup"><X size={18} /></button>
        </div>

        <p className="mt-4 text-sm leading-7 text-secondary">Assessment dan hasil publik tetap bisa digunakan tanpa akun. Akun hanya diperlukan ketika kamu memilih menyimpan data dan melanjutkan Guided Nutrition Program.</p>

        <div className="mt-7 flex border-b border-line" role="tablist" aria-label="Pilih metode autentikasi">
          <button type="button" role="tab" aria-selected={mode === "login"} onClick={() => switchMode("login")} className={`min-h-11 flex-1 border-b-2 px-3 text-sm font-semibold ${mode === "login" ? "border-primary text-primary-dark" : "border-transparent text-muted"}`}>Masuk</button>
          <button type="button" role="tab" aria-selected={mode === "register"} onClick={() => switchMode("register")} className={`min-h-11 flex-1 border-b-2 px-3 text-sm font-semibold ${mode === "register" ? "border-primary text-primary-dark" : "border-transparent text-muted"}`}>Buat akun</button>
        </div>

        <form className="mt-6 space-y-5" onSubmit={submit} noValidate>
          <Input id="auth-email" label="Email" type="email" autoComplete="email" value={email} onChange={(e) => { setEmail(e.target.value); setFieldErrors((current) => ({ ...current, email: "" })); }} required error={fieldErrors.email} />
          <Input id="auth-password" label="Password" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} value={password} onChange={(e) => { setPassword(e.target.value); setFieldErrors((current) => ({ ...current, password: "" })); }} required error={fieldErrors.password} helperText={mode === "register" ? "Minimal 10 karakter, dengan huruf besar, huruf kecil, dan angka." : undefined} />

          {requireSaveConsent && (
            <div>
              <label className={`flex gap-3 rounded-md border p-4 text-sm leading-6 transition-colors ${consent ? "border-primary/40 bg-primary-light/40 text-text" : "border-line bg-background text-secondary"}`}>
                <input type="checkbox" checked={consent} onChange={(e) => { setConsent(e.target.checked); setError(""); }} className="mt-1 h-4 w-4 shrink-0 accent-primary" />
                <span>Saya memahami assessment nutrisi dan aktivitas Guided Program akan disimpan agar program dapat dilanjutkan.</span>
              </label>
              {!consent && <p className="mt-2 text-xs font-medium text-muted">Centang konfirmasi untuk melanjutkan.</p>}
            </div>
          )}

          {error && <Alert variant="error" title="Belum dapat melanjutkan">{error}</Alert>}

          <Button type="submit" size="lg" className="w-full transition-opacity" disabled={loading || (requireSaveConsent && !consent)} isLoading={loading} loadingLabel={mode === "login" ? "Sedang masuk..." : "Membuat akun..."}>
            {mode === "login" ? "Masuk & Lanjutkan" : "Buat akun & Lanjutkan"}
          </Button>
          <Button type="button" variant="ghost" className="w-full" onClick={onClose}>Lanjut sebagai Guest</Button>
        </form>

        <p className="mt-5 text-xs leading-5 text-muted">Session menggunakan cookie HttpOnly dan data lokal hasil assessment tetap tersedia selama alur penyimpanan belum selesai.</p>
      </section>
    </div>
  );
}
