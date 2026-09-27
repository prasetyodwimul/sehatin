import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/components/auth-provider";
import { Navbar, Footer } from "@/components/layout";

export const metadata: Metadata = {
  title: "SEHATIN — Trusted Health Ecosystem",
  description: "Informasi kesehatan dengan evidence, verifikasi, provenance, dan ketidakpastian yang transparan.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id">
      <body className="flex min-h-screen flex-col font-sans">
        <AuthProvider>
          <a href="#main-content" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-sm focus:bg-surface focus:px-4 focus:py-3 focus:text-sm focus:font-semibold focus:text-primary-dark focus:shadow-subtle">Lewati ke konten utama</a>
          <Navbar />
          <main id="main-content" className="flex-1" tabIndex={-1}>{children}</main>
          <Footer />
        </AuthProvider>
      </body>
    </html>
  );
}
