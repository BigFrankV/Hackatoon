import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { Alert } from "@/components/ui/Alert";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { PageLoader } from "@/components/ui/PageLoader";
import { Pagination } from "@/components/ui/Pagination";
import { Select } from "@/components/ui/Select";
import { listCompanies } from "@/lib/api/companies";
import { formatDateTime, formatStatus, statusTone } from "@/lib/format";
import type { CompanyResponse, CompanyStatus } from "@/types";

export function CompaniesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialStatus = (searchParams.get("status") as CompanyStatus | null) || "";
  const [search, setSearch] = useState(searchParams.get("search") || "");
  const [status, setStatus] = useState<CompanyStatus | "">(initialStatus);
  const [page, setPage] = useState(Number(searchParams.get("page") || "1"));
  const [data, setData] = useState<{ items: CompanyResponse[]; total: number; page: number; page_size: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listCompanies({
        page,
        page_size: 20,
        search: search || undefined,
        status: status || undefined,
      });
      setData(result);
    } catch {
      setError("No se pudieron cargar las empresas.");
    } finally {
      setLoading(false);
    }
  }, [page, search, status]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    const params: Record<string, string> = {};
    if (search) params.search = search;
    if (status) params.status = status;
    if (page > 1) params.page = String(page);
    setSearchParams(params, { replace: true });
  }, [search, status, page, setSearchParams]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Empresas</h1>
          <p className="mt-1 text-sm text-slate-600">Gestiona las empresas de la plataforma y su estado.</p>
        </div>
        <Link to="/platform/companies/new">
          <Button>Crear empresa</Button>
        </Link>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="grid gap-3 md:grid-cols-3">
          <Input
            label="Buscar"
            name="search"
            value={search}
            onChange={(e) => {
              setPage(1);
              setSearch(e.target.value);
            }}
            placeholder="Nombre o ID fiscal"
          />
          <Select
            label="Estado"
            name="status"
            value={status}
            onChange={(e) => {
              setPage(1);
              setStatus(e.target.value as CompanyStatus | "");
            }}
            options={[
              { value: "", label: "Todos los estados" },
              { value: "active", label: "Activo" },
              { value: "inactive", label: "Inactivo" },
              { value: "suspended", label: "Suspendido" },
            ]}
          />
        </div>
      </div>

      {error ? <Alert variant="error">{error}</Alert> : null}

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        {loading ? (
          <PageLoader />
        ) : !data || data.items.length === 0 ? (
          <EmptyState
            title="No se encontraron empresas"
            description="Ajusta los filtros o crea una empresa nueva."
            action={
              <Link to="/platform/companies/new">
                <Button>Crear empresa</Button>
              </Link>
            }
          />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-slate-200 text-slate-500">
                  <tr>
                    <th className="py-2 pr-4 font-medium">Empresa</th>
                    <th className="py-2 pr-4 font-medium">ID fiscal</th>
                    <th className="py-2 pr-4 font-medium">Estado</th>
                    <th className="py-2 pr-4 font-medium">Usuarios</th>
                    <th className="py-2 pr-4 font-medium">Creado</th>
                    <th className="py-2 font-medium">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((company) => (
                    <tr key={company.id} className="border-b border-slate-100 last:border-0">
                      <td className="py-3 pr-4">
                        <div className="font-medium text-slate-900">{company.display_name || company.legal_name}</div>
                        <div className="text-xs text-slate-500">{company.legal_name}</div>
                      </td>
                      <td className="py-3 pr-4 text-slate-600">{company.tax_id || "—"}</td>
                      <td className="py-3 pr-4">
                        <Badge tone={statusTone(company.status)}>{formatStatus(company.status)}</Badge>
                      </td>
                      <td className="py-3 pr-4 text-slate-600">{company.users_count ?? "—"}</td>
                      <td className="py-3 pr-4 text-slate-600">{formatDateTime(company.created_at)}</td>
                      <td className="py-3">
                        <Link
                          to={`/platform/companies/${company.id}`}
                          className="font-medium text-slate-700 hover:text-slate-900"
                        >
                          Ver
                        </Link>
                      </td>
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
