import { useCallback, useEffect, useState } from "react";

import { Alert } from "@/components/ui/Alert";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { PageLoader } from "@/components/ui/PageLoader";
import { Pagination } from "@/components/ui/Pagination";
import { listGlobalAuditLogs } from "@/lib/api/audit";
import { formatDateTime } from "@/lib/format";
import type { AuditLogResponse } from "@/types";

export function PlatformAuditPage() {
  const [data, setData] = useState<{
    items: AuditLogResponse[];
    total: number;
    page: number;
    page_size: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [action, setAction] = useState("");
  const [entityType, setEntityType] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listGlobalAuditLogs({
        page,
        page_size: 20,
        action: action || undefined,
        entity_type: entityType || undefined,
      });
      setData(result);
    } catch {
      setError("No se pudieron cargar los registros de auditoría.");
    } finally {
      setLoading(false);
    }
  }, [page, action, entityType]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Auditoría global</h1>
        <p className="mt-1 text-sm text-slate-600">
          Revisa la actividad administrativa y de seguridad de toda la plataforma.
        </p>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="grid gap-3 md:grid-cols-2">
          <Input
            label="Acción"
            name="action"
            value={action}
            onChange={(e) => {
              setPage(1);
              setAction(e.target.value);
            }}
            placeholder="p. ej. user.login"
          />
          <Input
            label="Tipo de entidad"
            name="entity_type"
            value={entityType}
            onChange={(e) => {
              setPage(1);
              setEntityType(e.target.value);
            }}
            placeholder="p. ej. user, company"
          />
        </div>
      </div>

      {error ? <Alert variant="error">{error}</Alert> : null}

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        {loading ? (
          <PageLoader />
        ) : !data || data.items.length === 0 ? (
          <EmptyState
            title="No se encontraron registros de auditoría"
            description="Ajusta los filtros o vuelve a consultar cuando se registre actividad en la plataforma."
          />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-slate-200 text-slate-500">
                  <tr>
                    <th className="py-2 pr-4 font-medium">Fecha</th>
                    <th className="py-2 pr-4 font-medium">Acción</th>
                    <th className="py-2 pr-4 font-medium">Entidad</th>
                    <th className="py-2 pr-4 font-medium">Actor</th>
                    <th className="py-2 pr-4 font-medium">Empresa</th>
                    <th className="py-2 font-medium">IP</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((log) => (
                    <tr key={log.id} className="border-b border-slate-100 last:border-0 align-top">
                      <td className="py-3 pr-4 whitespace-nowrap text-slate-600">
                        {formatDateTime(log.occurred_at)}
                      </td>
                      <td className="py-3 pr-4 font-medium text-slate-900">{log.action}</td>
                      <td className="py-3 pr-4 text-slate-600">
                        <div>{log.entity_type}</div>
                        {log.entity_id ? (
                          <div className="font-mono text-xs text-slate-400 break-all">{log.entity_id}</div>
                        ) : null}
                      </td>
                      <td className="py-3 pr-4 font-mono text-xs text-slate-500 break-all">
                        {log.actor_user_id || "—"}
                      </td>
                      <td className="py-3 pr-4 font-mono text-xs text-slate-500 break-all">
                        {log.company_id || "—"}
                      </td>
                      <td className="py-3 text-slate-600">{log.ip_address || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination
              page={data.page}
              pageSize={data.page_size}
              total={data.total}
              onPageChange={setPage}
            />
          </>
        )}
      </div>
    </div>
  );
}
