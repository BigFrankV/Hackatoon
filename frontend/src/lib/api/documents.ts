import { apiRequest } from "@/lib/api/client";

export interface CompanyDocument {
  id: string;
  title: string;
  status: "uploaded" | "queued" | "processing" | "completed" | "failed" | "ready";
  created_at: string;
  version_number: number;
  job_status: "queued" | "processing" | "completed" | "failed" | "cancelled" | null;
  error_code: string | null;
}

export interface DocumentUploadResult {
  id: string;
  title: string;
  status: string;
  version_id: string;
  version_number: number;
  job_id: string;
}

export function listDocuments() {
  return apiRequest<CompanyDocument[]>("/documents");
}

export function uploadDocument(file: File) {
  const form = new FormData();
  form.append("file", file);
  return apiRequest<DocumentUploadResult>("/documents", {
    method: "POST",
    headers: { "Idempotency-Key": crypto.randomUUID() },
    body: form,
  });
}

export function retryDocument(documentId: string) {
  return apiRequest<{ id: string; status: string; job_status: string }>(
    `/documents/${documentId}/retry`,
    { method: "POST" },
  );
}
