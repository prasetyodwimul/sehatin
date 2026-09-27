export const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");
export const SESSION_EXPIRED_EVENT = "sehatin:session-expired";

export class ApiError extends Error {
  status: number;
  code?: string;

  constructor(message: string, status = 0, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

type ApiErrorBody = {
  error?: { code?: string; message?: string };
  detail?: string | Array<{ msg?: string }>;
  message?: string;
};

type ApiFetchOptions = RequestInit & { timeoutMs?: number };

function requireApiBase() {
  // Browser menggunakan proxy same-origin agar cookie session
  // tidak bergantung pada third-party/cross-site cookie iOS.
  if (typeof window !== "undefined") {
    return "/backend";
  }

  if (!API_BASE) {
    throw new ApiError("Konfigurasi API belum tersedia. Pastikan NEXT_PUBLIC_API_URL sudah diatur.");
  }

  return API_BASE;
}

export async function apiFetch<T>(path: string, init: ApiFetchOptions = {}): Promise<T> {
  const { timeoutMs = 15_000, signal: externalSignal, ...requestInit } = init;
  const controller = new AbortController();
  let timedOut = false;
  const onExternalAbort = () => controller.abort();
  externalSignal?.addEventListener("abort", onExternalAbort, { once: true });
  const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeoutMs);

  try {
    const response = await fetch(`${requireApiBase()}${path}`, {
      ...requestInit,
      credentials: requestInit.credentials ?? "include",
      signal: controller.signal,
      headers: { "Content-Type": "application/json", ...(requestInit.headers ?? {}) },
      cache: "no-store",
    });

    if (!response.ok) {
      if (response.status === 401 && !path.startsWith("/api/auth/") && typeof window !== "undefined") {
        window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
      }
      const body = (await response.json().catch(() => ({}))) as ApiErrorBody;
      const detailMessage = Array.isArray(body.detail) ? body.detail[0]?.msg : body.detail;
      throw new ApiError(
        body.error?.message ?? detailMessage ?? body.message ?? "Permintaan belum dapat diproses.",
        response.status,
        body.error?.code,
      );
    }

    if (response.status === 204) return undefined as T;
    return response.json() as Promise<T>;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (externalSignal?.aborted && !timedOut) {
      throw new ApiError("Permintaan dibatalkan.", 0, "REQUEST_ABORTED");
    }
    if (timedOut) {
      throw new ApiError("Permintaan membutuhkan waktu terlalu lama. Periksa koneksi lalu coba lagi.", 408, "REQUEST_TIMEOUT");
    }
    throw new ApiError("Backend belum dapat dihubungi. Periksa koneksi dan coba lagi.", 0, "NETWORK_ERROR");
  } finally {
    clearTimeout(timer);
    externalSignal?.removeEventListener("abort", onExternalAbort);
  }
}

