import type { ReactNode } from "react";

import { AuthorityShell } from "@/components/authority/authority-shell";
import { AuthorityRoute } from "@/components/auth/authority-route";

export default function AuthorityLayout({ children }: Readonly<{ children: ReactNode }>) {
  return <AuthorityRoute><AuthorityShell>{children}</AuthorityShell></AuthorityRoute>;
}
