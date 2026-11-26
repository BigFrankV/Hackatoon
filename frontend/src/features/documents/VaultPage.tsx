import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Alert } from "@/components/ui/Alert";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageLoader } from "@/components/ui/PageLoader";
import {
  CompanyDocument,
  listDocuments,
  retryDocument,
  uploadDocument,
} from "@/lib/api/documents";
import { formatDateTime } from "@/lib/format";

const statusLabels: Record<CompanyDocument["status"], string> = {
  uploaded: "Cargado",
  queued: "En cola",
  processing: "Procesando",
  completed: "Listo para consultar",
  failed: "Falló",
  ready: "Listo",
};

export function VaultPage() {
  const [documents, setDocuments] = useState<CompanyDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      setDocuments(await listDocuments());
    } catch {
      setError("No se pudieron cargar los documentos de la empresa.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedFile) return;
    const form = event.currentTarget;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await uploadDocument(selectedFile);
      setSelectedFile(null);
      form.reset();
      setNotice("Documento recibido; la extracción y generación de embeddings quedó en cola.");
      await refresh();
    } catch {
      setError("No se pudo cargar el archivo. Verifica que sea un PDF o DOCX válido.");
    } finally {
      setBusy(false);
    }
  }

  async function handleRetry(documentId: string) {
    setBusy(true);
    setError(null);
    try {
      await retryDocument(documentId);
      setNotice("El procesamiento del documento se volvió a poner en cola.");
      await refresh();
    } catch {
      setError("No se pudo reintentar el procesamiento del documento.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <PageLoader />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Repositorio</h1>
        <p className="mt-1 text-sm text-slate-600">
          Sube antecedentes PDF o DOCX. El chat podrá consultarlos cuando el estado indique que están listos.
        </p>
      </div>

      {error ? <Alert variant="error">{error}</Alert> : null}
      {notice ? <Alert variant="success">{notice}</Alert> : null}

      <form
        onSubmit={(event) => void handleUpload(event)}
        className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
      >
        <label htmlFor="document-file" className="block text-sm font-medium text-slate-800">
          Documento PDF o DOCX
        </label>
        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            id="document-file"
            type="file"
            accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
            className="block w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 file:mr-3 file:rounded file:border-0 file:bg-slate-100 file:px-3 file:py-1.5 file:text-sm file:font-medium"
          />
          <button
            type="submit"
            disabled={!selectedFile || busy}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {busy ? "Procesando..." : "Cargar documento"}
          </button>
        </div>
        <p className="text-xs text-slate-500">
          El archivo se guarda en almacenamiento privado; el límite configurado se valida en el servidor.
        </p>
      </form>

      {documents.length === 0 ? (
        <EmptyState
          title="Aún no hay documentos"
          description="Carga un PDF o DOCX para iniciar la extracción y búsqueda semántica."
          action={
            <Link to="/app/chat" className="text-sm font-medium text-slate-800 underline">
              Abrir chat
            </Link>
          }
        />
      ) : (
        <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-200 px-5 py-4">
            <h2 className="font-semibold text-slate-900">Documentos de la empresa</h2>
          </div>
          <ul className="divide-y divide-slate-100">
            {documents.map((document) => (
              <li key={document.id} className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <p className="truncate font-medium text-slate-900">{document.title}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    Versión {document.version_number} · {formatDateTime(document.created_at)}
                  </p>
                  {document.error_code ? (
                    <p className="mt-1 text-xs text-red-700">Error: {document.error_code}</p>
                  ) : null}
                </div>
                <div className="flex items-center gap-3">
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
                    {statusLabels[document.status]}
                  </span>
                  {document.status === "failed" ? (
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => void handleRetry(document.id)}
                      className="text-sm font-medium text-slate-700 underline disabled:opacity-50"
                    >
                      Reintentar
                    </button>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
