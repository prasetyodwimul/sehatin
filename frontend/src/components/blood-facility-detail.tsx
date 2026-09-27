"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { Clock3, Database, MapPin, ShieldCheck } from "lucide-react";
import { Alert, Badge, Card, Skeleton } from "@/components/ui";
import { getButtonClasses } from "@/components/button-styles";
import { ApiError, apiFetch } from "@/lib/api";
import { STATUS_VARIANT, facilityDataMode, type BloodFacility, type BloodStatus } from "@/lib/blood";

const STATUS_LABEL: Record<BloodStatus, string> = {
  AVAILABLE: "Tersedia",
  LIMITED: "Terbatas",
  EMPTY: "Habis",
  UNKNOWN: "Belum ada info",
};

export function BloodFacilityDetail({ facilityId }: { facilityId: string }) {
  const [facility, setFacility] = useState<BloodFacility | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState("");
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const requestSequence = useRef(0);

  const load = useCallback(async (silent = false) => {
    const requestId = ++requestSequence.current;
    if (silent) setRefreshing(true); else setLoading(true);
    setError(""); setNotFound(false);
    try {
      const row = await apiFetch<BloodFacility>(`/api/blood/facilities/${encodeURIComponent(facilityId)}`, { timeoutMs: 10_000 });
      if (requestId !== requestSequence.current) return;
      setFacility(row);
      setLastRefresh(new Date());
    } catch (err) {
      if (requestId !== requestSequence.current) return;
      if (err instanceof ApiError && err.status === 404) {
        setFacility(null); setNotFound(true);
      } else {
        setError(err instanceof Error ? err.message : "Data fasilitas belum dapat dimuat.");
      }
    } finally {
      if (requestId !== requestSequence.current) return;
      if (silent) setRefreshing(false); else setLoading(false);
    }
  }, [facilityId]);

  useEffect(() => { void load(); }, [load]);
  const refreshSeconds = Math.max(15, facility?.refresh_hint_seconds ?? 60);
  useEffect(() => {
    const timer = window.setInterval(() => { void load(true); }, refreshSeconds * 1000);
    return () => window.clearInterval(timer);
  }, [load, refreshSeconds]);

  if (loading) {
    return <div className="space-y-5" aria-busy="true"><Card large><Skeleton className="h-7 w-2/3"/><Skeleton className="mt-4 h-4 w-1/2"/></Card><Card large><Skeleton className="h-32 w-full"/></Card></div>;
  }

  if (!facility) {
    return <div><Alert variant="error" title={notFound ? "Fasilitas tidak ditemukan" : "Data belum dapat dimuat"}>{notFound ? "ID fasilitas tidak tersedia pada provider darah saat ini." : error || "Backend belum dapat dihubungi."}</Alert><Link href="/blood" className={getButtonClasses({ variant: "secondary", className: "mt-5" })}>Kembali ke Blood Connect</Link></div>;
  }

  return (
    <div aria-live="polite" aria-busy={refreshing || undefined}>
      <Alert variant="info" title="Catatan penggunaan">
        Informasi ini membantu pencarian awal. Sebelum donor atau transfusi dilakukan, pastikan kembali ketersediaan darah langsung ke fasilitas terkait.
      </Alert>

      <div className="mt-5 flex flex-wrap gap-2">
        <Badge variant={facilityDataMode(facility) === "SIMULATED" ? "warning" : "success"}>{facilityDataMode(facility) === "SIMULATED" ? "DEMO · bukan stok live resmi" : "LIVE/provider"}</Badge>
        <Badge variant="info"><Clock3 size={12} /> Diperbarui {new Date(facility.last_updated).toLocaleString("id-ID")}</Badge>
        <Badge variant={facility.verified ? "success" : "warning"}><ShieldCheck size={12} /> {facility.verified ? "Sumber terverifikasi" : "Perlu konfirmasi"}</Badge>
      </div>
      <p className="mt-2 text-xs text-muted">Refresh sesuai provider setiap {refreshSeconds} detik{refreshing ? " · memperbarui..." : ""}{lastRefresh ? ` · Dicek terakhir ${lastRefresh.toLocaleTimeString("id-ID")}` : ""}</p>

      <section className="mt-8" aria-labelledby="availability-heading">
        <h2 id="availability-heading" className="text-xl font-semibold">Ketersediaan darah</h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {facility.inventory.map((item) => (
            <Card key={`${item.blood_type}${item.rhesus}`} className="rounded-2xl border-line bg-white">
              <div className="flex items-center justify-between gap-3"><span className="text-2xl font-semibold">{item.blood_type}{item.rhesus}</span><Badge variant={STATUS_VARIANT[item.status]}>{STATUS_LABEL[item.status]}</Badge></div>
              <p className="mt-3 text-sm text-secondary">{item.quantity ?? item.units ?? "Belum tersedia"} unit</p>
            </Card>
          ))}
        </div>
      </section>

      <div className="mt-8 grid gap-5 lg:grid-cols-2">
        <Card className="rounded-2xl border-line bg-white"><h2 className="font-semibold">Informasi fasilitas</h2><dl className="mt-4 space-y-3 text-sm"><div><dt className="text-muted">Nama fasilitas</dt><dd className="mt-1 font-medium text-text">{facility.name}</dd></div><div><dt className="text-muted">Lokasi</dt><dd className="mt-1 text-secondary inline-flex items-center gap-1.5"><MapPin size={14} /> {facility.address}, {facility.city}</dd></div><div><dt className="text-muted">Status sumber</dt><dd className="mt-1 text-secondary">{facility.verified ? "Informasi sumber telah dicatat" : "Sebaiknya dikonfirmasi kembali ke fasilitas"}</dd></div></dl></Card>
        <Card className="rounded-2xl border-line bg-white"><h2 className="font-semibold">Sumber data</h2><dl className="mt-4 space-y-3 text-sm"><div><dt className="text-muted">Asal data</dt><dd className="mt-1 text-secondary inline-flex items-center gap-1.5"><Database size={14} /> {facility.data_source}</dd></div><div><dt className="text-muted">Waktu pembaruan</dt><dd className="mt-1 text-secondary">{new Date(facility.last_updated).toLocaleString("id-ID")}</dd></div><div><dt className="text-muted">Catatan</dt><dd className="mt-1 text-secondary">Gunakan informasi ini sebagai rujukan awal, lalu hubungi fasilitas untuk memastikan ketersediaan terbaru.</dd></div></dl></Card>
      </div>
      <Link href="/blood" className={getButtonClasses({ variant: "secondary", className: "mt-8" })}>Kembali ke Blood Connect</Link>
    </div>
  );
}
