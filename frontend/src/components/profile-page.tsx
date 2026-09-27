"use client";

import Link from "next/link";
import { ChangeEvent, useCallback, useEffect, useMemo, useState } from "react";
import { ArrowRight, Camera, CheckCircle2, LogOut, Pencil, Save, Trash2, UserRound, X } from "lucide-react";
import { AuthGate } from "@/components/auth-gate";
import { useAuth } from "@/components/auth-provider";
import { Alert, Badge, Button, Input, ProgressBar, Textarea } from "@/components/ui";
import { updateAccountProfile } from "@/lib/auth";
import { formatPercent, listNutritionPrograms, type ProgramSummary } from "@/lib/nutrition-program";

const AVATAR_TYPES = new Set(["image/png", "image/jpeg", "image/webp"]);
const MAX_AVATAR_BYTES = 750_000;
const MAX_AVATAR_DATA_URL_CHARS = 44_000;
const AVATAR_OUTPUT_SIZE = 256;

function profileName(user: { email: string; full_name?: string | null; display_name?: string | null }) {
  return user.display_name?.trim() || user.full_name?.trim() || user.email.split("@")[0];
}

type DecodedAvatar = {
  source: CanvasImageSource;
  width: number;
  height: number;
  cleanup: () => void;
};

function fileToDataUrl(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => typeof reader.result === "string" ? resolve(reader.result) : reject(new Error("Foto belum dapat dibaca."));
    reader.onerror = () => reject(new Error("Foto belum dapat dibaca."));
    reader.readAsDataURL(file);
  });
}

async function decodeAvatarImage(file: File): Promise<DecodedAvatar> {
  if (typeof createImageBitmap === "function") {
    try {
      const bitmap = await createImageBitmap(file);
      if (bitmap.width > 0 && bitmap.height > 0) {
        return {
          source: bitmap,
          width: bitmap.width,
          height: bitmap.height,
          cleanup: () => bitmap.close(),
        };
      }
      bitmap.close();
    } catch {
      // Continue to the HTMLImageElement fallback below.
    }
  }

  const dataUrl = await fileToDataUrl(file);
  const image = new Image();
  image.decoding = "async";
  image.src = dataUrl;
  try {
    if (typeof image.decode === "function") {
      await image.decode();
    } else {
      await new Promise<void>((resolve, reject) => {
        image.onload = () => resolve();
        image.onerror = () => reject(new Error("Foto belum dapat dibaca."));
      });
    }
  } catch {
    throw new Error("Format foto tidak dapat dibaca browser. Gunakan PNG, JPG, atau WebP standar.");
  }

  const width = image.naturalWidth || image.width;
  const height = image.naturalHeight || image.height;
  if (!width || !height) throw new Error("Foto belum dapat dibaca.");
  return { source: image, width, height, cleanup: () => undefined };
}

async function readAvatarFile(file: File) {
  const normalizedType = file.type.toLowerCase();
  const extension = file.name.split(".").pop()?.toLowerCase() ?? "";
  const supportedByType = AVATAR_TYPES.has(normalizedType);
  const supportedByExtension = ["png", "jpg", "jpeg", "webp"].includes(extension);
  if (!supportedByType && !supportedByExtension) throw new Error("Gunakan foto PNG, JPG, atau WebP.");
  if (file.size > MAX_AVATAR_BYTES) throw new Error("Ukuran foto maksimal 750 KB.");

  const decoded = await decodeAvatarImage(file);
  try {
    const sourceWidth = decoded.width;
    const sourceHeight = decoded.height;
    const cropSize = Math.min(sourceWidth, sourceHeight);
    const sourceX = Math.max(0, (sourceWidth - cropSize) / 2);
    const sourceY = Math.max(0, (sourceHeight - cropSize) / 2);
    const canvas = document.createElement("canvas");
    const context = canvas.getContext("2d", { alpha: false });
    if (!context) throw new Error("Foto belum dapat diproses di browser ini.");

    const sizes = [AVATAR_OUTPUT_SIZE, 224, 192, 160, 128];
    const qualities = [0.82, 0.72, 0.62, 0.52, 0.42];
    for (const size of sizes) {
      canvas.width = size;
      canvas.height = size;
      context.fillStyle = "#ffffff";
      context.fillRect(0, 0, size, size);
      context.drawImage(decoded.source, sourceX, sourceY, cropSize, cropSize, 0, 0, size, size);
      for (const quality of qualities) {
        const optimized = canvas.toDataURL("image/webp", quality);
        if (optimized.startsWith("data:image/webp") && optimized.length <= MAX_AVATAR_DATA_URL_CHARS) {
          return optimized;
        }
      }
    }
  } finally {
    decoded.cleanup();
  }
  throw new Error("Foto terlalu kompleks untuk profil. Coba foto lain dengan ukuran lebih kecil.");
}

export function ProfilePage() {
  const { status, user, logout, refreshAuth } = useAuth();
  const [programs, setPrograms] = useState<ProgramSummary[]>([]);
  const [loadingPrograms, setLoadingPrograms] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [authOpen, setAuthOpen] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);
  const [editingProfile, setEditingProfile] = useState(false);
  const [fullName, setFullName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [bio, setBio] = useState("");
  const [avatarDataUrl, setAvatarDataUrl] = useState<string | null>(null);

  const loadPrograms = useCallback(async () => {
    setLoadingPrograms(true);
    setError("");
    try {
      setPrograms(await listNutritionPrograms());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Riwayat program belum dapat dimuat.");
    } finally {
      setLoadingPrograms(false);
    }
  }, []);

  useEffect(() => {
    if (status === "authenticated") void loadPrograms();
    if (status === "unauthenticated") setPrograms([]);
  }, [loadPrograms, status, user?.id]);

  useEffect(() => {
    if (!user) return;
    setFullName(user.full_name ?? "");
    setDisplayName(user.display_name ?? "");
    setBio(user.bio ?? "");
    setAvatarDataUrl(user.avatar_data_url ?? null);
  }, [user]);

  const active = useMemo(() => programs.find((item) => item.status === "ACTIVE" && !item.completed_at) ?? null, [programs]);
  const history = useMemo(() => programs.filter((item) => item.status !== "ACTIVE" || Boolean(item.completed_at)), [programs]);
  const completeness = useMemo(() => {
    if (!user) return 0;
    const fields = [fullName.trim(), displayName.trim(), bio.trim(), avatarDataUrl, user.email];
    return Math.round((fields.filter(Boolean).length / fields.length) * 100);
  }, [avatarDataUrl, bio, displayName, fullName, user]);

  const handleAvatar = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setError("");
    setSuccess("");
    try {
      setAvatarDataUrl(await readAvatarFile(file));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Foto belum dapat diproses.");
    }
  };

  const cancelProfileEdit = () => {
    const currentUser = user;
    if (!currentUser) return;
    setFullName(currentUser.full_name ?? "");
    setDisplayName(currentUser.display_name ?? "");
    setBio(currentUser.bio ?? "");
    setAvatarDataUrl(currentUser.avatar_data_url ?? null);
    setError("");
    setEditingProfile(false);
  };

  const saveProfile = async () => {
    const currentUser = user;
    if (!currentUser) return;
    setSavingProfile(true);
    setError("");
    setSuccess("");
    try {
      const payload = {
        full_name: fullName.trim() || null,
        display_name: displayName.trim() || null,
        bio: bio.trim() || null,
        ...(avatarDataUrl !== (currentUser.avatar_data_url ?? null) ? { avatar_data_url: avatarDataUrl } : {}),
      };
      await updateAccountProfile(payload);
      await refreshAuth();
      setSuccess("Profil berhasil diperbarui.");
      setEditingProfile(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Profil belum dapat disimpan.");
    } finally {
      setSavingProfile(false);
    }
  };

  if (status === "loading") return <div className="min-h-[320px] animate-pulse border-y border-line bg-surface" aria-label="Memuat profile" />;

  if (status === "unauthenticated" || !user) {
    return (
      <>
        <div>
          <header className="border-b border-line pb-9">
            <p className="eyebrow">Guest profile</p>
            <h1 className="mt-3 text-4xl font-semibold tracking-[-0.045em] md:text-5xl">Profil sementara untuk penggunaan publik.</h1>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-secondary">Kamu sedang menggunakan SEHATIN sebagai guest. Assessment dan rekomendasi publik tetap dapat digunakan, tetapi program dan riwayat tidak disimpan ke akun sampai kamu login atau membuat akun.</p>
          </header>

          <section className="grid gap-8 border-b border-line py-9 md:grid-cols-[220px_1fr]">
            <div><p className="eyebrow">Session</p></div>
            <dl className="grid gap-6 sm:grid-cols-2">
              <div><dt className="text-xs font-bold uppercase tracking-[0.12em] text-muted">Status</dt><dd className="mt-2 text-lg font-semibold">Guest</dd></div>
              <div><dt className="text-xs font-bold uppercase tracking-[0.12em] text-muted">Persistence</dt><dd className="mt-2 text-lg font-semibold">Tidak tersimpan ke akun</dd></div>
            </dl>
          </section>

          <section className="grid gap-8 border-b border-line py-9 md:grid-cols-[220px_1fr]">
            <div><p className="eyebrow">Nutrition</p></div>
            <div>
              <p className="font-semibold">Fitur publik tetap tersedia.</p>
              <p className="mt-2 max-w-2xl text-sm leading-7 text-secondary">Kamu bisa menjalankan assessment dan melihat hasil rekomendasi. Saat ingin menyimpan Guided Nutrition Program, SEHATIN akan meminta login/register.</p>
              <Link href="/nutrition" className="mt-5 inline-flex min-h-11 items-center rounded-full border border-primary/40 px-5 text-sm font-semibold text-primary-dark">Buka Nutrition <ArrowRight className="ml-2" size={16} /></Link>
            </div>
          </section>

          <div className="flex flex-wrap gap-3 pt-8">
            <Button size="lg" onClick={() => setAuthOpen(true)}>Sign in / Create account <ArrowRight size={17} /></Button>
          </div>
        </div>
        <AuthGate open={authOpen} onClose={() => setAuthOpen(false)} onAuthenticated={async () => { setAuthOpen(false); await loadPrograms(); }} />
      </>
    );
  }

  const fallbackInitial = profileName(user).slice(0, 1).toUpperCase();

  return (
    <div>
      <header className="border-b border-line pb-9">
        <p className="eyebrow">Your SEHATIN profile</p>
        <div className="mt-4 flex flex-col gap-6 sm:flex-row sm:items-center">
          <div className="relative h-24 w-24 shrink-0 overflow-hidden rounded-full border border-line bg-primary-light shadow-[0_12px_35px_rgba(15,118,110,.12)]">
            {avatarDataUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={avatarDataUrl} alt={`Foto profil ${profileName(user)}`} className="h-full w-full object-cover" />
            ) : (
              <div className="flex h-full w-full items-center justify-center text-3xl font-black text-primary-dark" aria-label="Avatar tanpa foto">{fallbackInitial}</div>
            )}
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="min-w-0 text-4xl font-semibold tracking-[-0.045em] md:text-5xl">{profileName(user)}</h1>
              {!editingProfile && (
                <button
                  type="button"
                  onClick={() => { setError(""); setSuccess(""); setEditingProfile(true); }}
                  className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-line bg-white text-secondary transition-colors hover:border-primary/40 hover:text-primary-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
                  aria-label="Edit profil"
                  title="Edit profil"
                >
                  <Pencil size={17} />
                </button>
              )}
            </div>
            <p className="mt-2 text-sm text-secondary">{user.email}</p>
            <div className="mt-3 inline-flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-800"><CheckCircle2 size={14} /> Profil {completeness}% lengkap</div>
          </div>
        </div>
        <p className="mt-5 max-w-2xl text-sm leading-7 text-secondary">Kelola identitas akun dan Guided Nutrition yang tersimpan. Profil ini bukan rekam medis dan tidak digunakan untuk membuat diagnosis.</p>
      </header>

      {error && <div className="mt-6"><Alert variant="error">{error}</Alert></div>}
      {success && <div className="mt-6"><Alert variant="success">{success}</Alert></div>}

      {editingProfile && (
        <section className="grid gap-8 border-b border-line py-9 lg:grid-cols-[220px_1fr]">
          <div>
            <p className="eyebrow">Edit profile</p>
            <p className="mt-3 text-sm leading-6 text-secondary">Ubah foto, nama, atau bio. Data ini hanya digunakan untuk personalisasi akun SEHATIN.</p>
          </div>

          <div className="grid gap-7 rounded-2xl border border-primary/20 bg-surface p-5 shadow-[0_16px_45px_rgba(15,118,110,.06)] sm:p-7">
            <div className="flex items-center justify-between gap-4 border-b border-line pb-5">
              <div>
                <p className="text-lg font-semibold">Edit profil</p>
                <p className="mt-1 text-xs leading-5 text-muted">Ubah identitas yang tampil di akun SEHATIN.</p>
              </div>
              <button type="button" onClick={cancelProfileEdit} className="flex h-10 w-10 items-center justify-center rounded-full border border-line bg-white text-secondary hover:text-text" aria-label="Tutup edit profil"><X size={17} /></button>
            </div>

            <div className="grid gap-6 md:grid-cols-[180px_1fr] md:items-center">
              <div className="flex items-center gap-4 md:block">
                <div className="h-28 w-28 overflow-hidden rounded-full border border-line bg-primary-light">
                  {avatarDataUrl ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={avatarDataUrl} alt="Preview foto profil" className="h-full w-full object-cover" />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center text-primary-dark"><UserRound size={36} /></div>
                  )}
                </div>
              </div>
              <div>
                <p className="text-sm font-semibold">Foto profil</p>
                <p className="mt-1 text-xs leading-5 text-muted">PNG, JPG, atau WebP. Maksimal 750 KB; foto otomatis dioptimalkan untuk profil.</p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <label className="inline-flex min-h-10 cursor-pointer items-center gap-2 rounded-full border border-line bg-white px-4 text-sm font-semibold hover:border-primary/40">
                    <Camera size={16} /> Pilih foto
                    <input type="file" className="sr-only" accept="image/png,image/jpeg,image/webp" onChange={handleAvatar} />
                  </label>
                  {avatarDataUrl && <button type="button" onClick={() => setAvatarDataUrl(null)} className="inline-flex min-h-10 items-center gap-2 rounded-full border border-line px-4 text-sm font-semibold text-secondary hover:text-text"><Trash2 size={15} /> Hapus foto</button>}
                </div>
              </div>
            </div>

            <div className="grid gap-5 md:grid-cols-2">
              <Input label="Nama lengkap" value={fullName} onChange={(event) => setFullName(event.target.value)} maxLength={120} placeholder="Contoh: Bilal Rizky Akbar" autoComplete="name" />
              <Input label="Nama tampilan" value={displayName} onChange={(event) => setDisplayName(event.target.value)} maxLength={80} placeholder="Nama yang tampil di SEHATIN" />
            </div>
            <Textarea label="Bio singkat" value={bio} onChange={(event) => setBio(event.target.value)} maxLength={240} rows={4} placeholder="Ceritakan sedikit tentang diri kamu (opsional)." helperText={`${bio.length}/240 karakter`} />
            <div className="flex flex-wrap items-center justify-between gap-4 border-t border-line pt-5">
              <p className="text-xs leading-5 text-muted">Perubahan nama, foto, dan bio akan tersimpan ke akun ini.</p>
              <div className="flex flex-wrap gap-2">
                <Button variant="secondary" onClick={cancelProfileEdit} disabled={savingProfile}><X size={16} /> Batal</Button>
                <Button onClick={saveProfile} isLoading={savingProfile} loadingLabel="Menyimpan..."><Save size={16} /> Simpan profil</Button>
              </div>
            </div>
          </div>
        </section>
      )}

      <section className="grid gap-8 border-b border-line py-9 md:grid-cols-[220px_1fr]">
        <div><p className="eyebrow">Account</p></div>
        <dl className="grid gap-6 sm:grid-cols-3">
          <div><dt className="text-xs font-bold uppercase tracking-[0.12em] text-muted">Email</dt><dd className="mt-2 break-all text-lg font-semibold">{user.email}</dd><p className="mt-1 text-xs text-muted">Email login tidak diubah dari halaman ini.</p></div>
          <div><dt className="text-xs font-bold uppercase tracking-[0.12em] text-muted">Member since</dt><dd className="mt-2 text-lg font-semibold">{new Date(user.created_at).toLocaleDateString("id-ID")}</dd></div>
          <div><dt className="text-xs font-bold uppercase tracking-[0.12em] text-muted">Account status</dt><dd className="mt-2 text-lg font-semibold">Active</dd></div>
        </dl>
      </section>

      <section className="grid gap-8 border-b border-line py-9 md:grid-cols-[220px_1fr]">
        <div><p className="eyebrow">Nutrition guidance</p></div>
        <div>
          {loadingPrograms ? (
            <div className="h-36 animate-pulse rounded-lg bg-surface" aria-label="Memuat program" />
          ) : active ? (
            <div className="rounded-2xl border border-line bg-surface p-6">
              <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-2xl font-semibold tracking-[-0.03em]">{active.title}</h2><Badge variant="info">ACTIVE</Badge></div>
              <p className="mt-2 text-sm text-secondary">Day {active.current_day} of {active.duration_days}</p>
              <div className="mt-6 max-w-xl"><ProgressBar value={active.progress_percent} label={`${formatPercent(active.progress_percent)}% program progress`} /></div>
              <Link href={`/nutrition/program/${active.id}/today`} className="mt-6 inline-flex min-h-11 items-center rounded-full bg-text px-5 text-sm font-semibold text-white">Continue Program <ArrowRight className="ml-2" size={16} /></Link>
            </div>
          ) : (
            <div className="border-y border-line py-7"><p className="font-semibold">No active nutrition program.</p><Link href="/nutrition" className="mt-3 inline-flex text-sm font-semibold text-primary-dark">Start New Assessment →</Link></div>
          )}
        </div>
      </section>

      <section className="grid gap-8 border-b border-line py-9 md:grid-cols-[220px_1fr]">
        <div><p className="eyebrow">Program history</p></div>
        <div>
          {history.length ? (
            <div className="divide-y divide-line border-y border-line">
              {history.map((program) => (
                <Link key={program.id} href={`/nutrition/program/${program.id}/history`} className="grid gap-3 py-5 sm:grid-cols-[1fr_auto] sm:items-center">
                  <div><p className="font-semibold">{program.title}</p><p className="mt-1 text-sm text-secondary">{program.stage} · {program.days_completed}/{program.duration_days} days · {program.progress_percent}%</p></div>
                  <Badge variant={program.status === "CANCELLED" ? "neutral" : "success"}>{program.status}</Badge>
                </Link>
              ))}
            </div>
          ) : <p className="text-sm text-secondary">Belum ada program history.</p>}
        </div>
      </section>

      <div className="flex flex-wrap items-center justify-between gap-4 pt-8">
        <p className="text-sm text-secondary">Logout mengakhiri sesi browser, tetapi program tersimpan tetap ada di database dan kembali setelah login lagi.</p>
        <Button variant="secondary" onClick={async () => { try { await logout(); } catch (err) { setError(err instanceof Error ? err.message : "Logout belum dapat diproses."); } }}><LogOut size={16} /> Logout</Button>
      </div>
    </div>
  );
}
