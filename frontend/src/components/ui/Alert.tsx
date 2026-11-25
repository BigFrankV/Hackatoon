import type { PropsWithChildren } from "react";

type AlertVariant = "info" | "success" | "error" | "warning";

const styles: Record<AlertVariant, string> = {
  info: "border-blue-200 bg-blue-50 text-blue-800",
  success: "border-green-200 bg-green-50 text-green-800",
  error: "border-red-200 bg-red-50 text-red-800",
  warning: "border-amber-200 bg-amber-50 text-amber-800",
};

export function Alert({
  variant = "info",
  children,
  className = "",
}: PropsWithChildren<{ variant?: AlertVariant; className?: string }>) {
  return (
    <div className={`rounded-md border px-4 py-3 text-sm ${styles[variant]} ${className}`}>
      {children}
    </div>
  );
}
