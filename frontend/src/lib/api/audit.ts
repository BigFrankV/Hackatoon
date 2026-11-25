import { apiRequest } from "@/lib/api/client";
import type { AuditLogListResponse } from "@/types";

function toQuery(params: Record<string, string | number | undefined | null | "">): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

export interface AuditListParams {
  page?: number;
  page_size?: number;
  action?: string;
  entity_type?: string;
  entity_id?: string;
  actor_user_id?: string;
  company_id?: string;
  from_date?: string;
  to_date?: string;
}

export function listGlobalAuditLogs(params: AuditListParams = {}) {
  return apiRequest<AuditLogListResponse>(
    `/audit-logs${toQuery({
      page: params.page,
      page_size: params.page_size,
      action: params.action,
      entity_type: params.entity_type,
      entity_id: params.entity_id,
      actor_user_id: params.actor_user_id,
      company_id: params.company_id,
      from_date: params.from_date,
      to_date: params.to_date,
    })}`,
  );
}

export function listCompanyAuditLogs(params: AuditListParams = {}) {
  return apiRequest<AuditLogListResponse>(
    `/company/audit-logs${toQuery({
      page: params.page,
      page_size: params.page_size,
      action: params.action,
      entity_type: params.entity_type,
      entity_id: params.entity_id,
      actor_user_id: params.actor_user_id,
      from_date: params.from_date,
      to_date: params.to_date,
    })}`,
  );
}
