import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useParams } from "react-router-dom";

import { Alert } from "@/components/ui/Alert";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Input } from "@/components/ui/Input";
import { PageLoader } from "@/components/ui/PageLoader";
import { Select } from "@/components/ui/Select";
import { ApiRequestError } from "@/lib/api/client";
import { listCompanies } from "@/lib/api/companies";
import {
  activateGlobalUser,
  deactivateGlobalUser,
  getGlobalUser,
  resetGlobalUserPassword,
  revokeGlobalUserSessions,
  updateGlobalUser,
} from "@/lib/api/users";
import { formatDateTime, formatStatus, statusTone } from "@/lib/format";
import type { CompanyResponse, UserAdminResponse, UserRole, UserStatus } from "@/types";

export function PlatformUserDetailPage() {
  const { userId } = useParams<{ userId: string }>();
  const [user, setUser] = useState<UserAdminResponse | null>(null);
  const [companies, setCompanies] = useState<CompanyResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [tempPassword, setTempPassword] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<"activate" | "deactivate" | "reset-password" | "revoke-sessions" | null>(null);
  const [reason, setReason] = useState("");

  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    role: "user" as UserRole,
    status: "active" as UserStatus,
    company_id: "",
    must_change_password: false,
  });

  const load = useCallback(async () => {
    if (!userId) return;
    setLoading(true);
    setError(null);
    try {
      const [userRes, companiesRes] = await Promise.all([
        getGlobalUser(userId),
        listCompanies({ page: 1, page_size: 100 }),
      ]);
      setUser(userRes);
      setCompanies(companiesRes.items);
      setForm({
        first_name: userRes.first_name,
        last_name: userRes.last_name,
        role: userRes.role,
        status: userRes.status,
        company_id: userRes.company_id || "",
        must_change_password: userRes.must_change_password,
      });
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "No se pudo cargar el usuario.");
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => { void load(); }, [load]);

  const updateField = (key: string, value: string | boolean) =>
    setForm((p) => ({ ...p, [key]: value }));

  const handleSave = async (event: FormEvent) => {
    event.preventDefault();
    if (!userId) return;
    setSaving(true); setError(null); setSuccess(null); setTempPassword(null);
    try {
      const updated = await updateGlobalUser(userId, {
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        role: form.role,
        status: form.status,
        company_id: form.role === "super_admin" ? null : (form.company_id || null),
        must_change_password: form.must_change_password,
      });
      setUser(updated);
      setSuccess("Usuario actualizado correctamente.");
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "No se pudo actualizar el usuario.");
    } finally {
      setSaving(false);
    }
  };

  const handleConfirmedAction = async () => {
    if (!userId || !confirm) return;
    setActionLoading(true); setError(null); setSuccess(null); setTempPassword(null);
    try {
      if (confirm === "activate") {
        const updated = await activateGlobalUser(userId, reason);
        setUser(updated); setForm((p) => ({ ...p, status: updated.status }));
        setSuccess("Usuario activado.");
      } else if (confirm === "deactivate") {
        const updated = await deactivateGlobalUser(userId, reason);
        setUser(updated); setForm((p) => ({ ...p, status: updated.status }));
        setSuccess("Usuario desactivado y sesiones revocadas.");
      } else if (confirm === "reset-password") {
        const res = await resetGlobalUserPassword(userId);
        setTempPassword(res.temporary_password || null);
        setSuccess(res.message);
        await load();
      } else if (confirm === "revoke-sessions") {
        const res = await revokeGlobalUserSessions(userId);
        setSuccess(`${res.message}${typeof res.revoked_sessions === "number" ? ` (${res.revoked_sessions} revocadas)` : ""}.`);
      }
      setConfirm(null);
      setReason("");
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "La acción falló.");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) return <PageLoader />;
  if (error && !user) return <Alert variant="error">{error}</Alert>;
  if (!user) return <Alert variant="error">Usuario no encontrado.</Alert>;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold text-slate-900">{user.first_name} {user.last_name}</h1>
            <Badge tone={statusTone(user.status)}>{formatStatus(user.status)}</Badge>
          </div>
          <p className="mt-1 text-sm text-slate-600">{user.email}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {user.status === "active" ? (
            <Button variant="danger" onClick={() => setConfirm("deactivate")}>Desactivar</Button>
          ) : (
            <Button onClick={() => setConfirm("activate")}>Activar</Button>
          )}
          <Button variant="secondary" onClick={() => setConfirm("reset-password")}>Restablecer contraseña</Button>
          <Button variant="secondary" onClick={() => setConfirm("revoke-sessions")}>Revocar sesiones</Button>
        </div>
      </div>

      {error ? <Alert variant="error">{error}</Alert> : null}
      {success ? <Alert variant="success">{success}</Alert> : null}
      {tempPassword ? (
        <Alert variant="warning">
          <p className="font-medium">Contraseña temporal (compartir de forma segura)</p>
          <p className="mt-1 font-mono text-sm">{tempPassword}</p>
        </Alert>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-3">
        <form className="xl:col-span-2 rounded-xl border border-slate-200 bg-white p-6 shadow-sm" onSubmit={handleSave}>
          <h2 className="text-lg font-semibold text-slate-900">Datos del usuario</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <Input label="Nombre" name="first_name" value={form.first_name} onChange={(e) => updateField("first_name", e.target.value)} required />
            <Input label="Apellido" name="last_name" value={form.last_name} onChange={(e) => updateField("last_name", e.target.value)} required />
            <Select label="Rol" name="role" value={form.role} onChange={(e) => updateField("role", e.target.value)} options={[
              { value: "user", label: "Usuario" },
              { value: "admin", label: "Administrador" },
              { value: "super_admin", label: "Superadministrador" },
            ]} />
            <Select label="Estado" name="status" value={form.status} onChange={(e) => updateField("status", e.target.value)} options={[
              { value: "active", label: "Activo" },
              { value: "inactive", label: "Inactivo" },
              { value: "invited", label: "Invitado" },
              { value: "locked", label: "Bloqueado" },
            ]} />
            <Select
              label="Empresa"
              name="company_id"
              value={form.company_id}
              onChange={(e) => updateField("company_id", e.target.value)}
              disabled={form.role === "super_admin"}
              placeholder={form.role === "super_admin" ? "Sin empresa (plataforma)" : "Seleccionar empresa"}
              options={companies.map((c) => ({ value: c.id, label: c.display_name || c.legal_name }))}
            />
            <label className="flex items-center gap-2 text-sm text-slate-700 md:pt-7">
              <input
                type="checkbox"
                checked={form.must_change_password}
                onChange={(e) => updateField("must_change_password", e.target.checked)}
              />
              Debe cambiar la contraseña
            </label>
          </div>
          <div className="mt-5">
            <Button type="submit" loading={saving}>Guardar cambios</Button>
          </div>
        </form>

        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">Resumen</h2>
          <dl className="mt-4 space-y-3 text-sm">
            <div><dt className="text-slate-500">ID del usuario</dt><dd className="font-mono text-xs break-all text-slate-700">{user.id}</dd></div>
            <div><dt className="text-slate-500">Empresa</dt><dd className="text-slate-900">{user.company?.display_name || user.company?.legal_name || "—"}</dd></div>
            <div><dt className="text-slate-500">Último acceso</dt><dd className="text-slate-900">{formatDateTime(user.last_login_at)}</dd></div>
            <div><dt className="text-slate-500">Creado</dt><dd className="text-slate-900">{formatDateTime(user.created_at)}</dd></div>
            <div><dt className="text-slate-500">Actualizado</dt><dd className="text-slate-900">{formatDateTime(user.updated_at)}</dd></div>
          </dl>
        </div>
      </div>

      <ConfirmDialog
        open={confirm !== null}
        title={
          confirm === "deactivate" ? "Desactivar usuario"
          : confirm === "activate" ? "Activar usuario"
          : confirm === "reset-password" ? "Restablecer contraseña"
          : "Revocar sesiones"
        }
        description={
          confirm === "deactivate" ? "Esto desactivará al usuario y revocará las sesiones activas."
          : confirm === "activate" ? "Esto permitirá al usuario iniciar sesión de nuevo (según el estado de la empresa)."
          : confirm === "reset-password" ? "Esto generará una contraseña temporal, exigirá el cambio de contraseña y revocará las sesiones."
          : "Esto revocará todas las sesiones activas de este usuario."
        }
        confirmLabel={
          confirm === "deactivate" ? "Desactivar"
          : confirm === "activate" ? "Activar"
          : confirm === "reset-password" ? "Restablecer contraseña"
          : "Revocar sesiones"
        }
        tone={confirm === "deactivate" ? "danger" : "primary"}
        loading={actionLoading}
        onCancel={() => { if (!actionLoading) { setConfirm(null); setReason(""); } }}
        onConfirm={handleConfirmedAction}
      >
        {confirm === "deactivate" || confirm === "activate" ? (
          <label className="block text-sm text-slate-700">
            Motivo (opcional)
            <input className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" value={reason} onChange={(e) => setReason(e.target.value)} maxLength={500} />
          </label>
        ) : null}
      </ConfirmDialog>
    </div>
  );
}
