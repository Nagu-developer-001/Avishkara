import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

type PageLayoutProps = {
  children: ReactNode;
  className?: string;
};

type PageSectionProps = PageLayoutProps & {
  label?: string;
};

export function PageLayout({ children, className }: Readonly<PageLayoutProps>) {
  return <div className={cn("page-shell", className)}>{children}</div>;
}

export function PageMainSection({ children, className, label }: Readonly<PageSectionProps>) {
  return (
    <section className={cn("page-main-section", className)} aria-label={label}>
      {children}
    </section>
  );
}

export function PageSupportingSection({ children, className, label }: Readonly<PageSectionProps>) {
  return (
    <section className={cn("page-supporting-section", className)} aria-label={label}>
      {children}
    </section>
  );
}
