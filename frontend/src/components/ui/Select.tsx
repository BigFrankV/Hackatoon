import type { SelectHTMLAttributes } from "react";

interface Option {
  value: string;
  label: string;
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  options: Option[];
  error?: string;
  placeholder?: string;
}

export function Select({
  label,
  options,
  error,
  id,
  className = "",
  placeholder,
  ...props
}: SelectProps) {
  const selectId = id || props.name;
  return (
    <label className="block space-y-1">
      <span className="text-sm font-medium text-slate-700">{label}</span>
      <select
        id={selectId}
        {...props}
        className={`w-full rounded-md border px-3 py-2 text-sm text-slate-900 shadow-sm outline-none transition focus:border-slate-400 focus:ring-2 focus:ring-slate-200 ${
          error ? "border-red-400" : "border-slate-300"
        } ${className}`}
      >
        {placeholder ? <option value="">{placeholder}</option> : null}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {error ? <span className="block text-xs text-red-600">{error}</span> : null}
    </label>
  );
}
