import { apiRequest } from "@/lib/api/client";
import type {
  CompanyCreateResponse,
  CompanyResponse,
  CompanyStatus,
  PaginatedResponse,
} from "@/types";

export interface CompanyListParams {
  page?: number;
  page_size?: number;
  status?: CompanyStatus | "";
  search?: string;
}

function toQuery(params: Record<string, string | number | undefined | null | "">): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

export function listCompanies(params: CompanyListParams = {}) {
  return apiRequest<PaginatedResponse<CompanyResponse>>(
    `/companies${toQuery({
      page: params.page,
      page_size: params.page_size,
      status: params.status,
      search: params.search,
    })}`,
  );
}

export function createCompany(payload: {
  legal_name: string;
  display_name?: string | null;
  tax_id?: string | null;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
  initial_admin: { first_name: string; last_name: string; email: string };
}) {
  return apiRequest<CompanyCreateResponse>("/companies", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getCompany(companyId: string) {
  return apiRequest<CompanyResponse>(`/companies/${companyId}`);
}

export function updateCompany(
  companyId: string,
  payload: {
    legal_name?: string | null;
    display_name?: string | null;
    tax_id?: string | null;
    email?: string | null;
    phone?: string | null;
    address?: string | null;
  },
) {
  return apiRequest<CompanyResponse>(`/companies/${companyId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function suspendCompany(companyId: string, reason?: string) {
  return apiRequest<CompanyResponse>(`/companies/${companyId}/suspend`, {
    method: "POST",
    body: JSON.stringify({ reason: reason || null, confirmation: true }),
  });
}

export function activateCompany(companyId: string, reason?: string) {
  return apiRequest<CompanyResponse>(`/companies/${companyId}/activate`, {
    method: "POST",
    body: JSON.stringify({ reason: reason || null, confirmation: true }),
  });
}
