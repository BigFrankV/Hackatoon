import { apiRequest } from "@/lib/api/client";
import type {
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

export interface UserListParams {
  page?: number;
  page_size?: number;
  company_id?: string;
  role?: UserRole | "";
  status?: UserStatus | "";
  search?: string;
}

export function listGlobalUsers(params: UserListParams = {}) {
  return apiRequest<PaginatedResponse<UserAdminResponse>>(
    `/users${toQuery({
      page: params.page,
      page_size: params.page_size,
      company_id: params.company_id,
      role: params.role,
      status: params.status,
      search: params.search,
    })}`,
  );
}

export function createGlobalUser(payload: {
  first_name: string;
  last_name: string;
  email: string;
  role: UserRole;
  company_id?: string | null;
  status?: UserStatus;
}) {
  return apiRequest<UserCreatedResponse>("/users", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getGlobalUser(userId: string) {
  return apiRequest<UserAdminResponse>(`/users/${userId}`);
}

export function updateGlobalUser(
  userId: string,
  payload: {
    first_name?: string | null;
    last_name?: string | null;
    role?: UserRole | null;
    status?: UserStatus | null;
    company_id?: string | null;
    must_change_password?: boolean | null;
  },
) {
  return apiRequest<UserAdminResponse>(`/users/${userId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function activateGlobalUser(userId: string, reason?: string) {
  return apiRequest<UserAdminResponse>(`/users/${userId}/activate`, {
    method: "POST",
    body: JSON.stringify({ reason: reason || null }),
  });
}

export function deactivateGlobalUser(userId: string, reason?: string) {
  return apiRequest<UserAdminResponse>(`/users/${userId}/deactivate`, {
    method: "POST",
    body: JSON.stringify({ reason: reason || null }),
  });
}

export function resetGlobalUserPassword(userId: string) {
  return apiRequest<UserResetPasswordResponse>(`/users/${userId}/reset-password`, {
    method: "POST",
  });
}

export function revokeGlobalUserSessions(userId: string) {
  return apiRequest<{ message: string; revoked_sessions?: number }>(
    `/users/${userId}/revoke-sessions`,
    { method: "POST" },
  );
}
