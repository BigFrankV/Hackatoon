import type { InputHTMLAttributes } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  hint?: string;
}

export function Input({ label, error, hint, id, className = "", ...props }: InputProps) {
  const inputId = id || props.name;
  return (
    <label className="block space-y-1">
      <span className="text-sm font-medium text-slate-700">{label}</span>
      <input
        id={inputId}
        {...props}
        className={`w-full rounded-md border px-3 py-2 text-sm text-slate-900 shadow-sm outline-none transition focus:border-slate-400 focus:ring-2 focus:ring-slate-200 ${
          error ? "border-red-400" : "border-slate-300"
        } ${className}`}
      />
      {error ? <span className="block text-xs text-red-600">{error}</span> : null}
      {!error && hint ? <span className="block text-xs text-slate-500">{hint}</span> : null}
    </label>
  );
}
