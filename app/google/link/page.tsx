"use client";

import Link from "next/link";
import { useState } from "react";
import AuthCard from "../../components/AuthCard";
import {
  useGetMeQuery,
  useLinkGoogleMutation,
  useUnlinkGoogleMutation,
} from "../../../src/services/api";

export default function GoogleLinkPage() {
  const { data: user, isLoading } = useGetMeQuery();
  const [linkGoogle, linkState] = useLinkGoogleMutation();
  const [unlinkGoogle, unlinkState] = useUnlinkGoogleMutation();
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (isLoading) return <main className="grid min-h-dvh place-items-center text-muted">Loading account…</main>;
  if (!user) {
    return (
      <AuthCard eyebrow="Account settings" title="Sign in required" description="Sign in before connecting a Google account.">
        <Link className="flex h-12 items-center justify-center rounded-xl bg-accent font-semibold text-white" href="/login">Sign in</Link>
      </AuthCard>
    );
  }

  return (
    <AuthCard
      eyebrow="Connected accounts"
      title="Google account"
      description={`Manage the Google connection for ${user.email}.`}
    >
      <div className="flex items-center gap-3 rounded-2xl border border-line bg-panel-2 p-4">
        <div className="grid size-11 place-items-center rounded-full bg-white text-lg font-bold text-[#4285f4]">G</div>
        <div className="flex-1">
          <div className="text-sm font-semibold">Google</div>
          <div className="text-xs text-muted">Connect for faster sign-in</div>
        </div>
        <span className="rounded-full bg-slate-200 px-2.5 py-1 text-[11px] font-semibold text-slate-700">Manage</span>
      </div>
      <button
        disabled={linkState.isLoading}
        onClick={async () => {
          setNotice(null);
          setError(null);
          try {
            const response = await linkGoogle().unwrap();
            const url = response.authorization_url ?? response.url;
            if (url) window.location.assign(url);
            else setNotice(response.message ?? "Google account linking was started.");
          } catch {
            setError("Could not start Google account linking. Please try again.");
          }
        }}
        className="mt-5 h-12 w-full rounded-xl bg-accent text-sm font-semibold text-white transition hover:bg-[#194744] disabled:opacity-60"
      >
        {linkState.isLoading ? "Connecting…" : "Connect Google account"}
      </button>
      <button
        disabled={unlinkState.isLoading}
        onClick={async () => {
          setNotice(null);
          setError(null);
          try {
            const response = await unlinkGoogle().unwrap();
            setNotice(response.message ?? "Google account disconnected.");
          } catch {
            setError("Could not disconnect the Google account.");
          }
        }}
        className="mt-3 h-11 w-full rounded-xl border border-line text-sm font-semibold transition hover:bg-panel-2 disabled:opacity-60"
      >
        {unlinkState.isLoading ? "Disconnecting…" : "Disconnect Google account"}
      </button>
      {(notice || error) && (
        <p role={error ? "alert" : "status"} className={`mt-4 text-sm ${error ? "text-danger" : "text-emerald-700"}`}>
          {error ?? notice}
        </p>
      )}
      <Link href="/chat" className="mt-6 block text-center text-sm font-semibold text-accent hover:underline">Back to assistant</Link>
    </AuthCard>
  );
}
