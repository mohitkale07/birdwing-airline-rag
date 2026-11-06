import Link from "next/link";
import Image from "next/image";

export default function AuthCard({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <main className="grid min-h-dvh bg-bg lg:grid-cols-[1fr_1fr]">
      <section className="relative hidden overflow-hidden bg-[#203b3a] p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="absolute -right-36 -top-32 size-[520px] rounded-full border border-[#d0ad7b]/15" />
        <div className="absolute -right-12 -top-8 size-[360px] rounded-full border border-[#d0ad7b]/15" />
        <div className="absolute bottom-12 right-12 h-1 w-20 rounded-full bg-[#c18a57]" />
        <Link href="/" className="relative flex items-center gap-3">
          <Image
            src="/birdwing-logo.svg"
            alt=""
            width={40}
            height={40}
            className="size-10 rounded-xl bg-white p-1 object-contain"
          />
          <span className="text-lg font-bold tracking-tight">Birdwing Airlines</span>
        </Link>
        <div className="relative max-w-lg pb-12">
          <div className="mb-5 inline-flex rounded-full border border-[#d0ad7b]/30 bg-white/5 px-3 py-1.5 text-xs font-medium text-[#e8d8c0]">
            Birdwing Airlines knowledge, in one place
          </div>
          <h1 className="text-5xl font-bold leading-[1.12] tracking-[-.04em]">
            Good decisions start with clear answers.
          </h1>
          <p className="mt-5 max-w-md text-base leading-7 text-[#e5e9e3]/75">
            Get grounded answers from Birdwing Airlines’ knowledge base,
            whenever you need them.
          </p>
        </div>
        <p         className="relative text-xs text-[#e5e9e3]/60">
          Secure access for Birdwing Airlines employees and administrators
        </p>
      </section>
      <section className="flex min-h-dvh items-center justify-center px-5 py-12">
        <div className="w-full max-w-[420px]">
          <Link href="/" className="mb-10 inline-flex items-center gap-2 lg:hidden">
            <Image
              src="/birdwing-logo.svg"
              alt=""
              width={36}
              height={36}
              className="size-9 rounded-lg bg-[#e7eeea] p-1 object-contain"
            />
            <span className="font-bold">Birdwing Airlines</span>
          </Link>
          <div className="mb-8">
            <div className="mb-3 text-xs font-bold uppercase tracking-[.16em] text-accent">
              {eyebrow}
            </div>
            <h2 className="text-3xl font-bold tracking-[-.03em]">{title}</h2>
            <p className="mt-2 text-sm leading-6 text-muted">{description}</p>
          </div>
          {children}
        </div>
      </section>
    </main>
  );
}
