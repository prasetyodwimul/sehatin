export type TrustBreakdown = {
  source_authority: number;
  evidence_quality: number;
  recency: number;
  relevance: number;
  source_agreement: number;
  independent_publishers: number;
};

const ITEMS = [
  ["Source Authority", "source_authority", "Siapa yang menerbitkan evidence dan seberapa kuat otoritas relatifnya."],
  ["Evidence Quality", "evidence_quality", "Kualitas evidence yang tersedia dalam corpus."],
  ["Recency", "recency", "Seberapa mutakhir evidence dibandingkan konteks analisis."],
  ["Claim Relevance", "relevance", "Seberapa dekat evidence menjawab klaim yang dimasukkan."],
  ["Source Agreement", "source_agreement", "Seberapa konsisten arah evidence dari sumber independen."],
] as const;

export function TrustVisualization({ breakdown }: { breakdown: TrustBreakdown }) {
  return (
    <div className="border-y border-line">
      {ITEMS.map(([label, key, description]) => {
        const value = Math.max(0, Math.min(100, Math.round(breakdown[key] * 100)));
        return (
          <div key={key} className="grid gap-3 border-b border-line py-5 last:border-b-0 md:grid-cols-[180px_1fr_70px] md:items-center">
            <div><p className="text-sm font-semibold text-text">{label}</p><p className="mt-1 text-xs leading-5 text-muted md:hidden">{description}</p></div>
            <div>
              <div className="h-2 overflow-hidden rounded-full bg-[#e7eeec]" role="progressbar" aria-label={label} aria-valuenow={value} aria-valuemin={0} aria-valuemax={100}><div className="h-full rounded-full bg-primary transition-[width] duration-700" style={{ width: `${value}%` }} /></div>
              <p className="mt-2 hidden text-xs leading-5 text-muted md:block">{description}</p>
            </div>
            <p className="text-right text-xl font-semibold tracking-[-0.03em]">{value}<span className="text-xs font-normal text-muted">/100</span></p>
          </div>
        );
      })}
      <div className="py-5 text-xs leading-5 text-muted">Independent publishers: <strong className="text-text">{breakdown.independent_publishers}</strong>. Publisher diversity membantu confidence verdict, bukan menjadi jaminan kebenaran.</div>
    </div>
  );
}
