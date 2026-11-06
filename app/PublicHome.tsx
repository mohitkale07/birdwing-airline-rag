"use client";

import Link from "next/link";
import Image from "next/image";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useGetMeQuery } from "../src/services/api";

const highlights = [
  {
    number: "01",
    title: "Ask about Birdwing",
    description: "Get clear answers from Birdwing Airlines’ available knowledge.",
  },
  {
    number: "02",
    title: "Know the source",
    description: "Answers include references to the supporting material.",
  },
  {
    number: "03",
    title: "Start instantly",
    description: "Try public chat without creating an account.",
  },
];

export default function PublicHome() {
  const router = useRouter();
  const { data: user, isLoading } = useGetMeQuery();

  useEffect(() => {
    if (user) router.replace("/chat");
  }, [router, user]);

  if (isLoading || user) {
    return (
      <main className="grid min-h-dvh place-items-center bg-bg">
        <div className="flex items-center gap-3 text-sm text-muted">
          <span className="size-4 animate-spin rounded-full border-2 border-line border-t-accent" />
          Loading Birdwing Airlines…
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-dvh overflow-hidden bg-bg">
      <header className="sticky top-0 z-20 border-b border-line/80 bg-bg/95 backdrop-blur-sm">
        <div className="mx-auto flex h-[76px] max-w-7xl items-center justify-between px-5 md:px-10">
          <Link href="/" className="group flex items-center gap-3">
            <Image
              src="/birdwing-logo.svg"
              alt=""
              width={42}
              height={42}
              priority
              className="size-[42px] object-contain transition-transform duration-200 group-hover:scale-[1.04]"
            />
            <span className="flex flex-col leading-tight">
              <span className="text-[15px] font-bold tracking-[-.02em]">BIRDWING</span>
              <span className="mt-1 text-[9px] font-semibold tracking-[.2em] text-muted">AIRLINES</span>
            </span>
          </Link>
          <nav aria-label="Main navigation" className="flex items-center gap-1 sm:gap-3">
            <Link
              href="#how-it-works"
              className="hidden rounded-lg px-3 py-2 text-sm font-medium text-muted transition-colors hover:text-fg md:inline-flex"
            >
              About
            </Link>
            <Link
              href="/login"
              className="rounded-lg px-3 py-2.5 text-sm font-semibold text-fg transition-colors hover:bg-panel-2 sm:px-4"
            >
              Sign in
            </Link>
            <Link
              href="/signup"
              className="motion-hover rounded-lg bg-accent px-3.5 py-2.5 text-sm font-semibold text-white hover:bg-[#194744] sm:px-4"
            >
              Employee portal
            </Link>
          </nav>
        </div>
      </header>

      <section className="relative mx-auto grid max-w-7xl items-center gap-14 px-5 pb-20 pt-12 md:px-10 md:pb-28 md:pt-20 lg:grid-cols-[1.05fr_.95fr]">
        <div className="relative z-10 motion-rise">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-line bg-panel px-3.5 py-2 text-[10px] font-semibold tracking-[.12em] text-accent">
            <span className="size-1.5 rounded-full bg-[#bd7848]" />
            BIRDWING KNOWLEDGE
          </div>
          <h1 className="max-w-2xl text-[44px] font-bold leading-[1.08] tracking-[-.055em] text-fg sm:text-6xl lg:text-[68px]">
            The right answer,
            <span className="block text-[#ae6840]">without the search.</span>
          </h1>
          <p className="mt-6 max-w-xl text-base leading-7 text-slate-600 sm:text-lg sm:leading-8">
            Find answers about Birdwing Airlines in one place. Ask naturally
            and get clear responses grounded in airline knowledge, with sources
            you can check.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link
              href="/public-chat"
              className="motion-hover inline-flex items-center gap-3 rounded-xl bg-accent px-5 py-3.5 text-sm font-semibold text-white hover:bg-[#194744]"
            >
              Try anonymous chat <span className="text-lg leading-none">→</span>
            </Link>
            <Link
              href="/signup"
              className="motion-hover rounded-xl border border-line bg-panel px-5 py-3.5 text-sm font-semibold text-fg hover:bg-panel-2"
            >
              Create an account
            </Link>
          </div>
          <p className="mt-4 text-xs text-muted">
            Anonymous chats aren’t saved. Sign in to keep your history.
          </p>
        </div>

        <div className="relative z-10 mx-auto w-full max-w-[500px] motion-settle">
          <div className="overflow-hidden rounded-[22px] border border-line bg-panel shadow-[0_14px_38px_rgba(42,54,46,.08)]">
            <div className="flex items-center justify-between border-b border-line px-5 py-4">
              <div className="flex items-center gap-3">
                <Image
                  src="/birdwing-logo.svg"
                  alt=""
                  width={36}
                  height={36}
                  className="size-9 rounded-lg bg-[#e7eeea] p-1 object-contain"
                />
                <div>
                    <div className="text-sm font-bold">Birdwing assistant</div>
                  <div className="mt-0.5 flex items-center gap-1.5 text-[11px] text-muted">
                    <span className="size-1.5 rounded-full bg-[#bd7848]" />
                    Ready to help
                  </div>
                </div>
              </div>
              <span className="rounded-full bg-panel-2 px-2.5 py-1 text-[10px] font-semibold text-muted">
                PUBLIC CHAT
              </span>
            </div>
            <div className="space-y-5 bg-[#f7f5ef] p-5 sm:p-6 motion-stagger">
              <div className="max-w-[88%] rounded-2xl rounded-tl-md border border-line bg-panel px-4 py-3 text-sm leading-6">
                Welcome to Birdwing Airlines. What would you like to know?
              </div>
              <div className="ml-auto max-w-[82%] rounded-2xl rounded-tr-md bg-[#e7eeea] px-4 py-3 text-sm leading-6 text-[#294744]">
                What is the cabin baggage allowance?
              </div>
              <div className="max-w-[91%] rounded-2xl rounded-tl-md border border-line bg-panel px-4 py-3 text-sm leading-6">
                Ask about Birdwing Airlines and I’ll find relevant information
                from the available sources.
                <div className="mt-3 border-t border-line pt-3">
                  <div className="mb-2 text-[10px] font-bold uppercase tracking-wider text-muted">Answers grounded in sources</div>
                  <div className="inline-flex rounded-lg bg-panel-2 px-2.5 py-1.5 text-[11px] font-medium text-slate-600">References included</div>
                </div>
              </div>
            </div>
            <div className="border-t border-line p-4">
              <div className="flex items-center rounded-xl border border-line bg-panel p-2 pl-4">
                <span className="flex-1 text-sm text-slate-400">Ask a question…</span>
                <span className="grid size-9 place-items-center rounded-lg bg-accent text-lg text-white">↑</span>
              </div>
              <p className="mt-2 text-center text-[10px] text-muted">Anonymous · No account required</p>
            </div>
          </div>
          <div className="absolute -bottom-5 -left-6 hidden rounded-2xl border border-line bg-white px-4 py-3 shadow-lg sm:block">
            <div className="flex items-center gap-2 text-xs font-semibold">
              <span className="grid size-6 place-items-center rounded-lg bg-[#f4e8d8] text-[#ae6840]">✓</span>
              Grounded in Birdwing sources
            </div>
          </div>
        </div>
      </section>

      <section id="how-it-works" className="scroll-mt-24 border-y border-line bg-[#eeebe2]">
        <div className="mx-auto grid max-w-7xl gap-8 px-5 py-10 md:grid-cols-3 md:px-10 md:py-12 motion-stagger">
          {highlights.map((item) => (
            <div key={item.number} className="flex gap-4">
              <span className="pt-0.5 font-mono text-xs font-semibold text-accent">{item.number}</span>
              <div>
                <h2 className="text-sm font-bold">{item.title}</h2>
                <p className="mt-1.5 max-w-xs text-sm leading-6 text-muted">{item.description}</p>
              </div>
            </div>
          ))}
        </div>
      </section>
      <footer className="mx-auto flex max-w-7xl flex-col gap-3 px-5 py-7 text-xs text-muted sm:flex-row sm:items-center sm:justify-between md:px-10">
        <span>Birdwing Airlines · Answers grounded in airline knowledge.</span>
        <div className="flex gap-5">
          <Link href="/login" className="hover:text-fg">Sign in</Link>
          <Link href="/signup" className="hover:text-fg">Create account</Link>
        </div>
      </footer>
    </main>
  );
}
