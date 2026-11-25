import { EmptyState } from "@/components/ui/EmptyState";

interface ModulePlaceholderPageProps {
  title: string;
  description: string;
}

export function ModulePlaceholderPage({ title, description }: ModulePlaceholderPageProps) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">{title}</h1>
        <p className="mt-1 text-sm text-slate-600">{description}</p>
      </div>
      <EmptyState
        title="Módulo no implementado en Tramo 4"
        description="Esta sección es un marcador de posición de navegación. La implementación funcional está prevista para etapas posteriores."
      />
    </div>
  );
}
