export type UserRole = "super_admin" | "admin" | "user";
export type UserStatus = "active" | "inactive" | "locked" | "invited";
export type CompanyStatus = "active" | "inactive" | "suspended";

export interface CompanySummary {
  id: string;
  display_name: string | null;
  legal_name: string | null;
  status?: CompanyStatus | string | null;
}

export interface UserPublic {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  status: UserStatus;
  company_id: string | null;
  company: CompanySummary | null;
  must_change_password: boolean;
  last_login_at: string | null;
  permissions?: string[];
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: UserPublic;
}

export interface RefreshResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface ApiErrorPayload {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}

export interface MessageResponse {
  message: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface CompanyResponse {
  id: string;
  legal_name: string;
  display_name: string | null;
  tax_id: string | null;
  email: string | null;
  phone: string | null;
  address: string | null;
  status: CompanyStatus;
  created_at: string;
  updated_at: string;
  deactivated_at: string | null;
  users_count?: number | null;
}

export interface CompanyProfileResponse {
  id: string;
  legal_name: string;
  display_name: string | null;
  tax_id: string | null;
  email: string | null;
  phone: string | null;
  address: string | null;
  status: CompanyStatus;
  created_at: string;
  updated_at: string;
}

export interface CompanyCreateResponse {
  company: CompanyResponse;
  initial_admin: {
    id: string;
    email: string;
    first_name: string;
    last_name: string;
    role: UserRole;
    status: UserStatus;
    must_change_password: boolean;
    temporary_password?: string | null;
  };
  delivery: {
    method: string;
    note: string;
  };
}

export interface UserAdminResponse {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  status: UserStatus;
  company_id: string | null;
  company: CompanySummary | null;
  must_change_password: boolean;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
  deactivated_at: string | null;
}

export interface UserCreatedResponse {
  user: UserAdminResponse;
  delivery: {
    method: string;
    note: string;
  };
  temporary_password?: string | null;
}

export interface UserResetPasswordResponse {
  message: string;
  reset_initiated: boolean;
  delivery: string;
  temporary_password?: string | null;
  must_change_password?: boolean | null;
}

export interface AuditLogResponse {
  id: string;
  actor_user_id: string | null;
  company_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  occurred_at: string;
  ip_address: string | null;
  user_agent: string | null;
  metadata: Record<string, unknown> | null;
}

export interface AuditLogListResponse extends PaginatedResponse<AuditLogResponse> {}

export interface ApiHealthResponse {
  status: string;
}
