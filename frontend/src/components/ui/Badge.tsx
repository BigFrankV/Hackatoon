import type { PropsWithChildren } from "react";

type Tone = "gray" | "green" | "red" | "yellow" | "blue";

const tones: Record<Tone, string> = {
  gray: "bg-slate-100 text-slate-700",
  green: "bg-green-100 text-green-700",
  red: "bg-red-100 text-red-700",
  yellow: "bg-amber-100 text-amber-800",
  blue: "bg-blue-100 text-blue-700",
};

export function Badge({
  children,
  tone = "gray",
  className = "",
}: PropsWithChildren<{ tone?: Tone; className?: string }>) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${tones[tone]} ${className}`}
    >
      {children}
    </span>
  );
}
