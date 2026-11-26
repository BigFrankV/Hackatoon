import { apiRequest } from "@/lib/api/client";

export interface TenderItem {
  name: string | null;
  description: string | null;
  quantity: string | null;
  unit: string | null;
}

export interface TenderDetail {
  external_id: string;
  title: string;
  status: string | null;
  status_code: string | null;
  description: string | null;
  buyer_name: string | null;
  buyer_code: string | null;
  published_at: string | null;
  closing_at: string | null;
  estimated_amount: string | null;
  currency: string | null;
  official_url: string;
  items: TenderItem[];
}

export function getTenderById(externalId: string) {
  return apiRequest<TenderDetail>(`/tenders/${encodeURIComponent(externalId)}`);
}
