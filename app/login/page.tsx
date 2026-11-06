"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useDispatch } from "react-redux";
import AuthCard from "../components/AuthCard";
import { setCurrentUser } from "../../src/features/authSlice";
import {
  useLazyGetGoogleLoginQuery,
  useLazyGetMeQuery,
  useLoginMutation,
} from "../../src/services/api";

function messageFromError(error: unknown): string {
  if (typeof error === "object" && error !== null && "data" in error) {
    const data = error.data;
    if (typeof data === "string") return data;
    if (typeof data === "object" && data !== null && "detail" in data) {
      return String(data.detail);
    }
  }
  return "We couldn’t sign you in. Check your details and try again.";
}

export default function LoginPage() {
  const router = useRouter();
  const dispatch = useDispatch();
  const [login, loginState] = useLoginMutation();
  const [startGoogleLogin, googleLoginState] = useLazyGetGoogleLoginQuery();
  const [getMe] = useLazyGetMeQuery();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    try {
      await login({ email, password }).unwrap();
      const user = await getMe().unwrap();
      dispatch(setCurrentUser(user));
      router.replace(
        user.role === "admin"
          ? "/admin"
          : user.role === "moderator"
            ? "/moderation"
            : "/chat",
      );
    } catch (reason) {
      setError(messageFromError(reason));
    }
  };

  const continueWithGoogle = async () => {
    setError(null);
    try {
      const response = await startGoogleLogin().unwrap();
      const url = response.authorization_url ?? response.url;
      if (url) {
        window.location.assign(url);
        return;
      }
    } catch {
      // OAuth redirects are sometimes blocked by fetch; retry as a browser navigation.
    }
    window.location.assign(
      `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1"}/auth/google/login`,
    );
  };

  return (
    <AuthCard
      eyebrow="Welcome back"
      title="Sign in to Birdwing"
      description="Use your Birdwing Airlines account to access saved conversations and airline knowledge."
    >
      <form onSubmit={submit} className="space-y-4">
        <label className="block text-sm font-semibold">
          Work email
          <input
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@company.com"
            className="mt-2 h-12 w-full rounded-xl border border-line bg-panel px-3.5 text-sm font-normal outline-none transition placeholder:text-slate-400 focus:border-accent focus:ring-4 focus:ring-accent/15"
          />
        </label>
        <label className="block text-sm font-semibold">
          Password
          <input
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Enter your password"
            className="mt-2 h-12 w-full rounded-xl border border-line bg-panel px-3.5 text-sm font-normal outline-none transition placeholder:text-slate-400 focus:border-accent focus:ring-4 focus:ring-accent/15"
          />
        </label>
        {error && (
          <div role="alert" className="rounded-xl bg-danger-bg px-3.5 py-3 text-sm text-danger">
            {error}
          </div>
        )}
        <button
          type="submit"
          disabled={loginState.isLoading}
          className="h-12 w-full rounded-xl bg-accent text-sm font-semibold text-white transition hover:bg-[#194744] disabled:opacity-60"
        >
          {loginState.isLoading ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <div className="my-5 flex items-center gap-3 text-xs text-muted">
        <span className="h-px flex-1 bg-line" />
        OR
        <span className="h-px flex-1 bg-line" />
      </div>
      <button
        type="button"
        disabled={googleLoginState.isFetching}
        onClick={() => void continueWithGoogle()}
        className="flex h-12 w-full items-center justify-center gap-2 rounded-xl border border-line bg-white text-sm font-semibold transition hover:bg-panel-2 disabled:opacity-60"
      >
        <span className="text-base font-bold text-[#4285f4]">G</span>
        {googleLoginState.isFetching ? "Connecting…" : "Continue with Google"}
      </button>
      <p className="mt-7 text-center text-sm text-muted">
        New to Birdwing?{" "}
        <Link href="/signup" className="font-semibold text-accent hover:underline">
          Create an account
        </Link>
      </p>
      <p className="mt-4 text-center text-xs leading-5 text-muted">
        Administrator access is assigned by your organization. Sign in with
        your admin account to open the admin dashboard.
      </p>
    </AuthCard>
  );
}
