import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { ApiRequestError } from "@/lib/api/client";
import { createCompanyUser } from "@/lib/api/company";
import type { UserStatus } from "@/types";

export function CompanyUserCreatePage() {
  const navigate = useNavigate();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tempPassword, setTempPassword] = useState<string | null>(null);
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    status: "active" as UserStatus,
  });

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setTempPassword(null);
    if (!form.first_name.trim() || !form.last_name.trim() || !form.email.trim()) {
      setError("El nombre, el apellido y el correo electrónico son obligatorios.");
      return;
    }
    setSaving(true);
    try {
      const result = await createCompanyUser({
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        email: form.email.trim().toLowerCase(),
        status: form.status,
      });
      const pw = result.temporary_password || null;
      if (pw) {
        setTempPassword(pw);
      } else {
        navigate(`/app/settings/users/${result.user.id}`, { replace: true });
      }
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "No se pudo crear el usuario.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Crear usuario de la empresa</h1>
        <p className="mt-1 text-sm text-slate-600">
          Crea un usuario nuevo en tu empresa. El rol se asigna como <strong>Usuario</strong> por defecto.
        </p>
      </div>

      {error ? <Alert variant="error">{error}</Alert> : null}
      {tempPassword ? (
        <Alert variant="warning">
          <p className="font-medium">Usuario creado. Contraseña temporal (guárdala y compártela de forma segura):</p>
          <p className="mt-1 font-mono text-sm">{tempPassword}</p>
          <div className="mt-3">
            <Link to="/app/settings/users" className="font-medium underline">
              Ir a los usuarios de la empresa
            </Link>
          </div>
        </Alert>
      ) : null}

      <form
        className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm space-y-4 max-w-2xl"
        onSubmit={handleSubmit}
      >
        <div className="grid gap-4 md:grid-cols-2">
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
        </div>
        <Input
          label="Correo electrónico"
          name="email"
          type="email"
          value={form.email}
          onChange={(e) => setForm((p) => ({ ...p, email: e.target.value }))}
          required
          maxLength={255}
        />
        <Select
          label="Estado inicial"
          name="status"
          value={form.status}
          onChange={(e) => setForm((p) => ({ ...p, status: e.target.value as UserStatus }))}
          options={[
            { value: "active", label: "Activo" },
            { value: "inactive", label: "Inactivo" },
            { value: "invited", label: "Invitado" },
          ]}
        />
        <div className="flex gap-3 pt-2">
          <Button type="submit" loading={saving}>
            Crear usuario
          </Button>
          <Link to="/app/settings/users">
            <Button type="button" variant="secondary">
              Cancelar
            </Button>
          </Link>
        </div>
      </form>
    </div>
  );
}
