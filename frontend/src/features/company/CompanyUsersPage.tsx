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
import { listCompanyUsers } from "@/lib/api/company";
import { formatDateTime, formatStatus, statusTone } from "@/lib/format";
import type { UserAdminResponse, UserRole, UserStatus } from "@/types";

export function CompanyUsersPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [data, setData] = useState<{
    items: UserAdminResponse[];
    total: number;
    page: number;
    page_size: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState(searchParams.get("search") || "");
  const [role, setRole] = useState<UserRole | "">((searchParams.get("role") as UserRole | "") || "");
  const [status, setStatus] = useState<UserStatus | "">(
    (searchParams.get("status") as UserStatus | "") || "",
  );
  const [page, setPage] = useState(Number(searchParams.get("page") || "1"));

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listCompanyUsers({
        page,
        page_size: 20,
        search: search || undefined,
        role: role || undefined,
        status: status || undefined,
      });
      setData(result);
    } catch {
      setError("No se pudieron cargar los usuarios de la empresa.");
    } finally {
      setLoading(false);
    }
  }, [page, search, role, status]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    const params: Record<string, string> = {};
    if (search) params.search = search;
    if (role) params.role = role;
    if (status) params.status = status;
    if (page > 1) params.page = String(page);
    setSearchParams(params, { replace: true });
  }, [search, role, status, page, setSearchParams]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Usuarios de la empresa</h1>
          <p className="mt-1 text-sm text-slate-600">Gestiona los usuarios de tu empresa.</p>
        </div>
        <Link to="/app/settings/users/new">
          <Button>Crear usuario</Button>
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
            placeholder="Nombre o correo electrónico"
          />
          <Select
            label="Rol"
            name="role"
            value={role}
            onChange={(e) => {
              setPage(1);
              setRole(e.target.value as UserRole | "");
            }}
            options={[
              { value: "", label: "Todos los roles" },
              { value: "admin", label: "Administrador" },
              { value: "user", label: "Usuario" },
            ]}
          />
          <Select
            label="Estado"
            name="status"
            value={status}
            onChange={(e) => {
              setPage(1);
              setStatus(e.target.value as UserStatus | "");
            }}
            options={[
              { value: "", label: "Todos los estados" },
              { value: "active", label: "Activo" },
              { value: "inactive", label: "Inactivo" },
              { value: "invited", label: "Invitado" },
              { value: "locked", label: "Bloqueado" },
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
            title="No se encontraron usuarios"
            description="Ajusta los filtros o crea un usuario nuevo."
            action={
              <Link to="/app/settings/users/new">
                <Button>Crear usuario</Button>
              </Link>
            }
          />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-slate-200 text-slate-500">
                  <tr>
                    <th className="py-2 pr-4 font-medium">Nombre</th>
                    <th className="py-2 pr-4 font-medium">Correo electrónico</th>
                    <th className="py-2 pr-4 font-medium">Rol</th>
                    <th className="py-2 pr-4 font-medium">Estado</th>
                    <th className="py-2 pr-4 font-medium">Último acceso</th>
                    <th className="py-2 font-medium">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((u) => (
                    <tr key={u.id} className="border-b border-slate-100 last:border-0">
                      <td className="py-3 pr-4 text-slate-900">
                        {u.first_name} {u.last_name}
                      </td>
                      <td className="py-3 pr-4 text-slate-600">{u.email}</td>
                      <td className="py-3 pr-4 text-slate-600">{formatStatus(u.role)}</td>
                      <td className="py-3 pr-4">
                        <Badge tone={statusTone(u.status)}>{formatStatus(u.status)}</Badge>
                      </td>
                      <td className="py-3 pr-4 text-slate-600">{formatDateTime(u.last_login_at)}</td>
                      <td className="py-3">
                        <Link
                          to={`/app/settings/users/${u.id}`}
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
