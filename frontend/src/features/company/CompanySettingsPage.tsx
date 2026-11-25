import { useCallback, useEffect, useState, type FormEvent } from "react";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { PageLoader } from "@/components/ui/PageLoader";
import { ApiRequestError } from "@/lib/api/client";
import { getCompanyProfile, updateCompanyProfile } from "@/lib/api/company";
import { formatDateTime, formatStatus } from "@/lib/format";
import type { CompanyProfileResponse } from "@/types";

export function CompanySettingsPage() {
  const [company, setCompany] = useState<CompanyProfileResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [form, setForm] = useState({
    display_name: "",
    email: "",
    phone: "",
    address: "",
  });

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getCompanyProfile();
      setCompany(result);
      setForm({
        display_name: result.display_name || "",
        email: result.email || "",
        phone: result.phone || "",
        address: result.address || "",
      });
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "No se pudo cargar el perfil de la empresa.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await updateCompanyProfile({
        display_name: form.display_name.trim() || null,
        email: form.email.trim() || null,
        phone: form.phone.trim() || null,
        address: form.address.trim() || null,
      });
      setCompany(updated);
      setSuccess("Configuración de la empresa actualizada correctamente.");
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "No se pudo actualizar la configuración de la empresa.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <PageLoader />;
  if (error && !company) return <Alert variant="error">{error}</Alert>;
  if (!company) return <Alert variant="error">Perfil de la empresa no encontrado.</Alert>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Configuración de la empresa</h1>
        <p className="mt-1 text-sm text-slate-600">
          Gestiona el perfil de tu empresa y su información de contacto.
        </p>
      </div>

      {error ? <Alert variant="error">{error}</Alert> : null}
      {success ? <Alert variant="success">{success}</Alert> : null}

      <div className="grid gap-6 xl:grid-cols-3">
        <form
          className="xl:col-span-2 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
          onSubmit={handleSubmit}
        >
          <h2 className="text-lg font-semibold text-slate-900">Perfil de la empresa</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <Input
              label="Razón social"
              name="legal_name"
              value={company.legal_name}
              disabled
              hint="La razón social la gestionan los administradores de la plataforma."
            />
            <Input
              label="Nombre visible"
              name="display_name"
              value={form.display_name}
              onChange={(e) => setForm((p) => ({ ...p, display_name: e.target.value }))}
              maxLength={255}
            />
            <Input
              label="ID fiscal"
              name="tax_id"
              value={company.tax_id || ""}
              disabled
              hint="El ID fiscal lo gestionan los administradores de la plataforma."
            />
            <Input
              label="Correo electrónico"
              name="email"
              type="email"
              value={form.email}
              onChange={(e) => setForm((p) => ({ ...p, email: e.target.value }))}
              maxLength={255}
            />
            <Input
              label="Teléfono"
              name="phone"
              value={form.phone}
              onChange={(e) => setForm((p) => ({ ...p, phone: e.target.value }))}
              maxLength= {100}
            />
            <Input
              label="Dirección"
              name="address"
              value={form.address}
              onChange={(e) => setForm((p) => ({ ...p, address: e.target.value }))}
              maxLength={500}
            />
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
              <dt className="text-slate-500">Estado</dt>
              <dd className="text-slate-900">{formatStatus(company.status)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">ID de la empresa</dt>
              <dd className="font-mono text-xs break-all text-slate-700">{company.id}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Creado</dt>
              <dd className="text-slate-900">{formatDateTime(company.created_at)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Actualizado</dt>
              <dd className="text-slate-900">{formatDateTime(company.updated_at)}</dd>
            </div>
          </dl>
        </div>
      </div>
    </div>
  );
}
