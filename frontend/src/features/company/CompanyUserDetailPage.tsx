import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useParams } from "react-router-dom";

import { Alert } from "@/components/ui/Alert";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Input } from "@/components/ui/Input";
import { PageLoader } from "@/components/ui/PageLoader";
import { ApiRequestError } from "@/lib/api/client";
import {
  activateCompanyUser,
  deactivateCompanyUser,
  getCompanyUser,
  resetCompanyUserPassword,
  revokeCompanyUserSessions,
  updateCompanyUser,
} from "@/lib/api/company";
import { formatDateTime, formatStatus, statusTone } from "@/lib/format";
import type { UserAdminResponse } from "@/types";

export function CompanyUserDetailPage() {
  const { userId } = useParams<{ userId: string }>();
  const [user, setUser] = useState<UserAdminResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [tempPassword, setTempPassword] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<
    "activate" | "deactivate" | "reset-password" | "revoke-sessions" | null
  >(null);
  const [reason, setReason] = useState("");
  const [form, setForm] = useState({ first_name: "", last_name: "" });

  const load = useCallback(async () => {
    if (!userId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await getCompanyUser(userId);
      setUser(result);
      setForm({ first_name: result.first_name, last_name: result.last_name });
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "No se pudo cargar el usuario.");
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleSave = async (event: FormEvent) => {
    event.preventDefault();
    if (!userId) return;
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await updateCompanyUser(userId, {
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
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
    setActionLoading(true);
    setError(null);
    setSuccess(null);
    setTempPassword(null);
    try {
      if (confirm === "activate") {
        const updated = await activateCompanyUser(userId, reason);
        setUser(updated);
        setSuccess("Usuario activado.");
      } else if (confirm === "deactivate") {
        const updated = await deactivateCompanyUser(userId, reason);
        setUser(updated);
        setSuccess("Usuario desactivado y sesiones revocadas.");
      } else if (confirm === "reset-password") {
        const res = await resetCompanyUserPassword(userId);
        setTempPassword(res.temporary_password || null);
        setSuccess(res.message);
        await load();
      } else if (confirm === "revoke-sessions") {
        const res = await revokeCompanyUserSessions(userId);
        setSuccess(
          `${res.message}${typeof res.revoked_sessions === "number" ? ` (${res.revoked_sessions} revocadas)` : ""}.`,
        );
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
            <h1 className="text-2xl font-semibold text-slate-900">
              {user.first_name} {user.last_name}
            </h1>
            <Badge tone={statusTone(user.status)}>{formatStatus(user.status)}</Badge>
          </div>
          <p className="mt-1 text-sm text-slate-600">{user.email}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {user.status === "active" ? (
            <Button variant="danger" onClick={() => setConfirm("deactivate")}>
              Desactivar
            </Button>
          ) : (
            <Button onClick={() => setConfirm("activate")}>Activar</Button>
          )}
          <Button variant="secondary" onClick={() => setConfirm("reset-password")}>
            Restablecer contraseña
          </Button>
          <Button variant="secondary" onClick={() => setConfirm("revoke-sessions")}>
            Revocar sesiones
          </Button>
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
        <form
          className="xl:col-span-2 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
          onSubmit={handleSave}
        >
          <h2 className="text-lg font-semibold text-slate-900">Datos del usuario</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <Input
              label="Nombre"
              name="first_name"
              value={form.first_name}
              onChange={(e) => setForm((p) => ({ ...p, first_name: e.target.value }))}
              required
              maxLength={100}
            />
            <Input
              label="Apellido"
              name="last_name"
              value={form.last_name}
              onChange={(e) => setForm((p) => ({ ...p, last_name: e.target.value }))}
              required
              maxLength={100}
            />
            <Input label="Correo electrónico" name="email" value={user.email} disabled />
            <Input label="Rol" name="role" value={formatStatus(user.role)} disabled />
          </div>
          <div className="mt-5">
            <Button type="submit" loading={saving}>
              Guardar cambios
            </Button>
          </div>
        </form>

        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">Resumen</h2>
          <dl className="mt-4 space-y-3 text-sm">
            <div>
              <dt className="text-slate-500">ID del usuario</dt>
              <dd className="font-mono text-xs break-all text-slate-700">{user.id}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Estado</dt>
              <dd className="text-slate-900">{formatStatus(user.status)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Último acceso</dt>
              <dd className="text-slate-900">{formatDateTime(user.last_login_at)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Creado</dt>
              <dd className="text-slate-900">{formatDateTime(user.created_at)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Actualizado</dt>
              <dd className="text-slate-900">{formatDateTime(user.updated_at)}</dd>
            </div>
          </dl>
        </div>
      </div>

      <ConfirmDialog
        open={confirm !== null}
        title={
          confirm === "deactivate"
            ? "Desactivar usuario"
            : confirm === "activate"
              ? "Activar usuario"
              : confirm === "reset-password"
                ? "Restablecer contraseña"
                : "Revocar sesiones"
        }
        description={
          confirm === "deactivate"
            ? "Esto desactivará al usuario y revocará las sesiones activas."
            : confirm === "activate"
              ? "Esto permitirá al usuario iniciar sesión de nuevo."
              : confirm === "reset-password"
                ? "Esto generará una contraseña temporal, exigirá el cambio de contraseña y revocará las sesiones."
                : "Esto revocará todas las sesiones activas de este usuario."
        }
        confirmLabel={
          confirm === "deactivate"
            ? "Desactivar"
            : confirm === "activate"
              ? "Activar"
              : confirm === "reset-password"
                ? "Restablecer contraseña"
                : "Revocar sesiones"
        }
        tone={confirm === "deactivate" ? "danger" : "primary"}
        loading={actionLoading}
        onCancel={() => {
          if (!actionLoading) {
            setConfirm(null);
            setReason("");
          }
        }}
        onConfirm={handleConfirmedAction}
      >
        {confirm === "deactivate" || confirm === "activate" ? (
          <label className="block text-sm text-slate-700">
            Motivo (opcional)
            <input
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              maxLength={500}
            />
          </label>
        ) : null}
      </ConfirmDialog>
    </div>
  );
}
