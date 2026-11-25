import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import { Alert } from "@/components/ui/Alert";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { PageLoader } from "@/components/ui/PageLoader";
import { ApiRequestError } from "@/lib/api/client";
import {
  activateCompany,
  getCompany,
  suspendCompany,
  updateCompany,
} from "@/lib/api/companies";
import { listCompanyUsers } from "@/lib/api/company";
import { apiRequest } from "@/lib/api/client";
import { formatDateTime, formatStatus, statusTone } from "@/lib/format";
import type { CompanyResponse, PaginatedResponse, UserAdminResponse } from "@/types";

function toNull(value: string): string | null {
  const t = value.trim();
  return t === "" ? null : t;
}

export function CompanyDetailPage() {
  const { companyId } = useParams<{ companyId: string }>();
  const [company, setCompany] = useState<CompanyResponse | null>(null);
  const [users, setUsers] = useState<UserAdminResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<"suspend" | "activate" | null>(null);
  const [reason, setReason] = useState("");

  const [form, setForm] = useState({
    legal_name: "",
    display_name: "",
    tax_id: "",
    email: "",
    phone: "",
    address: "",
  });

  const load = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    setError(null);
    try {
      const [companyRes, usersRes] = await Promise.all([
        getCompany(companyId),
        apiRequest<PaginatedResponse<UserAdminResponse>>(
          `/companies/${companyId}/users?page=1&page_size=10`,
        ),
      ]);
      setCompany(companyRes);
      setUsers(usersRes.items);
      setForm({
        legal_name: companyRes.legal_name || "",
        display_name: companyRes.display_name || "",
        tax_id: companyRes.tax_id || "",
        email: companyRes.email || "",
        phone: companyRes.phone || "",
        address: companyRes.address || "",
      });
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "No se pudo cargar la empresa.");
    } finally {
      setLoading(false);
    }
  }, [companyId]);

  useEffect(() => {
    void load();
  }, [load]);

  const updateField = (key: keyof typeof form, value: string) =>
    setForm((p) => ({ ...p, [key]: value }));

  const handleSave = async (event: FormEvent) => {
    event.preventDefault();
    if (!companyId) return;
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await updateCompany(companyId, {
        legal_name: form.legal_name.trim(),
        display_name: toNull(form.display_name),
        tax_id: toNull(form.tax_id),
        email: toNull(form.email),
        phone: toNull(form.phone),
        address: toNull(form.address),
      });
      setCompany(updated);
      setSuccess("Empresa actualizada correctamente.");
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "No se pudo actualizar la empresa.");
    } finally {
      setSaving(false);
    }
  };

  const handleStatusAction = async () => {
    if (!companyId || !confirm) return;
    setActionLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const updated =
        confirm === "suspend"
          ? await suspendCompany(companyId, reason)
          : await activateCompany(companyId, reason);
      setCompany(updated);
      setSuccess(
        confirm === "suspend"
          ? "Empresa suspendida correctamente."
          : "Empresa activada correctamente.",
      );
      setConfirm(null);
      setReason("");
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "No se pudo actualizar el estado de la empresa.");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) return <PageLoader />;
  if (error && !company) return <Alert variant="error">{error}</Alert>;
  if (!company) return <Alert variant="error">Empresa no encontrada.</Alert>;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold text-slate-900">
              {company.display_name || company.legal_name}
            </h1>
            <Badge tone={statusTone(company.status)}>{formatStatus(company.status)}</Badge>
          </div>
          <p className="mt-1 text-sm text-slate-600">{company.legal_name}</p>
        </div>
        <div className="flex gap-2">
          {company.status === "active" ? (
            <Button variant="danger" onClick={() => setConfirm("suspend")}>
              Suspender
            </Button>
          ) : (
            <Button onClick={() => setConfirm("activate")}>Activar</Button>
          )}
        </div>
      </div>

      {error ? <Alert variant="error">{error}</Alert> : null}
      {success ? <Alert variant="success">{success}</Alert> : null}

      <div className="grid gap-6 xl:grid-cols-3">
        <form className="xl:col-span-2 rounded-xl border border-slate-200 bg-white p-6 shadow-sm" onSubmit={handleSave}>
          <h2 className="text-lg font-semibold text-slate-900">Datos de la empresa</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <Input label="Razón social" name="legal_name" value={form.legal_name} onChange={(e) => updateField("legal_name", e.target.value)} required />
            <Input label="Nombre visible" name="display_name" value={form.display_name} onChange={(e) => updateField("display_name", e.target.value)} />
            <Input label="ID fiscal" name="tax_id" value={form.tax_id} onChange={(e) => updateField("tax_id", e.target.value)} />
            <Input label="Correo electrónico" name="email" type="email" value={form.email} onChange={(e) => updateField("email", e.target.value)} />
            <Input label="Teléfono" name="phone" value={form.phone} onChange={(e) => updateField("phone", e.target.value)} />
            <Input label="Dirección" name="address" value={form.address} onChange={(e) => updateField("address", e.target.value)} />
          </div>
          <div className="mt-5">
            <Button type="submit" loading={saving}>Guardar cambios</Button>
          </div>
        </form>

        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">Resumen</h2>
          <dl className="mt-4 space-y-3 text-sm">
            <div>
              <dt className="text-slate-500">ID de la empresa</dt>
              <dd className="font-mono text-xs text-slate-700 break-all">{company.id}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Usuarios</dt>
              <dd className="text-slate-900">{company.users_count ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Creado</dt>
              <dd className="text-slate-900">{formatDateTime(company.created_at)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Actualizado</dt>
              <dd className="text-slate-900">{formatDateTime(company.updated_at)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Desactivado</dt>
              <dd className="text-slate-900">{formatDateTime(company.deactivated_at)}</dd>
            </div>
          </dl>
        </div>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-slate-900">Usuarios</h2>
          <Link to={`/platform/users?company_id=${company.id}`} className="text-sm font-medium text-slate-700 hover:text-slate-900">
            Ver todos los usuarios
          </Link>
        </div>
        {users.length === 0 ? (
          <div className="mt-4">
            <EmptyState title="No se encontraron usuarios" description="Esta empresa aún no tiene usuarios." />
          </div>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-200 text-slate-500">
                <tr>
                  <th className="py-2 pr-4 font-medium">Nombre</th>
                  <th className="py-2 pr-4 font-medium">Correo electrónico</th>
                  <th className="py-2 pr-4 font-medium">Rol</th>
                  <th className="py-2 pr-4 font-medium">Estado</th>
                  <th className="py-2 font-medium">Acción</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-b border-slate-100 last:border-0">
                    <td className="py-2 pr-4 text-slate-900">{u.first_name} {u.last_name}</td>
                    <td className="py-2 pr-4 text-slate-600">{u.email}</td>
                    <td className="py-2 pr-4 text-slate-600">{formatStatus(u.role)}</td>
                    <td className="py-2 pr-4"><Badge tone={statusTone(u.status)}>{formatStatus(u.status)}</Badge></td>
                    <td className="py-2">
                      <Link to={`/platform/users/${u.id}`} className="font-medium text-slate-700 hover:text-slate-900">Ver</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <ConfirmDialog
        open={confirm !== null}
        title={confirm === "suspend" ? "Suspender empresa" : "Activar empresa"}
        description={
          confirm === "suspend"
            ? "Suspender esta empresa bloqueará el acceso de sus miembros y revocará las sesiones activas. Esta acción se puede revertir."
            : "Reactivar esta empresa permitirá que sus miembros vuelvan a iniciar sesión."
        }
        confirmLabel={confirm === "suspend" ? "Suspender empresa" : "Activar empresa"}
        tone={confirm === "suspend" ? "danger" : "primary"}
        loading={actionLoading}
        onCancel={() => {
          if (!actionLoading) {
            setConfirm(null);
            setReason("");
          }
        }}
        onConfirm={handleStatusAction}
      >
        <label className="block text-sm text-slate-700">
          Motivo (opcional)
          <input
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            maxLength={500}
          />
        </label>
      </ConfirmDialog>
    </div>
  );
}
