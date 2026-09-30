import type {
  AuditEvent,
  DecisionDetail,
  Incident,
  IncidentListItem,
  IntelligenceOverview,
} from "@/types/incident";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export function parseApiDate(value: string): Date {
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value);
  return new Date(hasTimezone ? value : value + "Z");
}

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

export class IncidentNotFoundError extends ApiError {}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    const isFormData = typeof FormData !== "undefined" && init.body instanceof FormData;
    response = await fetch(API_URL + path, {
      ...init,
      headers: {
        ...(init.body && !isFormData ? { "Content-Type": "application/json" } : {}),
        ...init.headers,
      },
      cache: "no-store",
      signal: init.signal ?? AbortSignal.timeout(10_000),
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Network request failed";
    throw new ApiError("Cannot reach AquaPass API: " + message, 0);
  }

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail =
      payload && typeof payload === "object" && "detail" in payload
        ? String(payload.detail)
        : "API request failed with status " + response.status;
    if (response.status === 404 && path.startsWith("/incidents/") && !path.includes("/audit")) {
      throw new IncidentNotFoundError(detail, response.status);
    }
    throw new ApiError(detail, response.status);
  }
  return payload as T;
}

export async function getIncidents(): Promise<IncidentListItem[]> {
  return apiRequest<IncidentListItem[]>("/incidents");
}

export type IncidentWorkspace = {
  incident: Incident;
  decisionDetail: DecisionDetail | null;
  intelligence: IntelligenceOverview | null;
  intelligenceError: string | null;
  audit: AuditEvent[];
};

export async function getIncidentWorkspace(id: string): Promise<IncidentWorkspace> {
  const incident = await apiRequest<Incident>("/incidents/" + encodeURIComponent(id));
  const decision =
    incident.decisions.find((item) => item.status === "PENDING") ??
    [...incident.decisions].sort((a, b) => b.current_version - a.current_version)[0];

  if (!decision) {
    return {
      incident,
      decisionDetail: null,
      intelligence: null,
      intelligenceError: "This incident does not have a decision record yet.",
      audit: [],
    };
  }

  const [decisionResult, intelligenceResult, auditResult] = await Promise.allSettled([
    apiRequest<DecisionDetail>("/decisions/" + encodeURIComponent(decision.id)),
    apiRequest<IntelligenceOverview>(
      "/api/intelligence/incidents/" + encodeURIComponent(id) + "/overview",
    ),
    apiRequest<AuditEvent[]>("/api/incidents/" + encodeURIComponent(id) + "/audit"),
  ]);

  return {
    incident,
    decisionDetail: decisionResult.status === "fulfilled" ? decisionResult.value : null,
    intelligence: intelligenceResult.status === "fulfilled" ? intelligenceResult.value : null,
    intelligenceError:
      intelligenceResult.status === "rejected"
        ? intelligenceResult.reason instanceof Error
          ? intelligenceResult.reason.message
          : "Intelligence data is unavailable."
        : null,
    audit: auditResult.status === "fulfilled" ? auditResult.value : [],
  };
}
