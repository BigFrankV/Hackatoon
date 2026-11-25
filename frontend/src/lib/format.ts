export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString();
}

const STATUS_LABELS: Record<string, string> = {
  super_admin: "Superadministrador",
  admin: "Administrador",
  user: "Usuario",
  active: "Activo",
  inactive: "Inactivo",
  suspended: "Suspendido",
  invited: "Invitado",
  locked: "Bloqueado",
  must_change_password: "Debe cambiar la contraseña",
  deactivated: "Desactivado",
};

export function formatStatus(status: string): string {
  return (
    STATUS_LABELS[status] ??
    status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
  );
}

export function statusTone(
  status: string,
): "gray" | "green" | "red" | "yellow" | "blue" {
  switch (status) {
    case "active":
      return "green";
    case "inactive":
    case "suspended":
      return "red";
    case "invited":
    case "locked":
      return "yellow";
    default:
      return "gray";
  }
}
