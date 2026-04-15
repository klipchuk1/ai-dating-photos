import axios from "axios";

// In production VITE_API_URL points to the Railway backend (e.g. https://xxx.railway.app)
// In local dev the Vite proxy rewrites /api → http://localhost:8000
const BASE = import.meta.env.VITE_API_URL ?? "/api";

const api = axios.create({ baseURL: BASE });

// ── Types ──────────────────────────────────────────────────────────────────────

export interface StyleOption {
  id: string;
  name: string;
  description: string;
  preview_url: string;
  style_strength: number;
}

export interface JobStatusResponse {
  job_id: string;
  user_id: string;
  style_id: string;
  status: "pending" | "processing" | "done" | "failed";
  progress: number;
  error?: string | null;
}

export interface PhotoOut {
  url: string;
  similarity_score: number;
}

export interface ResultResponse {
  job_id: string;
  user_id: string;
  style_id: string;
  photos: PhotoOut[];
  top_photo: PhotoOut | null;
}

// ── Endpoints ──────────────────────────────────────────────────────────────────

export const uploadPhotos = async (files: File[]) => {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  const { data } = await api.post<{ user_id: string; uploaded_count: number; message: string }>(
    "/upload",
    form,
  );
  return data;
};

export const fetchStyles = async (): Promise<StyleOption[]> => {
  const { data } = await api.get<StyleOption[]>("/styles");
  return data;
};

/** Backend accepts one style_id at a time. */
export const startGeneration = async (user_id: string, style_id: string) => {
  const { data } = await api.post<{ job_id: string; user_id: string; style_id: string; status: string }>(
    "/generate",
    { user_id, style_id },
  );
  return data;
};

export const pollJobStatus = async (job_id: string): Promise<JobStatusResponse> => {
  const { data } = await api.get<JobStatusResponse>(`/status/${job_id}`);
  return data;
};

export const getResult = async (job_id: string): Promise<ResultResponse> => {
  const { data } = await api.get<ResultResponse>(`/result/${job_id}`);
  return data;
};
