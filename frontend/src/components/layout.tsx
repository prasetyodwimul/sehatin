"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ChevronDown, LogOut, Menu, UserRound, X } from "lucide-react";
import { useAuth } from "@/components/auth-provider";

export function Container({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`mx-auto w-full max-w-content px-5 md:px-8 lg:px-14 xl:px-16 ${className}`}>{children}</div>;
}

const NAV_LINKS = [
  { href: "/nutrition", label: "Nutrition" },
  { href: "/blood", label: "Blood Connect" },
  { href: "/health-checker", label: "Health Checker" },
  { href: "/about", label: "About" },
];


function ProfileMenu() {
  const { status, user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const [logoutError, setLogoutError] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  if (status === "loading") return null;
  const authenticated = Boolean(user);
  const profileName = user?.display_name?.trim() || user?.full_name?.trim() || user?.email.split("@")[0] || "";
  const initial = profileName.slice(0, 1).toUpperCase();
  const triggerLabel = user ? `Profile ${user.email}` : "Akun";

  return (
    <div className="relative ml-2" ref={rootRef}>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="inline-flex min-h-10 items-center gap-2 rounded-full border border-white/10 bg-white/[0.08] px-2 py-1 text-sm font-semibold text-white transition-colors hover:bg-white/[0.14] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-light/80"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={triggerLabel}
      >
        {authenticated ? (
          user?.avatar_data_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={user.avatar_data_url} alt="" className="h-8 w-8 rounded-full object-cover ring-1 ring-white/50" aria-hidden="true" />
          ) : <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-xs font-black text-white ring-1 ring-white/30" aria-hidden="true">{initial}</span>
        ) : <UserRound size={17} aria-hidden="true" />}
        {!authenticated && <span>Akun</span>}
        <ChevronDown size={15} aria-hidden="true" />
      </button>
      {open && (
        <div role="menu" className="absolute right-0 top-[calc(100%+.6rem)] w-64 overflow-hidden rounded-lg border border-line bg-surface p-2 shadow-xl">
          {user ? (
            <>
              <div className="px-3 pb-2 pt-1">
                <p className="truncate text-sm font-semibold text-text">{profileName}</p>
                <p className="mt-0.5 truncate text-xs text-muted">{user.email}</p>
              </div>
              <Link role="menuitem" href="/profile" onClick={() => setOpen(false)} className="flex min-h-11 items-center gap-2 rounded-md px-3 text-sm font-semibold hover:bg-background"><UserRound size={16} /> Profile</Link>
              <Link role="menuitem" href="/nutrition/history" onClick={() => setOpen(false)} className="flex min-h-11 items-center rounded-md px-3 text-sm font-semibold hover:bg-background">Nutrition History</Link>
              <button
                role="menuitem"
                type="button"
                onClick={async () => {
                  setLogoutError("");
                  try {
                    await logout();
                    setOpen(false);
                  } catch (error) {
                    setLogoutError(error instanceof Error ? error.message : "Logout belum dapat diproses.");
                  }
                }}
                className="flex min-h-11 w-full items-center gap-2 rounded-md px-3 text-left text-sm font-semibold hover:bg-background"
              >
                <LogOut size={16} /> Logout
              </button>
            </>
          ) : (
            <>
              <div className="px-3 pb-2 pt-1">
                <p className="text-sm font-semibold text-text">Akun SEHATIN</p>
                <p className="mt-1 text-xs leading-5 text-muted">Fitur publik tetap dapat digunakan tanpa login. Masuk hanya diperlukan untuk program dan riwayat tersimpan.</p>
              </div>
              <Link role="menuitem" href="/login" onClick={() => setOpen(false)} className="flex min-h-11 items-center rounded-md px-3 text-sm font-semibold hover:bg-background">Sign In</Link>
              <Link role="menuitem" href="/register" onClick={() => setOpen(false)} className="flex min-h-11 items-center rounded-md px-3 text-sm font-semibold hover:bg-background">Create Account</Link>
            </>
          )}
          {logoutError && <p role="alert" className="px-3 py-2 text-xs text-error">{logoutError}</p>}
        </div>
      )}
    </div>
  );
}

export function Navbar() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const pathname = usePathname();
  const { status, user, logout } = useAuth();

  useEffect(() => setDrawerOpen(false), [pathname]);
  useEffect(() => {
    if (!drawerOpen) return;
    const onKeyDown = (event: KeyboardEvent) => event.key === "Escape" && setDrawerOpen(false);
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [drawerOpen]);

  const active = (href: string) => pathname.startsWith(href);
  const isAbout = pathname === "/about";

  return (
    <>
      <header className="fixed inset-x-0 top-3 z-[100] px-4 sm:top-4 sm:px-6" data-testid="site-navbar">
        <div className={`mx-auto ${isAbout ? "max-w-[880px]" : "max-w-[1240px]"}`}>
          <div className="relative rounded-full bg-[#064f4a] px-3 shadow-[0_12px_35px_rgba(6,79,74,.14)] ring-1 ring-black/5 sm:px-4">
            <div className="flex h-14 items-center justify-between gap-3 sm:h-[68px]">
              <Link href="/" className="inline-flex shrink-0 items-center rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-light/80" aria-label="SEHATIN home">
                <img
                  src="/images/sehatin-navbar-full-logo.png"
                  alt="SEHATIN — Healthy Life Recovery"
                  className="block h-auto w-[120px] max-h-[44px] object-contain sm:w-[132px] sm:max-h-[46px]"
                />
              </Link>

              <nav className={`hidden flex-1 items-center justify-center lg:flex ${isAbout ? "gap-5" : "gap-7"}`} aria-label="Navigasi utama">
                {NAV_LINKS.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    aria-current={active(link.href) ? "page" : undefined}
                    className={`group relative inline-flex min-h-10 items-center px-1 text-[13px] font-semibold tracking-[-0.01em] transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-light/80 ${active(link.href) ? "text-white" : "text-white/75 hover:text-white"}`}
                  >
                    {link.label}
                    <span
                      className={`absolute bottom-0.5 left-1/2 h-[2px] -translate-x-1/2 rounded-full bg-[#7de4d6] transition-all duration-200 ${active(link.href) ? "w-[68%] opacity-100" : "w-0 opacity-0 group-hover:w-[68%]"}`}
                      aria-hidden="true"
                    />
                  </Link>
                ))}
              </nav>

              <div className="hidden items-center gap-2 lg:flex">
                {status !== "loading" ? <ProfileMenu /> : null}
              </div>

              <div className="flex items-center gap-2 lg:hidden">
                {status !== "loading" ? <ProfileMenu /> : null}
                <button
                  type="button"
                  className="flex h-10 w-10 items-center justify-center rounded-full text-white transition-colors hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-light/80"
                  aria-expanded={drawerOpen}
                  aria-controls="mobile-nav-drawer"
                  aria-label={drawerOpen ? "Tutup menu" : "Buka menu"}
                  onClick={() => setDrawerOpen((value) => !value)}
                >
                  {drawerOpen ? <X size={20} aria-hidden="true" /> : <Menu size={21} aria-hidden="true" />}
                </button>
              </div>
            </div>

            {drawerOpen && (
              <nav id="mobile-nav-drawer" aria-label="Navigasi seluler" className="border-t border-white/10 pb-3 pt-2 lg:hidden">
                <div className="flex flex-col px-2">
                  {NAV_LINKS.map((link) => (
                    <Link
                      key={link.href}
                      href={link.href}
                      aria-current={active(link.href) ? "page" : undefined}
                      className={`flex min-h-12 items-center justify-between rounded-xl px-3 text-base font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-light/80 ${active(link.href) ? "bg-white/[0.09] text-white" : "text-white/75 hover:bg-white/[0.06] hover:text-white"}`}
                    >
                      <span>{link.label}</span>
                      {active(link.href) && <span className="h-1.5 w-1.5 rounded-full bg-[#7de4d6]" aria-hidden="true" />}
                    </Link>
                  ))}
                  {status === "authenticated" && user ? (
                    <>
                      <div className="my-2 border-t border-white/10" />
                      <Link href="/nutrition/program" className="flex min-h-12 items-center rounded-xl px-3 text-base font-semibold text-white/75 hover:bg-white/[0.06] hover:text-white">My Nutrition Program</Link>
                      <Link href="/nutrition/history" className="flex min-h-12 items-center rounded-xl px-3 text-base font-semibold text-white/75 hover:bg-white/[0.06] hover:text-white">Nutrition History</Link>
                      <Link href="/profile" className="flex min-h-12 items-center rounded-xl px-3 text-base font-semibold text-white/75 hover:bg-white/[0.06] hover:text-white">Profile</Link>
                      <button
                        type="button"
                        onClick={() => {
                          void logout().then(() => setDrawerOpen(false)).catch(() => undefined);
                        }}
                        className="flex min-h-12 items-center rounded-xl px-3 text-left text-base font-semibold text-white/75 hover:bg-white/[0.06] hover:text-white"
                      >
                        Logout
                      </button>
                    </>
                  ) : status === "unauthenticated" ? (
                    <>
                      <div className="my-2 border-t border-white/10" />
                      <Link href="/login" className="flex min-h-12 items-center rounded-xl px-3 text-base font-semibold text-white/75 hover:bg-white/[0.06] hover:text-white">Sign In</Link>
                      <Link href="/register" className="flex min-h-12 items-center rounded-xl px-3 text-base font-semibold text-white/75 hover:bg-white/[0.06] hover:text-white">Create Account</Link>
                    </>
                  ) : null}
                </div>
              </nav>
            )}
          </div>
        </div>
      </header>
      <div className="h-[5.25rem] sm:h-[5.5rem]" aria-hidden="true" />
    </>
  );
}

export function Footer() {
  const pathname = usePathname();
  if (pathname === "/about") return null;

  return (
    <footer className="mt-24 bg-text text-white">
      <Container className="py-14 md:py-16">
        <div className="grid gap-10 lg:grid-cols-[1.3fr_.7fr] lg:items-end">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-primary-light">Trusted Health Ecosystem</p>
            <p className="mt-5 max-w-3xl text-3xl font-semibold leading-tight tracking-[-0.035em] md:text-5xl">Jawaban kesehatan lebih berguna ketika dasar buktinya ikut terlihat.</p>
          </div>
          <nav aria-label="Navigasi footer" className="flex flex-wrap gap-1 rounded-xl border border-white/15 bg-white/[.04] p-1 text-sm text-white/70 lg:ml-auto lg:w-fit">
            <Link href="/nutrition" className="rounded-lg px-3 py-2 transition-colors hover:bg-white/10 hover:text-white">Nutrition</Link>
            <Link href="/blood" className="rounded-lg px-3 py-2 transition-colors hover:bg-white/10 hover:text-white">Blood Connect</Link>
            <Link href="/health-checker" className="rounded-lg px-3 py-2 transition-colors hover:bg-white/10 hover:text-white">Health Checker</Link>
            <Link href="/about" className="rounded-lg px-3 py-2 transition-colors hover:bg-white/10 hover:text-white">About</Link>
          </nav>
        </div>
        <div className="mt-12 grid gap-4 border-t border-white/15 pt-6 text-xs leading-5 text-white/55 md:grid-cols-2 md:items-end">
          <p>Informasi di SEHATIN bersifat edukatif dan tidak menggantikan diagnosis atau konsultasi tenaga kesehatan.</p>
          <p className="md:text-right">Fitur publik tanpa login. Akun hanya digunakan bila kamu memilih menyimpan Guided Nutrition Program. © {new Date().getFullYear()} SEHATIN.</p>
        </div>
      </Container>
    </footer>
  );
}

export function PageHeader({ title, subtitle, stepIndicator }: { title: string; subtitle?: string; stepIndicator?: { current: number; total: number; label: string } }) {
  return (
    <div className="mb-10 max-w-4xl md:mb-14">
      {stepIndicator && (
        <div className="mb-5 max-w-xs">
          <p className="eyebrow">Langkah {stepIndicator.current} / {stepIndicator.total} · {stepIndicator.label}</p>
          <div className="mt-3 grid grid-cols-3 gap-1.5" aria-hidden="true">
            {Array.from({ length: stepIndicator.total }).map((_, index) => <span key={index} className={`h-1 rounded-full ${index < stepIndicator.current ? "bg-primary" : "bg-line"}`} />)}
          </div>
        </div>
      )}
      <h1 className="text-4xl font-semibold leading-[1.02] tracking-[-0.045em] text-text sm:text-5xl md:text-6xl">{title}</h1>
      {subtitle && <p className="mt-5 max-w-3xl text-base leading-7 text-secondary md:text-lg">{subtitle}</p>}
    </div>
  );
}
