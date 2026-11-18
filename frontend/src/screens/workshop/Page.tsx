/** The frame every workshop screen shares: the graphite top bar and one centred column. */
import type { ReactNode } from "react";

import { TopBar } from "../../components/ui";

export function Page({ title, back = "/workshop", children }: { title: string; back?: string; children: ReactNode }) {
  return (
    <>
      <TopBar title={title} back={back} />
      <main className="mx-auto max-w-3xl space-y-8 px-4 pt-5 pb-16">{children}</main>
    </>
  );
}

/** Owners change the workshop; staff only read it. */
export function isOwner(role: string | undefined): boolean {
  return role === "owner";
}
