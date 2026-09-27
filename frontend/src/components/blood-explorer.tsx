"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowUpRight, Clock3, Database, MapPin, Search, ShieldCheck } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { BLOOD_TYPES, RHESUS_VALUES, STATUS_VARIANT, facilityDataMode, type BloodFacility, type BloodStatus } from "@/lib/blood";
import { Alert, Badge, Button, Card, Input, Select, Skeleton } from "@/components/ui";

type Filters = { bloodType?: string; rhesus?: string; city?: string; facility?: string };

const STATUS_LABEL: Record<BloodStatus, string> = {
  AVAILABLE: "Tersedia",
  LIMITED: "Terbatas",
  EMPTY: "Habis",
  UNKNOWN: "Belum ada info",
};

export function BloodExplorer() {
  const [bloodType, setBloodType] = useState("");
  const [rhesus, setRhesus] = useState("");
  const [city, setCity] = useState("");
  const [facility, setFacility] = useState("");
  const [appliedFilters, setAppliedFilters] = useState<Filters>({});
  const [facilities, setFacilities] = useState<BloodFacility[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const requestSequence = useRef(0);

  const load = useCallback(async (filters: Filters = {}, silent = false) => {
    const requestId = ++requestSequence.current;
    if (silent) setRefreshing(true); else setLoading(true);
    setError("");
    const params = new URLSearchParams();
    if (filters.bloodType) params.set("blood_type", filters.bloodType);
    if (filters.rhesus) params.set("rhesus", filters.rhesus);
    if (filters.city?.trim()) params.set("city", filters.city.trim());
    if (filters.facility?.trim()) params.set("facility", filters.facility.trim());
    try {
      const query = params.toString();
      const rows = await apiFetch<BloodFacility[]>(`/api/blood/inventory${query ? `?${query}` : ""}`, { timeoutMs: 10_000 });
      if (requestId !== requestSequence.current) return;
      setFacilities(rows);
      setLastRefresh(new Date());
    } catch (err) {
      if (requestId !== requestSequence.current) return;
      if (!silent) setFacilities([]);
      setError(err instanceof Error ? err.message : "Data darah belum dapat dimuat.");
    } finally {
      if (requestId !== requestSequence.current) return;
      if (silent) setRefreshing(false); else setLoading(false);
    }
  }, []);

  useEffect(() => { void load(appliedFilters); }, [appliedFilters, load]);
  const refreshSeconds = useMemo(() => Math.max(15, facilities[0]?.refresh_hint_seconds ?? 60), [facilities]);
  const hasSimulatedData = useMemo(() => facilities.some((item) => facilityDataMode(item) === "SIMULATED"), [facilities]);

  useEffect(() => {
    const timer = window.setInterval(() => { void load(appliedFilters, true); }, refreshSeconds * 1000);
    return () => window.clearInterval(timer);
  }, [appliedFilters, load, refreshSeconds]);

  function submit(event: FormEvent) {
    event.preventDefault();
    setAppliedFilters({ bloodType, rhesus, city, facility });
  }

  function reset() {
    setBloodType("");
    setRhesus("");
    setCity("");
    setFacility("");
    setAppliedFilters({});
  }

  const totalInventoryRows = useMemo(
    () => facilities.reduce((count, item) => count + item.inventory.length, 0),
    [facilities],
  );

  return (
    <div>
      <div className="flex flex-col gap-3 border-b border-line pb-5 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="eyebrow">Availability</p>
          <h2 className="mt-3 text-[1.85rem] font-semibold leading-tight tracking-[-0.035em] text-text sm:text-[2.05rem]">
            {loading ? "Memuat ketersediaan..." : `${facilities.length} fasilitas · ${totalInventoryRows} data ketersediaan`}
          </h2>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted" aria-live="polite">
          <Badge variant={hasSimulatedData ? "warning" : "success"}>{hasSimulatedData ? "Data demonstrasi" : "Data live/provider"}</Badge>
          <Badge variant="info">Pembaruan berkala</Badge>
          <span>{refreshing ? "Memperbarui..." : `Refresh sesuai provider · ${refreshSeconds} detik`}</span>
          {lastRefresh && <span>· Dicek {lastRefresh.toLocaleTimeString("id-ID")}</span>}
        </div>
      </div>


      <Card large className="mt-6 overflow-hidden rounded-[24px] border-line bg-white p-0 shadow-[0_14px_40px_rgba(16,32,29,.05)]">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-background px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary-light/70 text-primary-dark">
              <Search size={18} />
            </div>
            <p className="text-sm font-semibold text-text">Filter pencarian</p>
          </div>
        </div>

        <form onSubmit={submit} className="grid gap-4 px-6 py-6 md:grid-cols-2 lg:grid-cols-[1fr_1fr_1.2fr_1.45fr_auto] lg:items-end">
          <Select label="Blood Type" value={bloodType} onChange={(e) => setBloodType(e.target.value)} options={[{ value: "", label: "Semua" }, ...BLOOD_TYPES.map((value) => ({ value, label: value }))]} />
          <Select label="Rhesus" value={rhesus} onChange={(e) => setRhesus(e.target.value)} options={[{ value: "", label: "Semua" }, ...RHESUS_VALUES.map((value) => ({ value, label: value === "+" ? "Positif (+)" : "Negatif (-)" }))]} />
          <Input label="Location" value={city} maxLength={100} onChange={(e) => setCity(e.target.value)} placeholder="Contoh: Bandung" />
          <Input label="Facility" value={facility} maxLength={120} onChange={(e) => setFacility(e.target.value)} placeholder="Nama fasilitas" />
          <Button type="submit" isLoading={loading} loadingLabel="Mencari..." className="min-h-11 w-full lg:w-auto"><Search size={16} /> Search</Button>
          <div className="flex flex-wrap gap-2 md:col-span-2 lg:col-span-5"><Button type="button" variant="secondary" onClick={reset} disabled={loading}>Reset filter</Button></div>
        </form>
      </Card>

      <div className="mt-8" aria-live="polite" aria-busy={loading || refreshing || undefined}>
        {loading ? (
          <div className="grid gap-8 xl:grid-cols-2">{[0, 1, 2, 3].map((i) => <Card key={i} large><Skeleton className="h-6 w-2/3" /><Skeleton className="mt-3 h-4 w-1/2" /><Skeleton className="mt-6 h-24 w-full" /></Card>)}</div>
        ) : error ? (
          <Alert variant="error" title="Data belum dapat dimuat">{error}</Alert>
        ) : facilities.length === 0 ? (
          <Card large><Badge variant="neutral">No Availability</Badge><h2 className="mt-4 text-xl font-semibold">Belum ada fasilitas yang cocok</h2><p className="mt-2 text-sm text-secondary">Coba longgarkan filter lokasi, nama fasilitas, golongan darah, atau rhesus.</p></Card>
        ) : (
          <div className="grid gap-10 xl:grid-cols-2">
            {facilities.map((item) => (
              <Link key={item.id} href={`/blood/${encodeURIComponent(item.id)}`} aria-label={`${item.name} — buka detail ketersediaan darah`} className="group block h-full rounded-[24px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-4">
                <Card interactive large className="h-full min-w-0 rounded-[24px] border-line bg-white p-7 shadow-[0_14px_45px_rgba(16,32,29,.05)] transition-[transform,box-shadow,border-color] duration-300 group-hover:-translate-y-1 group-hover:border-primary/25 group-hover:shadow-[0_22px_60px_rgba(16,32,29,.09)]">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h2 className="text-xl font-semibold tracking-[-0.03em] text-text">{item.name}</h2>
                        {item.facility_type && <Badge variant="neutral">{item.facility_type}</Badge>}
                        <Badge variant={facilityDataMode(item) === "SIMULATED" ? "warning" : "success"}>{facilityDataMode(item) === "SIMULATED" ? "DEMO" : "LIVE"}</Badge>
                      </div>
                      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-secondary">
                        <span className="inline-flex min-w-0 items-center gap-1.5"><MapPin size={15} className="shrink-0" /> <span>{item.city} · {item.address}</span></span>
                        <span className="inline-flex items-center gap-1.5"><Clock3 size={15} className="shrink-0" /> Diperbarui {new Date(item.last_updated).toLocaleString("id-ID")}</span>
                      </div>
                    </div>
                    <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-line bg-background text-primary-dark transition-transform duration-300 group-hover:translate-x-1 group-hover:-translate-y-1" aria-hidden="true"><ArrowUpRight size={18} /></span>
                  </div>

                  <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
                    {item.inventory.map((inv) => (
                      <div key={`${inv.blood_type}${inv.rhesus}`} className="min-w-0 min-h-[124px] rounded-2xl border border-line bg-surface p-4">
                        <span className="block text-2xl font-semibold leading-none text-text">{inv.blood_type}{inv.rhesus}</span>
                        <div className="mt-3 min-h-7"><Badge variant={STATUS_VARIANT[inv.status]}>{STATUS_LABEL[inv.status]}</Badge></div>
                        <p className="mt-3 text-sm text-secondary">{inv.quantity ?? inv.units ?? "Belum tersedia"} unit</p>
                      </div>
                    ))}
                  </div>

                  <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4 text-xs leading-5 text-muted">
                    <span className="inline-flex items-center gap-1.5"><Database size={14} /> Sumber: {item.data_source}</span>
                    <span className="font-semibold text-primary-dark">Lihat detail fasilitas</span>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
