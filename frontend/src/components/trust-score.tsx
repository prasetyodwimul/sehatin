import { MotionNumber } from "@/components/motion";

type ScoreKind = "support" | "confidence";
function level(score: number) { return score >= 75 ? "HIGH" : score >= 45 ? "MODERATE" : "LOW"; }
function explanation(score: number, kind: ScoreKind) {
  const label = level(score);
  if (kind === "confidence") {
    if (label === "HIGH") return "Evidence relatif kuat dan konsisten untuk mendasari verdict.";
    if (label === "MODERATE") return "Evidence memberi arah yang cukup, dengan keterbatasan penting.";
    return "Evidence yang mendasari verdict masih terbatas atau kurang konsisten.";
  }
  if (label === "HIGH") return "Evidence yang tersedia memberi dukungan kuat terhadap klaim.";
  if (label === "MODERATE") return "Evidence memberi dukungan sebagian atau bercampur terhadap klaim.";
  return "Evidence memberi sedikit atau tidak ada dukungan. Trust Score rendah dapat berpasangan dengan confidence tinggi pada verdict CONTRADICTED.";
}

export function TrustScore({ score, title = "Trust Score", kind = "support" }: { score: number; title?: string; kind?: ScoreKind }) {
  const label = level(score);
  return (
    <div className="border-t-2 border-primary pt-5">
      <div className="flex items-start justify-between gap-4"><p className="text-xs font-black uppercase tracking-[0.14em] text-muted">{title}</p><span className="text-xs font-black tracking-[0.14em] text-primary-dark">{label}</span></div>
      <p className="mt-5 text-6xl font-semibold tracking-[-0.06em] text-text"><MotionNumber value={score} /><span className="ml-1 text-lg font-normal text-muted">/100</span></p>
      <div className="mt-5 h-2 overflow-hidden rounded-full bg-line" aria-hidden="true"><div className="h-full rounded-full bg-primary" style={{ width: `${Math.max(0, Math.min(100, score))}%` }} /></div>
      <p className="mt-4 text-xs leading-5 text-muted">{explanation(score, kind)}</p>
    </div>
  );
}
