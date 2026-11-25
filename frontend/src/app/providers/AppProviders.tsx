import type { PropsWithChildren } from "react";

// Global providers will be added in later tranches (auth, query client, etc.).
export function AppProviders({ children }: PropsWithChildren) {
  return children;
}
