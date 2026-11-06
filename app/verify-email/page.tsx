"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";
import AuthCard from "../components/AuthCard";
import {
  useResendVerificationEmailMutation,
  useVerifyEmailMutation,
} from "../../src/services/api";

function VerificationForm() {
  const params = useSearchParams();
  const [token, setToken] = useState(params?.get("token") ?? "");
  const [email, setEmail] = useState(params?.get("email") ?? "");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [verify, verifyState] = useVerifyEmailMutation();
  const [resend, resendState] = useResendVerificationEmailMutation();

  const submitToken = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setStatus(null);
    try {
      const response = await verify({ token }).unwrap();
      setStatus(response.message ?? "Your email has been verified. You can now sign in.");
    } catch {
      setError("That verification token is invalid or expired. Request a new email and try again.");
    }
  };

  const resendEmail = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setStatus(null);
    try {
      const response = await resend({ email }).unwrap();
      setStatus(response.message ?? "If your account needs verification, a new email is on its way.");
    } catch {
      setError("We couldn’t send a verification email. Check the address and try again.");
    }
  };

  return (
    <AuthCard
      eyebrow="One last step"
      title="Verify your email"
      description="Enter the verification token from your email, or request a fresh verification message."
    >
      <form onSubmit={submitToken} className="space-y-4">
        <label className="block text-sm font-semibold">
          Verification token
          <input
            required
            value={token}
            onChange={(event) => setToken(event.target.value)}
            placeholder="Paste your email token"
            className="mt-2 h-12 w-full rounded-xl border border-line bg-panel px-3.5 text-sm font-normal outline-none focus:border-accent focus:ring-4 focus:ring-accent/15"
          />
        </label>
        <button
          disabled={verifyState.isLoading}
          className="h-12 w-full rounded-xl bg-accent text-sm font-semibold text-white transition hover:bg-[#194744] disabled:opacity-60"
        >
          {verifyState.isLoading ? "Verifying…" : "Verify email"}
        </button>
      </form>
      <div className="my-6 border-t border-line" />
      <form onSubmit={resendEmail} className="space-y-3">
        <label className="block text-sm font-semibold">
          Didn’t get the email?
          <input
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@company.com"
            className="mt-2 h-12 w-full rounded-xl border border-line bg-panel px-3.5 text-sm font-normal outline-none focus:border-accent focus:ring-4 focus:ring-accent/15"
          />
        </label>
        <button
          type="submit"
          disabled={resendState.isLoading}
          className="h-11 w-full rounded-xl border border-line text-sm font-semibold transition hover:bg-panel-2 disabled:opacity-60"
        >
          {resendState.isLoading ? "Sending…" : "Resend verification email"}
        </button>
      </form>
      {(status || error) && (
        <div
          role={error ? "alert" : "status"}
          className={`mt-4 rounded-xl px-3.5 py-3 text-sm ${
            error ? "bg-danger-bg text-danger" : "bg-emerald-50 text-emerald-800"
          }`}
        >
          {error ?? status}
        </div>
      )}
      <p className="mt-6 text-center text-sm text-muted">
        <Link href="/login" className="font-semibold text-accent hover:underline">
          Back to sign in
        </Link>
      </p>
    </AuthCard>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<div className="grid min-h-dvh place-items-center text-muted">Loading verification…</div>}>
      <VerificationForm />
    </Suspense>
  );
}
