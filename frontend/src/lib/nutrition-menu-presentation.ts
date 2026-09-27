export function naturalList(items: string[]) {
  const values = items.map((item) => item.trim()).filter(Boolean);
  if (values.length <= 1) return values[0] ?? "";
  if (values.length === 2) return `${values[0]} dan ${values[1]}`;
  return `${values.slice(0, -1).join(", ")}, dan ${values[values.length - 1]}`;
}

function tidyPart(value: string) {
  return value
    .replace(/\s+/g, " ")
    .replace(/^[-–—,.;\s]+|[-–—,.;\s]+$/g, "")
    .trim();
}

function trimSentence(sentence: string, maxLength = 112) {
  const clean = sentence.replace(/\s+/g, " ").trim();
  if (clean.length <= maxLength) return clean;
  const withoutStop = clean.replace(/[.!?]$/, "");
  const boundary = withoutStop.lastIndexOf(",", maxLength - 8);
  if (boundary >= 48) return `${withoutStop.slice(0, boundary)}, dan lainnya.`;
  const words = withoutStop.slice(0, maxLength - 4).trimEnd().split(" ");
  if (words.length > 1) words.pop();
  return `${words.join(" ")}…`;
}

/**
 * Presentation-only menu formatter. It never mutates the underlying menu data.
 * Raw separators from engine/data storage are converted into natural Indonesian copy.
 */
export function formatMenuDisplayTitle(stage: string, value: unknown) {
  const source = typeof value === "string" && value.trim() ? value : "Menu sesuai panduan";
  const original = source.replace(/\s+/g, " ").trim();

  // Context notes belong in supporting copy, not in the large menu title.
  const withoutContext = original.split(/\s*Catatan konteks\s*:\s*/i)[0]?.trim() || original;
  const withoutCategorySuffix = withoutContext.replace(/\s*[:\-–—]\s*(MPASI|Toddler|Lansia)\s*$/i, "").trim();

  const normalized = withoutCategorySuffix
    .replace(/\s*\+\s*/g, ", ")
    .replace(/\s*;\s*/g, ", ")
    .replace(/\s*:\s*/g, ", ")
    .replace(/\s*,\s*,+/g, ", ")
    .replace(/\s+/g, " ")
    .trim();

  const prefixMatch = normalized.match(/^(Sarapan|Makan siang|Makan malam|Makan utama|Camilan|Snack|Menu)\s*,\s*(.+)$/i);
  const rawPrefix = prefixMatch?.[1]?.trim();
  const prefix = rawPrefix?.toLowerCase() === "menu" ? undefined : rawPrefix;
  const body = tidyPart(prefixMatch?.[2] ?? normalized);
  const parts = body.split(/\s*,\s*/).map(tidyPart).filter(Boolean);
  const maxParts = stage === "toddler" ? 5 : 4;
  const concise = parts.slice(0, maxParts);

  if (!concise.length) return "Menu sesuai panduan.";

  let sentence: string;
  if (concise.length === 1) {
    const item = concise[0];
    const capitalized = `${item.charAt(0).toUpperCase()}${item.slice(1)}`;
    sentence = prefix ? `${prefix} berupa ${item}.` : `${capitalized}.`;
  } else if (prefix) {
    sentence = `${prefix} berupa ${naturalList(concise)}.`;
  } else {
    const first = `${concise[0].charAt(0).toUpperCase()}${concise[0].slice(1)}`;
    sentence = `${first} dengan ${naturalList(concise.slice(1))}.`;
  }

  // Guarantee raw data punctuation does not leak back into the display title.
  return trimSentence(sentence.replace(/[+:]/g, ""));
}
