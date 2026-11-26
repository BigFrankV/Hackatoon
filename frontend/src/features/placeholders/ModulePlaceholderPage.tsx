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
        title="Módulo en preparación"
        description="La estructura y los permisos están listos; la funcionalidad de este módulo se implementará en las siguientes fases."
      />
    </div>
  );
}
