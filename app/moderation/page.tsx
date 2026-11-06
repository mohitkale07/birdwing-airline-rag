"use client";

import Link from "next/link";
import { useGetMeQuery, useGetModerationDashboardQuery } from "../../src/services/api";

export default function ModerationPage() {
  const { data: user, isLoading } = useGetMeQuery();
  const dashboard = useGetModerationDashboardQuery(undefined, {
    skip: !user || (user.role !== "admin" && user.role !== "moderator"),
  });
  if (isLoading) return <main className="grid min-h-dvh place-items-center text-muted">Checking access…</main>;
  if (!user) return <PageMessage text="Sign in to access moderation." link="/login" linkText="Sign in" />;
  if (user.role !== "admin" && user.role !== "moderator") {
    return <PageMessage text="You don’t have permission to access moderation." link="/chat" linkText="Return to chat" />;
  }
  return (
    <main className="grid min-h-dvh place-items-center px-5">
      <section className="w-full max-w-xl rounded-3xl border border-line bg-white p-8 text-center shadow-sm">
        <div className="mx-auto mb-4 grid size-12 place-items-center rounded-2xl bg-[#e7eeea] text-xl text-accent">✓</div>
        <div className="text-xs font-bold uppercase tracking-[.15em] text-accent">Moderation access</div>
        <h1 className="mt-2 text-3xl font-bold">You’re all set</h1>
        <p className="mt-3 text-muted">{dashboard.data?.message ?? "Access granted."}</p>
        <p className="mt-1 text-sm capitalize text-muted">Role: {dashboard.data?.role ?? user.role}</p>
        {dashboard.error && <p role="alert" className="mt-4 text-sm text-danger">Unable to verify moderation access.</p>}
        <Link href="/chat" className="mt-7 inline-flex rounded-xl bg-accent px-5 py-3 text-sm font-semibold text-white">Open assistant</Link>
      </section>
    </main>
  );
}

function PageMessage({ text, link, linkText }: { text: string; link: string; linkText: string }) {
  return <main className="grid min-h-dvh place-items-center px-5 text-center"><div><p>{text}</p><Link className="mt-3 inline-block font-semibold text-accent" href={link}>{linkText}</Link></div></main>;
}
