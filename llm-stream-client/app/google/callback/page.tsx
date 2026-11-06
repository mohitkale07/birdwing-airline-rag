"use client";

import Link from "next/link";
import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useDispatch } from "react-redux";
import { setCurrentUser } from "../../../src/features/authSlice";
import { useLazyGetGoogleCallbackQuery, useLazyGetMeQuery } from "../../../src/services/api";

function CallbackHandler() {
  const params = useSearchParams();
  const router = useRouter();
  const dispatch = useDispatch();
  const [callback] = useLazyGetGoogleCallbackQuery();
  const [getMe] = useLazyGetMeQuery();
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);
  const providerError = params?.get("error");
  const displayError =
    error ??
    (providerError
      ? "Google sign-in was cancelled or could not be completed."
      : null);

  useEffect(() => {
    if (!params) return;
    if (started.current) return;
    started.current = true;
    if (providerError) {
      return;
    }
    void (async () => {
      try {
        await callback({
          code: params?.get("code") ?? undefined,
          state: params?.get("state") ?? undefined,
        }).unwrap();
        const user = await getMe().unwrap();
        dispatch(setCurrentUser(user));
        router.replace(user.role === "admin" ? "/admin" : "/chat");
      } catch {
        setError("Google sign-in could not be completed. Please return and try again.");
      }
    })();
  }, [callback, dispatch, getMe, params, providerError, router]);

  return (
    <main className="grid min-h-dvh place-items-center px-5 text-center">
      <div className="max-w-md rounded-3xl border border-line bg-white p-8 shadow-sm">
        {!displayError && <div className="mx-auto mb-4 size-8 animate-spin rounded-full border-2 border-line border-t-accent" />}
        <h1 className="text-xl font-bold">{displayError ? "Sign-in issue" : "Finishing Google sign-in…"}</h1>
        {displayError && <p role="alert" className="mt-3 text-sm text-danger">{displayError}</p>}
        {displayError && <Link href="/login" className="mt-5 inline-block font-semibold text-accent">Back to sign in</Link>}
      </div>
    </main>
  );
}

export default function GoogleCallbackPage() {
  return <Suspense fallback={<main className="grid min-h-dvh place-items-center text-muted">Finishing sign-in…</main>}><CallbackHandler /></Suspense>;
}
