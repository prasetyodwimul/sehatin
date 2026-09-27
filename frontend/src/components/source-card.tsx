export type SourceView = {
  name: string;
  title: string;
  source_type: string;
  publication_date: string;
  url: string;
  last_checked: string;
  verified?: boolean;
  authority_level?: number | null;
  provider?: string;
  why_considered?: string | null;
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

export function SourceCard({ source }: { source: SourceView }) {
  return (
    <article className="border-t border-line py-5">
      <div className="flex flex-wrap items-center gap-2 text-[11px] font-black uppercase tracking-[0.12em] text-primary-dark">
        <span>Sumber</span><span className="text-muted">·</span><span className="text-muted">{humanSourceType(source.source_type)}</span>
        {source.verified !== false && <><span className="text-muted">·</span><span>Terverifikasi</span></>}
      </div>
      <h3 className="mt-3 text-lg font-semibold tracking-[-0.02em]">{source.name}</h3>
      <p className="mt-1 text-sm leading-6 text-secondary">{source.title}</p>
      {source.why_considered && <p className="mt-3 text-xs leading-5 text-secondary">{source.why_considered}</p>}
      <p className="mt-3 text-xs text-muted">Diterbitkan {source.publication_date || "Tanggal tidak tersedia"}</p>
      <a href={source.url} target="_blank" rel="noopener noreferrer" className="mt-4 inline-flex min-h-10 items-center text-sm font-semibold text-primary-dark underline underline-offset-4">Lihat sumber ↗</a>
    </article>
  );
}
