"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { Check, Circle, Droplets, Leaf, Wheat, Drumstick, Apple } from "lucide-react";

export type FoodGroupKey = "carbohydrate" | "protein" | "vegetable" | "fruit" | "healthy-fat";

export const FOOD_GROUP_ORDER: FoodGroupKey[] = ["carbohydrate", "protein", "vegetable", "fruit", "healthy-fat"];

const GROUP_COPY: Record<FoodGroupKey, { label: string; examples: string }> = {
  carbohydrate: { label: "Karbohidrat", examples: "Nasi, kentang, oat, atau umbi" },
  protein: { label: "Protein", examples: "Telur, ayam, ikan, tahu, atau tempe" },
  vegetable: { label: "Sayuran", examples: "Sayuran yang sesuai tahap dan toleransi" },
  fruit: { label: "Buah", examples: "Buah yang sesuai tahap dan toleransi" },
  "healthy-fat": { label: "Lemak baik", examples: "Minyak, santan, atau sumber lemak sesuai panduan" },
};

export function normalizeFoodGroup(value: string): FoodGroupKey | null {
  const text = value.toLowerCase();
  if (/(karbo|carbo|grain|staple|cereal|nasi|beras)/.test(text)) return "carbohydrate";
  if (/(protein|animal|hewani|meat|egg|telur|fish|ayam|ikan)/.test(text)) return "protein";
  if (/(sayur|vegetable|veg)/.test(text)) return "vegetable";
  if (/(buah|fruit)/.test(text)) return "fruit";
  if (/(lemak|fat|oil|minyak)/.test(text)) return "healthy-fat";
  return null;
}

export function foodGroupsFrom(values: unknown): FoodGroupKey[] {
  if (!Array.isArray(values)) return [];
  const mapped = values.map((value) => normalizeFoodGroup(String(value))).filter(Boolean) as FoodGroupKey[];
  return Array.from(new Set(mapped));
}

export function FoodGroupIcon({ group, size = "md" }: { group: FoodGroupKey; size?: "sm" | "md" | "lg" }) {
  const sizeClass = size === "lg" ? "h-14 w-14" : size === "sm" ? "h-9 w-9" : "h-11 w-11";
  const iconSize = size === "lg" ? 27 : size === "sm" ? 17 : 21;
  const common = `${sizeClass} flex shrink-0 items-center justify-center rounded-full border border-line bg-white shadow-[0_6px_20px_rgba(18,75,61,.06)]`;
  return <span className={common} aria-hidden="true">
    {group === "carbohydrate" && <Wheat size={iconSize} className="text-amber-600" />}
    {group === "protein" && <Drumstick size={iconSize} className="text-orange-600" />}
    {group === "vegetable" && <Leaf size={iconSize} className="text-emerald-700" />}
    {group === "fruit" && <Apple size={iconSize} className="text-rose-500" />}
    {group === "healthy-fat" && <Droplets size={iconSize} className="text-yellow-600" />}
  </span>;
}

export function FoodGroupCard({ group, completed = false, onToggle, disabled = false, compact = false, recommended = true }: { group: FoodGroupKey; completed?: boolean; onToggle?: () => void; disabled?: boolean; compact?: boolean; recommended?: boolean }) {
  const copy = GROUP_COPY[group];
  const content = <>
    <FoodGroupIcon group={group} size={compact ? "sm" : "md"} />
    <span className="min-w-0 flex-1">
      <span className="block font-semibold text-text">{copy.label}</span>
      <span className="mt-0.5 block text-xs leading-5 text-secondary">{copy.examples}</span>
      {!compact && <span className="mt-1 block text-xs leading-5 text-muted">{recommended ? "Direkomendasikan dari meal guidance hari ini." : "Centang jika kelompok ini ada atau diberikan hari ini."}</span>}
    </span>
    <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full border transition-all duration-300 motion-reduce:transition-none ${completed ? "border-primary bg-primary text-white" : "border-slate-300 bg-white text-muted"}`} aria-hidden="true">
      {completed ? <Check size={15} /> : <Circle size={10} />}
    </span>
  </>;

  if (!onToggle) return <div className={`flex items-center gap-3 rounded-xl border p-3.5 transition-colors ${completed ? "border-primary/25 bg-primary-light/60" : "border-line bg-white"}`}>{content}</div>;
  return <button type="button" onClick={onToggle} disabled={disabled} className={`flex w-full items-center gap-3 rounded-xl border p-3.5 text-left transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 motion-reduce:transition-none ${completed ? "border-primary/25 bg-primary-light/60" : "border-line bg-white hover:border-primary/30 hover:shadow-sm"} disabled:cursor-not-allowed disabled:opacity-70`} aria-pressed={completed}>{content}</button>;
}

export function FoodGroupLegend({ groups }: { groups: FoodGroupKey[] }) {
  return <div className="flex flex-wrap gap-3">{groups.map((group) => <div key={group} className="inline-flex items-center gap-2"><FoodGroupIcon group={group} size="sm" /><span className="text-xs font-semibold text-secondary">{GROUP_COPY[group].label}</span></div>)}</div>;
}

function stageVisualAsset(stage: string) {
  if (stage === "mpasi") return "/images/sehatin/nutrition-mpasi-final.png";
  if (stage === "toddler") return "/images/sehatin/nutrition-toddler-final.png";
  return "/images/sehatin/nutrition-elderly-final.png";
}

const MENU_VISUALS = {
  mpasi: [
    "/images/sehatin/menu-library/mpasi-pumpkin-veg.webp",
    "/images/sehatin/menu-library/mpasi-soft-puree.webp",
    "/images/sehatin/menu-library/mpasi-banana-veg.webp",
    "/images/sehatin/menu-library/mpasi-vegetable.webp",
    "/images/sehatin/menu-library/mpasi-balanced.webp",
    "/images/sehatin/menu-library/mpasi-congee-chicken.webp",
    "/images/sehatin/menu-library/mpasi-puree-mixed.webp",
    "/images/sehatin/menu-library/mpasi-porridge-fresh.webp",
    "/images/sehatin/menu-library/mpasi-creamy-bowl.png",
    "/images/sehatin/menu-library/mpasi-protein-bowl.png",
    "/images/sehatin/menu-library/mpasi-rice-egg-spinach.webp",
    "/images/sehatin/menu-library/mpasi-fish-broccoli.webp",
    "/images/sehatin/menu-library/mpasi-beef-carrot.webp",
  ],
  toddler: [
    "/images/sehatin/menu-library/toddler-divided.webp",
    "/images/sehatin/menu-library/toddler-soft-tray.webp",
    "/images/sehatin/menu-library/toddler-main.webp",
    "/images/sehatin/menu-library/toddler-balanced.webp",
    "/images/sehatin/menu-library/toddler-fruit.webp",
    "/images/sehatin/menu-library/toddler-balanced-new.webp",
    "/images/sehatin/menu-library/toddler-tray-new.webp",
    "/images/sehatin/menu-library/toddler-colorful-new.webp",
    "/images/sehatin/menu-library/toddler-protein-plate.png",
    "/images/sehatin/menu-library/toddler-colorful-tray.png",
    "/images/sehatin/menu-library/toddler-fish-vegetable.webp",
    "/images/sehatin/menu-library/toddler-fruit-yogurt.webp",
    "/images/sehatin/menu-library/toddler-banana-sweet-potato.webp",
  ],
  elderly: [
    "/images/sehatin/menu-library/elderly-fish.webp",
    "/images/sehatin/menu-library/elderly-balanced.webp",
    "/images/sehatin/menu-library/elderly-soft.webp",
    "/images/sehatin/menu-library/elderly-warm.webp",
    "/images/sehatin/menu-library/elderly-light.webp",
    "/images/sehatin/menu-library/elderly-fish-new.webp",
    "/images/sehatin/menu-library/elderly-soft-new.webp",
    "/images/sehatin/menu-library/elderly-balanced-new.webp",
    "/images/sehatin/menu-library/elderly-breakfast-new.webp",
    "/images/sehatin/menu-library/elderly-soup-light.png",
    "/images/sehatin/menu-library/elderly-tempe-vegetable.webp",
    "/images/sehatin/menu-library/elderly-fruit-snack.webp",
  ],
} as const;

const MENU_VISUAL_KEY_MAP: Record<string, string> = {
  "mpasi_pumpkin": "/images/sehatin/menu-library/mpasi-pumpkin-veg.png",
  "mpasi_banana": "/images/sehatin/menu-library/mpasi-banana-veg.png",
  "mpasi_vegetable": "/images/sehatin/menu-library/mpasi-vegetable.png",
  "mpasi_protein": "/images/sehatin/menu-library/mpasi-protein-bowl.png",
  "mpasi_soft": "/images/sehatin/menu-library/mpasi-soft-puree.png",
  "toddler_protein": "/images/sehatin/menu-library/toddler-main.png",
  "toddler_fruit": "/images/sehatin/menu-library/toddler-fruit.png",
  "toddler_vegetable": "/images/sehatin/menu-library/toddler-divided.png",
  "toddler_balanced": "/images/sehatin/menu-library/toddler-balanced.png",
  "elderly_fish": "/images/sehatin/menu-library/elderly-fish.png",
  "elderly_soft": "/images/sehatin/menu-library/elderly-soft.png",
  "elderly_protein": "/images/sehatin/menu-library/elderly-warm.png",
  "elderly_balanced": "/images/sehatin/menu-library/elderly-balanced.png",
  "elderly_hydration": "/images/sehatin/menu-library/elderly-light.png",
};

function stableVisualIndex(value: string, length: number) {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) hash = (hash * 31 + value.charCodeAt(index)) >>> 0;
  return length ? hash % length : 0;
}

export function mealVisualAsset(stage: string, title: string, visualKey = "") {
  // The backend visual_key is intentionally coarse for backward compatibility.
  // Prefer distinctive ingredient combinations from the actual displayed menu
  // before falling back to that generic key, so the illustration matches the
  // menu text users are reading.
  const titleNormalized = title.toLowerCase();
  const normalized = `${visualKey} ${title}`.toLowerCase();

  if (stage === "mpasi") {
    if (/(telur|egg)/.test(titleNormalized) && /(bayam|spinach)/.test(titleNormalized)) {
      return "/images/sehatin/menu-library/mpasi-rice-egg-spinach.webp";
    }
    if (/(ikan|fish)/.test(titleNormalized) && /(brokoli|wortel|sayur)/.test(titleNormalized)) {
      return "/images/sehatin/menu-library/mpasi-fish-broccoli.webp";
    }
    if (/(daging|sapi|beef)/.test(titleNormalized)) {
      return "/images/sehatin/menu-library/mpasi-beef-carrot.webp";
    }
    if (/(labu|pumpkin)/.test(titleNormalized)) return "/images/sehatin/menu-library/mpasi-pumpkin-veg.webp";
    if (/(pisang|banana)/.test(titleNormalized)) return "/images/sehatin/menu-library/mpasi-banana-veg.webp";
    if (/(alpukat|mangga|pepaya|buah)/.test(titleNormalized)) return "/images/sehatin/menu-library/mpasi-creamy-bowl.png";
    if (/(brokoli|wortel|bayam|sayur)/.test(titleNormalized)) return "/images/sehatin/menu-library/mpasi-vegetable.webp";
    if (/(ayam|ikan|telur|tahu|tempe|protein)/.test(titleNormalized)) return "/images/sehatin/menu-library/mpasi-protein-bowl.png";
    if (/(bubur|puree|purée|lumat|lembut|kental|nasi tim|kentang)/.test(titleNormalized)) return "/images/sehatin/menu-library/mpasi-porridge-fresh.webp";

    const explicit = MENU_VISUAL_KEY_MAP[visualKey.trim().toLowerCase()];
    if (explicit) return explicit;
    return MENU_VISUALS.mpasi[stableVisualIndex(normalized, MENU_VISUALS.mpasi.length)];
  }

  if (stage === "toddler") {
    const snack = /(camilan|snack|selingan)/.test(titleNormalized);
    if (snack && /(yogurt|yoghurt|susu)/.test(titleNormalized) && /(buah|apel|pisang|pepaya|mangga|beri|berry|stroberi)/.test(titleNormalized)) {
      return "/images/sehatin/menu-library/toddler-fruit-yogurt.webp";
    }
    if (snack && /(pisang|banana)/.test(titleNormalized) && /(ubi|sweet potato)/.test(titleNormalized)) {
      return "/images/sehatin/menu-library/toddler-banana-sweet-potato.webp";
    }
    if (/(ikan|fish)/.test(titleNormalized)) return "/images/sehatin/menu-library/toddler-fish-vegetable.webp";
    if (/(telur|egg)/.test(titleNormalized)) return "/images/sehatin/menu-library/toddler-main.png";
    if (/(ayam|chicken|daging|meat|tahu|tofu|tempe)/.test(titleNormalized)) return "/images/sehatin/menu-library/toddler-balanced-new.webp";
    if (/(sup|berkuah|lunak|lembut)/.test(titleNormalized)) return "/images/sehatin/menu-library/toddler-soft-tray.webp";
    if (/(buah|apel|pisang|pepaya|mangga|beri|berry|stroberi)/.test(titleNormalized) && snack) return "/images/sehatin/menu-library/toddler-colorful-new.webp";
    if (/(buah|apel|pisang|pepaya|mangga|beri|berry|stroberi)/.test(titleNormalized)) return "/images/sehatin/menu-library/toddler-fruit.webp";
    if (/(brokoli|wortel|bayam|sayur|jagung)/.test(titleNormalized)) return "/images/sehatin/menu-library/toddler-divided.webp";
    if (/(nasi|oat|kentang|ubi|pasta|roti)/.test(titleNormalized)) return "/images/sehatin/menu-library/toddler-balanced-new.webp";

    const explicit = MENU_VISUAL_KEY_MAP[visualKey.trim().toLowerCase()];
    if (explicit) return explicit;
    return MENU_VISUALS.toddler[stableVisualIndex(normalized, MENU_VISUALS.toddler.length)];
  }

  const breakfast = /(sarapan|oatmeal|oat|havermut)/.test(titleNormalized);
  const snack = /(selingan|camilan|snack)/.test(titleNormalized);
  if (breakfast && /(telur|egg|buah|pisang|pepaya)/.test(titleNormalized)) return "/images/sehatin/menu-library/elderly-breakfast-new.webp";
  if (/(tempe|tahu)/.test(titleNormalized) && /(sayur|vegetable)/.test(titleNormalized) && !/(ayam|ikan|daging)/.test(titleNormalized)) {
    return "/images/sehatin/menu-library/elderly-tempe-vegetable.webp";
  }
  if (snack && /(buah|pisang|pepaya|apel|mangga)/.test(titleNormalized)) return "/images/sehatin/menu-library/elderly-fruit-snack.webp";
  if (/(ikan|fish|salmon)/.test(titleNormalized)) return "/images/sehatin/menu-library/elderly-fish.webp";
  if (/(bubur|lembut|lunak|lumat|mudah dikunyah|mudah ditelan)/.test(titleNormalized)) return "/images/sehatin/menu-library/elderly-soft-new.webp";
  if (/(sup|sop|sayur bening|kuah)/.test(titleNormalized)) return "/images/sehatin/menu-library/elderly-soup-light.png";
  if (/(ayam|tahu|tempe|protein|telur)/.test(titleNormalized)) return "/images/sehatin/menu-library/elderly-warm.webp";
  if (/(bayam|wortel|sayur|buah)/.test(titleNormalized)) return "/images/sehatin/menu-library/elderly-balanced-new.webp";
  if (/(teh|air|minum|cairan|hidrasi)/.test(titleNormalized)) return "/images/sehatin/menu-library/elderly-light.webp";

  const explicit = MENU_VISUAL_KEY_MAP[visualKey.trim().toLowerCase()];
  if (explicit) return explicit;
  return MENU_VISUALS.elderly[stableVisualIndex(normalized, MENU_VISUALS.elderly.length)];
}

function stageLabel(stage: string) {
  return stage === "mpasi" ? "MPASI" : stage === "toddler" ? "Toddler" : "Lansia";
}

function contextFromPath(pathname: string, compact: boolean) {
  if (pathname === "/nutrition") return compact ? "category" : "landing";
  if (pathname.includes("/result")) return "result";
  if (pathname.includes("/history")) return "history";
  if (pathname.includes("/program")) return "program";
  return "assessment";
}

function IllustrationFrame({ children, compact = false, bleed = false }: { children: ReactNode; compact?: boolean; bleed?: boolean }) {
  if (bleed) return <div className="relative aspect-[4/3] h-full w-full overflow-hidden rounded-[inherit]">{children}</div>;
  return <div className={`relative aspect-[4/3] w-full rounded-[24px] bg-[#eef7f2] ${compact ? "p-2.5" : "p-3"}`}>
    <div className="relative aspect-[4/3] h-full w-full overflow-hidden rounded-[18px] bg-white/65">
      {children}
    </div>
  </div>;
}

export function MealIllustration({ stage, title = "Panduan makan hari ini", groups = [], compact = false, fill = false, visualKey = "" }: { stage: string; title?: string; groups?: FoodGroupKey[]; compact?: boolean; fill?: boolean; visualKey?: string }) {
  const asset = mealVisualAsset(stage, title, visualKey);
  const label = stageLabel(stage);
  void groups;
  return <div role="img" aria-label={`Ilustrasi menu ${label}: ${title}`} data-menu-visual={asset} className={fill ? "absolute inset-0 overflow-hidden" : "relative h-full w-full overflow-hidden rounded-[inherit]"}>
    {/* eslint-disable-next-line @next/next/no-img-element */}
    <img
      src={asset}
      alt=""
      className={`absolute inset-0 h-full w-full ${compact ? "object-cover" : "object-cover"} object-center`}
      aria-hidden="true"
      onError={(event) => {
        const fallback = stageVisualAsset(stage);
        if (event.currentTarget.src.endsWith(fallback)) return;
        event.currentTarget.src = fallback;
      }}
    />
  </div>;
}

export function StageCompanionIllustration({ stage, compact = false }: { stage: string; compact?: boolean }) {
  const pathname = usePathname() ?? "";
  const context = contextFromPath(pathname, compact);
  const label = stageLabel(stage);
  const categoryAsset = stageVisualAsset(stage);

  if (context === "landing") return <div className="rounded-[30px] bg-[#eef7f2] p-4 shadow-[0_16px_44px_rgba(21,67,55,.06)]" role="img" aria-label="Grafis Nutrition Assistant umum tanpa figur manusia">
    <div className="relative aspect-[16/11] overflow-hidden rounded-[24px] bg-white/70">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/images/sehatin/nutrition-hero-general.webp" alt="" className="absolute inset-0 h-full w-full object-cover object-center" aria-hidden="true" />
    </div>
  </div>;

  if (context === "category") return <div role="img" aria-label={`Grafis kategori nutrisi ${label} tanpa figur manusia`} className="w-full">
    <IllustrationFrame compact>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={categoryAsset} alt="" className="absolute inset-0 h-full w-full object-cover object-center" aria-hidden="true" />
    </IllustrationFrame>
  </div>;

  void compact;
  return <div role="img" aria-label={`Grafis ${context} nutrisi ${label} tanpa figur manusia`} className="relative h-full w-full overflow-hidden rounded-[inherit]">
    {/* eslint-disable-next-line @next/next/no-img-element */}
    <img src={categoryAsset} alt="" className="absolute inset-0 h-full w-full object-cover object-center" aria-hidden="true" />
  </div>;
}

export function FoodGroupChecklist({ groups, states, onToggle, disabled = false }: { groups: FoodGroupKey[]; states: boolean[]; onToggle?: (index: number) => void; disabled?: boolean }) {
  return <div className="space-y-2.5">{groups.map((group, index) => <FoodGroupCard key={`${group}-${index}`} group={group} completed={states[index] ?? false} disabled={disabled} onToggle={onToggle ? () => onToggle(index) : undefined} />)}</div>;
}
