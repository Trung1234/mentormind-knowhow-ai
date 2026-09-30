import {
  AssistantAnswer,
  LotRecord,
  ProfilePatchRequest,
  ProfileStatus,
  RcaReport,
  ReviewRequest,
  WorkProfile,
} from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  const res = await fetch(url, { ...options, headers });
  if (!res.ok) {
    let errMsg = `${res.status} ${res.statusText}`;
    try {
      const errJson = await res.json();
      if (errJson.detail) {
        errMsg = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(errMsg);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getHealth: () => request<{ status: string; neo4j: string; postgres: string }>("/health"),

  getProfiles: (processId?: string, status?: ProfileStatus | string) => {
    const params = new URLSearchParams();
    if (processId) params.append("process_id", processId);
    if (status) params.append("status", status);
    const qs = params.toString() ? `?${params.toString()}` : "";
    return request<WorkProfile[]>(`/profiles${qs}`);
  },

  getProfileDetails: (profileId: string) => {
    return request<{ profile: WorkProfile; reviews: any[] }>(`/profiles/${profileId}`);
  },

  patchProfile: (profileId: string, data: ProfilePatchRequest) => {
    return request<WorkProfile>(`/profiles/${profileId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  reviewProfile: (profileId: string, data: ReviewRequest) => {
    return request<WorkProfile>(`/profiles/${profileId}/review`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  getSigmaLots: (processId?: string) => {
    const qs = processId ? `?process_id=${processId}` : "";
    return request<LotRecord[]>(`/sigma/lots${qs}`);
  },

  askAssistant: (processId: string, question: string) => {
    return request<AssistantAnswer>("/assistant/ask", {
      method: "POST",
      body: JSON.stringify({ process_id: processId, question }),
    });
  },

  investigateRca: (lotId?: string, symptom?: string) => {
    return request<RcaReport>("/rca/investigate", {
      method: "POST",
      body: JSON.stringify({ lot_id: lotId || undefined, symptom: symptom || undefined }),
    });
  },

  getMediaUrl: (relpath: string) => {
    if (relpath.startsWith("http://") || relpath.startsWith("https://")) return relpath;
    const clean = relpath.startsWith("/") ? relpath.slice(1) : relpath;
    return `${BASE_URL}/${clean}`;
  },
};
