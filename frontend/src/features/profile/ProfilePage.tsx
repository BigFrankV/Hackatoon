import { useEffect, useState, type FormEvent } from "react";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ApiRequestError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";
import { formatStatus } from "@/lib/format";
import { ROLE_LABELS } from "@/lib/permissions";

export function ProfilePage() {
  const { user, updateProfile, changePassword } = useAuth();
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [profileSuccess, setProfileSuccess] = useState<string | null>(null);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordSuccess, setPasswordSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      setFirstName(user.first_name);
      setLastName(user.last_name);
    }
  }, [user]);

  if (!user) return null;

  const handleProfileSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setProfileError(null);
    setProfileSuccess(null);
    if (!firstName.trim() || !lastName.trim()) {
      setProfileError("El nombre y el apellido son obligatorios.");
      return;
    }
    setProfileSaving(true);
    try {
      await updateProfile({
        first_name: firstName.trim(),
        last_name: lastName.trim(),
      });
      setProfileSuccess("Perfil actualizado correctamente.");
    } catch (err) {
      setProfileError(err instanceof ApiRequestError ? err.message : "No se pudo actualizar el perfil.");
    } finally {
      setProfileSaving(false);
    }
  };

  const handlePasswordSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setPasswordError(null);
    setPasswordSuccess(null);

    if (!currentPassword || !newPassword || !confirmPassword) {
      setPasswordError("Todos los campos de la contraseña son obligatorios.");
      return;
    }
    if (newPassword.length < 8) {
      setPasswordError("La nueva contraseña debe tener al menos 8 caracteres.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError("La nueva contraseña y la confirmación no coinciden.");
      return;
    }

    setPasswordSaving(true);
    try {
      const message = await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setPasswordSuccess(message || "Contraseña cambiada correctamente.");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setPasswordError(
        err instanceof ApiRequestError ? err.message : "No se pudo cambiar la contraseña.",
      );
    } finally {
      setPasswordSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Mi perfil</h1>
        <p className="mt-1 text-sm text-slate-600">
          Gestiona tus datos personales y tu contraseña.
        </p>
      </div>

      {user.must_change_password ? (
        <Alert variant="warning">
          Tu cuenta requiere un cambio de contraseña. Actualízala para seguir usando la plataforma de forma segura.
        </Alert>
      ) : null}

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">Datos del perfil</h2>
          <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-slate-500">Correo electrónico</dt>
              <dd className="font-medium text-slate-900">{user.email}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Rol</dt>
              <dd className="font-medium text-slate-900">{ROLE_LABELS[user.role]}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Empresa</dt>
              <dd className="font-medium text-slate-900">
                {user.company?.display_name || user.company?.legal_name || "Plataforma"}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Estado</dt>
              <dd className="font-medium text-slate-900">{formatStatus(user.status)}</dd>
            </div>
          </dl>

          <form className="mt-6 space-y-4" onSubmit={handleProfileSubmit}>
            {profileError ? <Alert variant="error">{profileError}</Alert> : null}
            {profileSuccess ? <Alert variant="success">{profileSuccess}</Alert> : null}
            <Input
              label="Nombre"
              name="first_name"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              maxLength={100}
              required
            />
            <Input
              label="Apellido"
              name="last_name"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              maxLength={100}
              required
            />
            <Button type="submit" loading={profileSaving}>
              Guardar cambios
            </Button>
          </form>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">Cambiar contraseña</h2>
          <p className="mt-1 text-sm text-slate-600">
            Al actualizar tu contraseña se revocan las sesiones existentes y se mantiene activa la sesión actual.
          </p>

          <form className="mt-6 space-y-4" onSubmit={handlePasswordSubmit}>
            {passwordError ? <Alert variant="error">{passwordError}</Alert> : null}
            {passwordSuccess ? <Alert variant="success">{passwordSuccess}</Alert> : null}
            <Input
              label="Contraseña actual"
              name="current_password"
              type="password"
              autoComplete="current-password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
            />
            <Input
              label="Nueva contraseña"
              name="new_password"
              type="password"
              autoComplete="new-password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              minLength={8}
              required
            />
            <Input
              label="Confirmar nueva contraseña"
              name="confirm_new_password"
              type="password"
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              minLength={8}
              required
            />
            <Button type="submit" loading={passwordSaving}>
              Actualizar contraseña
            </Button>
          </form>
        </div>
      </section>
    </div>
  );
}
