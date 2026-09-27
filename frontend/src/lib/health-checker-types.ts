import type { EvidenceView } from "@/components/evidence-card";
import type { SourceView } from "@/components/source-card";

export type Verdict = "SUPPORTED" | "PARTIALLY_SUPPORTED" | "INSUFFICIENT_EVIDENCE" | "CONTRADICTED";
export type EvidenceLevel = "HIGH" | "MODERATE" | "LOW" | "INSUFFICIENT";
export type InputType = "claim" | "article" | "url";

export type ScoreBreakdown = {
  source_authority: number;
  evidence_quality: number;
  recency: number;
  relevance: number;
  source_agreement: number;
  independent_publishers: number;
};

export type VerificationResponse = {
  claim: string;
  verdict: Verdict;
  result: Verdict;
  trust_score: number;
  evidence_confidence: number;
  confidence: number;
  score_breakdown: ScoreBreakdown;
  scoring_weights?: { source_authority: number; evidence_quality: number; recency: number; claim_relevance: number };
  evidence_level: EvidenceLevel;
  explanation: string;
  summary: string;
  why_this_result: string;
  reason: string;
  supporting_evidence: EvidenceView[];
  contradicting_evidence: EvidenceView[];
  neutral_evidence?: EvidenceView[];
  sources: SourceView[];
  sources_checked: number;
  last_checked: string;
  limitations: string[];
  demo_evidence: boolean;
  original_claim?: string | null;
  normalized_claim?: string | null;
  claim_id?: string | null;
  claim_type?: string | null;
  topic?: string | null;
  confidence_label?: "HIGH" | "MODERATE" | "LOW" | "INSUFFICIENT" | null;
  retrieval_notes?: string[];
};

export type HealthRun = VerificationResponse & {
  run_id: string;
  input_type: InputType;
  claims: VerificationResponse[];
  article?: { title?: string | null; publisher?: string | null; published_date?: string | null; author?: string | null; url?: string | null; text_length?: number } | null;
  retrieval_mode?: "curated" | "live+curated" | "url+curated" | "url+live+curated";
  source_outages?: string[];
  checked_claims?: number;
};

export const HEALTH_CHECKER_RESULT_STORAGE_KEY = "sehatin-health-checker-result";
export const HEALTH_CHECKER_REQUEST_CLAIM_STORAGE_KEY = "sehatin-health-checker-request-claim";
