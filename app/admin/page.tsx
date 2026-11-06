"use client";

import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { useDispatch } from "react-redux";
import { clearCredentials } from "../../src/features/authSlice";
import {
  useGetAdminDashboardQuery,
  useGetAdminMetricsQuery,
  useGetMeQuery,
  useGetUsersQuery,
  useLogoutMutation,
  useUpdateUserRestrictionMutation,
} from "../../src/services/api";

const metricCards = [
  { key: "total_users", label: "Total users" },
  { key: "active_users", label: "Active users" },
  { key: "total_conversations", label: "Conversations" },
  { key: "total_messages", label: "Messages" },
] as const;

export default function AdminPage() {
  const router = useRouter();
  const dispatch = useDispatch();
  const { data: user, isLoading: userLoading } = useGetMeQuery();
  const isAdmin = user?.role === "admin";
  const dashboard = useGetAdminDashboardQuery(undefined, { skip: !isAdmin });
  const metricsQuery = useGetAdminMetricsQuery(undefined, { skip: !isAdmin });
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const usersQuery = useGetUsersQuery(
    { limit: 20, offset: page * 20, search: search.trim() || undefined },
    { skip: !isAdmin },
  );
  const [updateRestriction] = useUpdateUserRestrictionMutation();
  const [logout] = useLogoutMutation();
  const metrics = metricsQuery.data;
  const pageCount = useMemo(
    () => Math.max(1, Math.ceil((usersQuery.data?.total ?? 0) / 20)),
    [usersQuery.data?.total],
  );

  if (userLoading) return <CenteredState text="Checking your account…" />;
  if (!user) {
    return (
      <CenteredState
        text="Sign in with an administrator account to continue."
        action={<Link className="font-semibold text-accent" href="/login">Sign in</Link>}
      />
    );
  }
  if (!isAdmin) {
    return (
      <CenteredState
        text="You don’t have permission to view this dashboard."
        action={<Link className="font-semibold text-accent" href="/chat">Return to chat</Link>}
      />
    );
  }

  return (
    <main className="min-h-dvh bg-bg">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex h-[72px] max-w-7xl items-center justify-between px-5 md:px-8">
          <Link href="/chat" className="flex items-center gap-3">
            <Image
              src="/birdwing-logo.svg"
              alt=""
              width={36}
              height={36}
              className="size-9 rounded-lg bg-[#e7eeea] p-1 object-contain"
            />
            <span className="font-bold">Birdwing Airlines <span className="ml-1 font-medium text-muted">Admin</span></span>
          </Link>
          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-muted sm:inline">{user.email}</span>
            <button
              onClick={async () => {
                try {
                  await logout().unwrap();
                } finally {
                  dispatch(clearCredentials());
                  router.replace("/");
                }
              }}
              className="rounded-lg border border-line px-3 py-2 text-sm font-medium hover:bg-panel-2"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>
      <div className="mx-auto max-w-7xl px-5 py-9 md:px-8">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <div className="mb-2 text-xs font-bold uppercase tracking-[.15em] text-accent">Overview</div>
            <h1 className="text-3xl font-bold tracking-tight">Admin dashboard</h1>
            <p className="mt-2 text-sm text-muted">
              {dashboard.data?.message ?? "Manage users and monitor workspace activity."}
            </p>
          </div>
          <Link href="/chat" className="rounded-xl border border-line bg-white px-4 py-2.5 text-sm font-semibold hover:bg-panel-2">
            Open assistant
          </Link>
        </div>

        {metricsQuery.error && (
          <ErrorBanner message="Dashboard metrics could not be loaded." />
        )}
        <div className="mb-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {metricCards.map((card) => (
            <div key={card.key} className="rounded-2xl border border-line bg-white p-5 shadow-sm shadow-slate-200/40">
              <div className="text-sm font-medium text-muted">{card.label}</div>
              <div className="mt-3 text-3xl font-bold tracking-tight">
                {metricsQuery.isLoading ? "—" : (metrics?.[card.key] ?? 0).toLocaleString()}
              </div>
            </div>
          ))}
        </div>
        <div className="overflow-hidden rounded-2xl border border-line bg-white shadow-sm shadow-slate-200/40">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-line p-5">
            <div>
              <h2 className="font-bold">People</h2>
              <p className="mt-1 text-sm text-muted">Review account activity and restrictions.</p>
            </div>
            <label className="relative block w-full sm:w-72">
              <span className="sr-only">Search users</span>
              <input
                type="search"
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value);
                  setPage(0);
                }}
                placeholder="Search name or email"
                className="h-10 w-full rounded-lg border border-line bg-panel px-3 text-sm outline-none focus:border-accent focus:ring-4 focus:ring-accent/15"
              />
            </label>
          </div>
          {usersQuery.error ? (
            <div className="p-6"><ErrorBanner message="Could not load users. Try refreshing the page." /></div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="bg-panel-2 text-xs uppercase tracking-wide text-muted">
                  <tr>
                    <th className="px-5 py-3 font-semibold">User</th>
                    <th className="px-5 py-3 font-semibold">Role</th>
                    <th className="px-5 py-3 font-semibold">Activity</th>
                    <th className="px-5 py-3 font-semibold">Status</th>
                    <th className="px-5 py-3 text-right font-semibold">Access</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {usersQuery.data?.items.map((person) => (
                    <tr key={person.id} className="hover:bg-slate-50/70">
                      <td className="px-5 py-4">
                        <div className="font-semibold">{person.name ?? "Unnamed user"}</div>
                        <div className="mt-1 text-xs text-muted">{person.email}</div>
                      </td>
                      <td className="px-5 py-4 capitalize">{person.role}</td>
                      <td className="px-5 py-4 text-muted">
                        {person.conversation_count} chats · {person.message_count} messages
                      </td>
                      <td className="px-5 py-4">
                        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${person.is_verified ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-800"}`}>
                          {person.is_verified ? "Verified" : "Unverified"}
                        </span>
                        {!person.is_active && <span className="ml-2 text-xs text-muted">Inactive</span>}
                      </td>
                      <td className="px-5 py-4 text-right">
                        <button
                          disabled={person.id === user.id}
                          onClick={async () => {
                            try {
                              await updateRestriction({
                                userId: person.id,
                                payload: { is_restricted: !person.is_restricted },
                              }).unwrap();
                            } catch {
                              window.alert("The account restriction could not be updated.");
                            }
                          }}
                          className={`rounded-lg px-3 py-2 text-xs font-semibold disabled:cursor-not-allowed disabled:opacity-40 ${
                            person.is_restricted
                              ? "border border-line hover:bg-panel-2"
                              : "bg-rose-50 text-rose-700 hover:bg-rose-100"
                          }`}
                        >
                          {person.is_restricted ? "Restore access" : "Restrict"}
                        </button>
                      </td>
                    </tr>
                  ))}
                  {!usersQuery.isLoading && !usersQuery.data?.items.length && (
                    <tr><td colSpan={5} className="px-5 py-12 text-center text-muted">No users match your search.</td></tr>
                  )}
                  {usersQuery.isLoading && (
                    <tr><td colSpan={5} className="px-5 py-12 text-center text-muted">Loading users…</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
          <div className="flex items-center justify-between border-t border-line px-5 py-4 text-sm">
            <span className="text-muted">
              {usersQuery.data
                ? `${usersQuery.data.total} total users`
                : "Loading users…"}
            </span>
            <div className="flex items-center gap-2">
              <button
                disabled={page === 0}
                onClick={() => setPage((value) => Math.max(0, value - 1))}
                className="rounded-lg border border-line px-3 py-1.5 disabled:opacity-40"
              >
                Previous
              </button>
              <span className="px-1 text-xs text-muted">{page + 1} / {pageCount}</span>
              <button
                disabled={page + 1 >= pageCount}
                onClick={() => setPage((value) => value + 1)}
                className="rounded-lg border border-line px-3 py-1.5 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}

function CenteredState({ text, action }: { text: string; action?: React.ReactNode }) {
  return (
    <main className="grid min-h-dvh place-items-center px-5 text-center">
      <div>
        <p className="text-lg font-semibold">{text}</p>
        <div className="mt-3">{action}</div>
      </div>
    </main>
  );
}

function ErrorBanner({ message }: { message: string }) {
  return <div role="alert" className="rounded-xl border border-rose-100 bg-danger-bg px-4 py-3 text-sm text-danger">{message}</div>;
}
