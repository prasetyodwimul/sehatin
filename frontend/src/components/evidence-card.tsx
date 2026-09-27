import { Badge } from "@/components/ui";
import { ExternalLink, FileText } from "lucide-react";

export type EvidenceView = {
  id: string;
  title: string;
  source: string;
  source_type: string;
  publication_date: string;
  retrieved_at: string;
  url: string;
  stance: "support" | "contradict" | "neutral";
  excerpt: string;
  authority_level: number;
  authority_score: number;
  evidence_quality_score: number;
  recency_score: number;
  relevance_score: number;
  weighted_score: number;
  demo: boolean;
  source_id?: string | null;
  verified?: boolean;
  provider?: string;
  trace_note?: string | null;
};

function humanSourceType(value: string) {
  const labels: Record<string, string> = {
    government: "Sumber pemerintah",
    international_health_agency: "Lembaga kesehatan internasional",
    professional_medical_org: "Organisasi medis",
    peer_reviewed: "Artikel ilmiah",
  };
  return labels[value] ?? value.replaceAll("_", " ");
}

export function EvidenceCard({ evidence }: { evidence: EvidenceView }) {
  const stance = evidence.stance === "support" ? "Mendukung" : evidence.stance === "contradict" ? "Berbeda" : "Konteks saja";
  const variant = evidence.stance === "support" ? "success" : evidence.stance === "contradict" ? "error" : "neutral";
  const accent = evidence.stance === "support" ? "border-success/15 bg-success/[.025]" : evidence.stance === "contradict" ? "border-error/15 bg-error/[.025]" : "border-line bg-white";
  return (
    <article className={`my-4 overflow-hidden rounded-2xl border p-5 ${accent}`}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex min-w-0 items-start gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white text-primary-dark shadow-sm"><FileText size={17} aria-hidden="true" /></span>
          <div className="min-w-0">
            <p className="text-xs font-semibold text-muted">{evidence.source} · {humanSourceType(evidence.source_type)}</p>
            <h4 className="mt-1 text-base font-bold leading-6 tracking-[-0.015em]">{evidence.title}</h4>
          </div>
        </div>
        <Badge variant={variant}>{stance}</Badge>
      </div>
      <blockquote className="mt-4 rounded-xl bg-white/80 p-4 text-sm leading-6 text-secondary">“{evidence.excerpt}”</blockquote>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <div className="text-xs text-muted">{evidence.publication_date || "Tanggal tidak tersedia"}</div>
        <a href={evidence.url} target="_blank" rel="noopener noreferrer" className="inline-flex min-h-9 items-center gap-2 rounded-full border border-line bg-white px-3.5 text-xs font-bold text-primary-dark transition hover:border-primary/40 hover:bg-primary-light">
          Lihat sumber <ExternalLink size={13} aria-hidden="true" />
        </a>
      </div>
      {evidence.trace_note && <p className="mt-3 text-xs leading-5 text-muted">Catatan: {evidence.trace_note}</p>}
    </article>
  );
}
