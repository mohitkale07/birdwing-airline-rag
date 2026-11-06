"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import AuthCard from "../components/AuthCard";
import { useRegisterMutation } from "../../src/services/api";

function getErrorMessage(error: unknown): string {
  if (typeof error === "object" && error !== null && "data" in error) {
    const data = error.data;
    if (typeof data === "string") return data;
    if (typeof data === "object" && data !== null && "detail" in data) {
      return String(data.detail);
    }
  }
  return "We couldn’t create your account. Please try again.";
}

export default function SignupPage() {
  const router = useRouter();
  const [register, state] = useRegisterMutation();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    try {
      await register({ name, email, password }).unwrap();
      router.push(`/verify-email?email=${encodeURIComponent(email)}`);
    } catch (reason) {
      setError(getErrorMessage(reason));
    }
  };

  return (
    <AuthCard
      eyebrow="Get started"
      title="Create your account"
      description="Set up your Birdwing Airlines account. We’ll send a verification link to finish."
    >
      <form onSubmit={submit} className="space-y-4">
        <label className="block text-sm font-semibold">
          Full name
          <input
            autoComplete="name"
            required
            minLength={2}
            maxLength={150}
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Your name"
            className="mt-2 h-12 w-full rounded-xl border border-line bg-panel px-3.5 text-sm font-normal outline-none focus:border-accent focus:ring-4 focus:ring-accent/15"
          />
        </label>
        <label className="block text-sm font-semibold">
          Work email
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
        <label className="block text-sm font-semibold">
          Password
          <input
            type="password"
            autoComplete="new-password"
            minLength={8}
            maxLength={128}
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="At least 8 characters"
            className="mt-2 h-12 w-full rounded-xl border border-line bg-panel px-3.5 text-sm font-normal outline-none focus:border-accent focus:ring-4 focus:ring-accent/15"
          />
        </label>
        {error && (
          <div role="alert" className="rounded-xl bg-danger-bg px-3.5 py-3 text-sm text-danger">
            {error}
          </div>
        )}
        <button
          disabled={state.isLoading}
          className="h-12 w-full rounded-xl bg-accent text-sm font-semibold text-white transition hover:bg-[#194744] disabled:opacity-60"
        >
          {state.isLoading ? "Creating account…" : "Create account"}
        </button>
      </form>
      <p className="mt-7 text-center text-sm text-muted">
        Already have an account?{" "}
        <Link href="/login" className="font-semibold text-accent hover:underline">
          Sign in
        </Link>
      </p>
      <p className="mt-4 text-center text-xs text-muted">
        Administrator access is provisioned by Birdwing Airlines.
      </p>
    </AuthCard>
  );
}
