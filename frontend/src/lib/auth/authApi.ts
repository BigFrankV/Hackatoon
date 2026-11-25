import { apiRequest } from "@/lib/api/client";
import type {
  LoginResponse,
  MessageResponse,
  RefreshResponse,
  UserPublic,
} from "@/types";

export async function loginRequest(email: string, password: string): Promise<LoginResponse> {
  return apiRequest<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
    skipAuth: true,
    skipRefresh: true,
  });
}

export async function refreshRequest(): Promise<RefreshResponse> {
  return apiRequest<RefreshResponse>("/auth/refresh", {
    method: "POST",
    skipAuth: true,
    skipRefresh: true,
  });
}

export async function logoutRequest(): Promise<MessageResponse> {
  return apiRequest<MessageResponse>("/auth/logout", {
    method: "POST",
    skipRefresh: true,
  });
}

export async function meRequest(): Promise<UserPublic> {
  return apiRequest<UserPublic>("/auth/me", {
    method: "GET",
  });
}

export async function updateProfileRequest(payload: {
  first_name?: string | null;
  last_name?: string | null;
}): Promise<UserPublic> {
  return apiRequest<UserPublic>("/auth/me", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function changePasswordRequest(payload: {
  current_password: string;
  new_password: string;
}): Promise<{
  message: string;
  access_token: string;
  token_type: string;
  expires_in: number;
}> {
  return apiRequest("/auth/change-password", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
