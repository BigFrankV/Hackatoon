import { apiRequest } from "@/lib/api/client";
import type {
  CompanyProfileResponse,
  PaginatedResponse,
  UserAdminResponse,
  UserCreatedResponse,
  UserResetPasswordResponse,
  UserRole,
  UserStatus,
} from "@/types";

function toQuery(params: Record<string, string | number | undefined | null | "">): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

export function getCompanyProfile() {
  return apiRequest<CompanyProfileResponse>("/company/profile");
}

export function updateCompanyProfile(payload: {
  display_name?: string | null;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
}) {
  return apiRequest<CompanyProfileResponse>("/company/profile", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export interface CompanyUserListParams {
  page?: number;
  page_size?: number;
  role?: UserRole | "";
  status?: UserStatus | "";
  search?: string;
}

export function listCompanyUsers(params: CompanyUserListParams = {}) {
  return apiRequest<PaginatedResponse<UserAdminResponse>>(
    `/company/users${toQuery({
      page: params.page,
      page_size: params.page_size,
      role: params.role,
      status: params.status,
      search: params.search,
    })}`,
  );
}

export function createCompanyUser(payload: {
  first_name: string;
  last_name: string;
  email: string;
  status?: UserStatus;
}) {
  return apiRequest<UserCreatedResponse>("/company/users", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getCompanyUser(userId: string) {
  return apiRequest<UserAdminResponse>(`/company/users/${userId}`);
}

export function updateCompanyUser(
  userId: string,
  payload: { first_name?: string | null; last_name?: string | null },
) {
  return apiRequest<UserAdminResponse>(`/company/users/${userId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function activateCompanyUser(userId: string, reason?: string) {
  return apiRequest<UserAdminResponse>(`/company/users/${userId}/activate`, {
    method: "POST",
    body: JSON.stringify({ reason: reason || null }),
  });
}

export function deactivateCompanyUser(userId: string, reason?: string) {
  return apiRequest<UserAdminResponse>(`/company/users/${userId}/deactivate`, {
    method: "POST",
    body: JSON.stringify({ reason: reason || null }),
  });
}

export function resetCompanyUserPassword(userId: string) {
  return apiRequest<UserResetPasswordResponse>(`/company/users/${userId}/reset-password`, {
    method: "POST",
  });
}

export function revokeCompanyUserSessions(userId: string) {
  return apiRequest<{ message: string; revoked_sessions?: number }>(
    `/company/users/${userId}/revoke-sessions`,
    { method: "POST" },
  );
}
