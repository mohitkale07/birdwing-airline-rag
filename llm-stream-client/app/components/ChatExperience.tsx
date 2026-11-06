"use client";

import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { useDispatch, useSelector } from "react-redux";
import {
  clearChatStreamEvents,
} from "../../src/features/chatSlice";
import { clearCredentials, setCurrentUser } from "../../src/features/authSlice";
import {
  useDeleteConversationMutation,
  useGetConversationsQuery,
  useGetMeQuery,
  useLazyGetConversationQuery,
  useLogoutMutation,
  useStreamChatMutation,
} from "../../src/services/api";
import type { ChatSource, ChatStreamEvent, StoredChatMessage } from "../../src/schemas/api";
import type { RootState } from "../../src/store";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  error?: string;
  sources?: ChatSource[];
}

const requestId = () => crypto.randomUUID();

type ChatExperienceProps = {
  mode?: "workspace" | "public";
};

export default function ChatExperience({
  mode = "workspace",
}: ChatExperienceProps) {
  const isWorkspace = mode === "workspace";
  const router = useRouter();
  const dispatch = useDispatch();
  const signedInUser = useSelector((state: RootState) => state.auth.user);
  const streamEvents = useSelector((state: RootState) => state.chat.events);
  const { data: sessionUser, error: sessionError } = useGetMeQuery();
  const user = sessionUser ?? signedInUser;
  const { data: conversations } = useGetConversationsQuery(
    { limit: 50, include_archived: false },
    { skip: !isWorkspace || !user },
  );
  const [loadConversation] = useLazyGetConversationQuery();
  const [deleteConversation] = useDeleteConversationMutation();
  const [logout] = useLogoutMutation();
  const [streamChat, streamState] = useStreamChatMutation();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [editedQuestion, setEditedQuestion] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [activeRequest, setActiveRequest] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const processedEvents = useRef({ requestId: null as string | null, count: 0 });
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (sessionUser) dispatch(setCurrentUser(sessionUser));
  }, [dispatch, sessionUser]);

  useEffect(() => {
    if (user && !isWorkspace) router.replace("/chat");
    if (
      isWorkspace &&
      !user &&
      sessionError &&
      "status" in sessionError &&
      sessionError.status === 401
    ) {
      router.replace("/");
    }
  }, [isWorkspace, router, sessionError, user]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  useEffect(() => {
    if (!activeRequest) return;
    if (processedEvents.current.requestId !== activeRequest) {
      processedEvents.current = { requestId: activeRequest, count: 0 };
    }
    const requestEvents = streamEvents.filter(
      (item) => item.requestId === activeRequest,
    );
    const newEvents = requestEvents.slice(processedEvents.current.count);
    processedEvents.current.count = requestEvents.length;
    for (const item of newEvents) {
      const event: ChatStreamEvent = item.event;
      if (event.type === "start") {
        setConversationId(event.conversation_id);
      } else if (event.type === "token") {
        setMessages((current) => {
          const next = [...current];
          const last = next[next.length - 1];
          if (last?.role === "assistant") {
            next[next.length - 1] = {
              ...last,
              content: last.content + event.content,
            };
          }
          return next;
        });
      } else if (event.type === "done") {
        setConversationId(event.conversation_id);
        setMessages((current) => {
          const next = [...current];
          const last = next[next.length - 1];
          if (last?.role === "assistant") {
            next[next.length - 1] = { ...last, sources: event.sources };
          }
          return next;
        });
      } else {
        setMessages((current) => {
          const next = [...current];
          const last = next[next.length - 1];
          if (last?.role === "assistant") {
            next[next.length - 1] = { ...last, error: event.message };
          }
          return next;
        });
      }
    }
  }, [activeRequest, streamEvents]);

  const startNewChat = () => {
    setConversationId(null);
    setMessages([]);
    setInput("");
    setNotice(null);
    dispatch(clearChatStreamEvents());
    processedEvents.current = { requestId: null, count: 0 };
  };

  const selectConversation = async (id: string) => {
    try {
      const data = await loadConversation({ conversationId: id }).unwrap();
      setConversationId(data.id);
      setMessages(data.messages.map(toMessage));
      setSidebarOpen(false);
      setNotice(null);
    } catch {
      setNotice("That conversation could not be loaded. Please try again.");
    }
  };

  const send = async (suggestion?: string) => {
    const text = (suggestion ?? input).trim();
    if (!text || streamState.isLoading) return;
    const id = requestId();
    setNotice(null);
    setMessages((current) => [
      ...current,
      { id: requestId(), role: "user", content: text },
      { id: requestId(), role: "assistant", content: "" },
    ]);
    setInput("");
    setActiveRequest(id);
    processedEvents.current = { requestId: id, count: 0 };
    dispatch(clearChatStreamEvents());
    try {
      await streamChat({
        requestId: id,
        conversation_id: isWorkspace ? conversationId : null,
        text,
      }).unwrap();
    } catch (error) {
      const message =
        typeof error === "object" && error !== null && "data" in error
          ? String(error.data)
          : "The assistant could not answer right now. Please try again.";
      setMessages((current) => {
        const next = [...current];
        const last = next[next.length - 1];
        if (last?.role === "assistant") {
          next[next.length - 1] = { ...last, error: message };
        }
        return next;
      });
    }
  };

  const resendEditedQuestion = async () => {
    const text = editedQuestion.trim();
    if (!text || streamState.isLoading) return;
    setEditingMessageId(null);
    setEditedQuestion("");
    await send(text);
  };

  const handleLogout = async () => {
    try {
      await logout().unwrap();
    } finally {
      dispatch(clearCredentials());
      router.replace("/");
    }
  };

  const hasSessionError =
    sessionError &&
    "status" in sessionError &&
    sessionError.status !== 401 &&
    isWorkspace;

  if (
    (isWorkspace && !user && (!sessionError || ("status" in sessionError && sessionError.status === 401))) ||
    (!isWorkspace && user)
  ) {
    return (
      <main className="grid min-h-dvh place-items-center bg-bg">
        <div className="flex items-center gap-3 text-sm text-muted">
          <span className="size-4 animate-spin rounded-full border-2 border-line border-t-accent" />
          {isWorkspace ? "Opening your workspace…" : "Opening your chat…"}
        </div>
      </main>
    );
  }

  return (
    <div className={`flex h-dvh min-h-[560px] overflow-hidden bg-bg ${isWorkspace ? "" : "flex-col"}`}>
      {isWorkspace && sidebarOpen && (
        <button
          aria-label="Close navigation"
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 z-20 bg-slate-950/20 md:hidden"
        />
      )}
      {isWorkspace && (
        <aside
          className={`fixed inset-y-0 left-0 z-30 flex w-[286px] flex-col border-r border-line bg-white transition-transform md:static md:translate-x-0 ${
            sidebarOpen ? "translate-x-0" : "-translate-x-full"
          }`}
        >
        <div className="flex h-[76px] items-center gap-3 border-b border-line px-5">
          <Image
            src="/birdwing-logo.svg"
            alt=""
            width={40}
            height={40}
            className="size-10 rounded-lg bg-[#e7eeea] p-1 object-contain"
          />
          <div>
            <div className="font-bold tracking-tight">Birdwing Airlines</div>
            <div className="text-xs text-muted">Knowledge assistant</div>
          </div>
        </div>
        <div className="p-4">
          <button
            onClick={() => {
              startNewChat();
              setSidebarOpen(false);
            }}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-accent px-4 py-3 text-sm font-semibold text-white transition hover:bg-[#194744]"
          >
            <span className="text-lg leading-none">+</span> New conversation
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-3">
          <div className="mb-2 px-2 text-[11px] font-bold uppercase tracking-[.14em] text-muted">
            Recent conversations
          </div>
          {user &&
            (conversations?.items.length ? (
              conversations.items.map((conversation) => (
                <div
                  key={conversation.id}
                  className={`group mb-1 flex items-center gap-1 rounded-xl px-2 ${
                    conversation.id === conversationId
                      ? "bg-panel-2"
                      : "hover:bg-panel-2"
                  }`}
                >
                  <button
                    onClick={() => void selectConversation(conversation.id)}
                    className="min-w-0 flex-1 py-2.5 text-left"
                  >
                    <div className="truncate text-sm font-medium">
                      {conversation.title}
                    </div>
                    <div className="mt-0.5 truncate text-xs text-muted">
                      {conversation.last_message ?? "No messages yet"}
                    </div>
                  </button>
                  <button
                    aria-label={`Delete ${conversation.title}`}
                    title="Delete conversation"
                    onClick={async () => {
                      try {
                        await deleteConversation(conversation.id).unwrap();
                        if (conversation.id === conversationId) startNewChat();
                      } catch {
                        setNotice("Could not delete the conversation.");
                      }
                    }}
                    className="rounded-lg px-2 py-1 text-muted opacity-0 transition hover:bg-white hover:text-danger group-hover:opacity-100 focus:opacity-100"
                  >
                    ×
                  </button>
                </div>
              ))
            ) : (
              <p className="px-2 py-3 text-sm text-muted">
                Your saved conversations will appear here.
              </p>
            ))}
        </div>
        <div className="border-t border-line p-4">
          {user && (
            <>
              {(user.role === "admin" || user.role === "moderator") && (
                <Link
                  href={user.role === "admin" ? "/admin" : "/moderation"}
                  className="mb-3 block rounded-lg px-2 py-2 text-sm font-medium text-muted hover:bg-panel-2 hover:text-fg"
                >
                  {user.role === "admin" ? "Admin dashboard" : "Moderation"}
                </Link>
              )}
              <div className="mb-3 flex items-center gap-3 px-1">
                <div className="grid size-9 place-items-center rounded-full bg-[#e7eeea] text-sm font-bold text-accent">
                  {(user.name ?? user.email).slice(0, 1).toUpperCase()}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-semibold">
                    {user.name ?? user.email}
                  </div>
                  <div className="truncate text-xs capitalize text-muted">
                    {user.role}
                  </div>
                </div>
                <Link
                  href="/google/link"
                  aria-label="Google account settings"
                  title="Google account settings"
                  className="rounded-lg p-2 text-muted hover:bg-panel-2 hover:text-fg"
                >
                  ⚙
                </Link>
              </div>
              <button
                onClick={() => void handleLogout()}
                className="w-full rounded-lg px-2 py-2 text-left text-sm text-muted hover:bg-panel-2 hover:text-fg"
              >
                Sign out
              </button>
            </>
          )}
        </div>
        </aside>
      )}

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-[76px] flex-none items-center justify-between border-b border-line bg-panel px-4 md:px-8">
          <div className="flex items-center gap-3">
            {isWorkspace && (
              <button
                aria-label="Open navigation"
                onClick={() => setSidebarOpen(true)}
                className="grid size-9 place-items-center rounded-lg border border-line text-lg md:hidden"
              >
                ☰
              </button>
            )}
            {!isWorkspace && (
              <Link href="/" className="flex items-center gap-3">
                <Image
                  src="/birdwing-logo.svg"
                  alt=""
                  width={36}
                  height={36}
                  className="size-9 rounded-lg bg-[#e7eeea] p-1 object-contain"
                />
                <span className="font-bold tracking-tight">Birdwing Airlines</span>
              </Link>
            )}
            {isWorkspace && (
              <div>
                <div className="text-sm font-bold">Birdwing assistant</div>
                <div className="flex items-center gap-1.5 text-xs text-muted">
                  <span className="size-1.5 rounded-full bg-emerald-500" />
                  Private workspace
                </div>
              </div>
            )}
          </div>
          {isWorkspace ? (
            <div className="hidden items-center gap-2 text-xs text-muted sm:flex">
              <span className="rounded-full border border-line bg-white px-3 py-1.5">
                Saved to your account
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <span className="hidden rounded-full border border-line bg-white px-3 py-1.5 text-xs text-muted sm:inline-flex">
                Anonymous · not saved
              </span>
              <Link href="/login" className="rounded-lg px-3 py-2 text-sm font-semibold hover:bg-panel-2">Sign in</Link>
              <button
                onClick={startNewChat}
                disabled={!messages.length || streamState.isLoading}
                className="rounded-lg bg-accent px-3 py-2 text-sm font-semibold text-white disabled:hidden"
              >
                New chat
              </button>
            </div>
          )}
        </header>

        <section className="flex flex-1 flex-col overflow-y-auto px-4 py-7 md:px-8">
          <div className="mx-auto flex w-full max-w-[820px] flex-1 flex-col">
            {hasSessionError && (
              <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                Could not verify your saved session. Public chat is still available.
              </div>
            )}
            {messages.length === 0 ? (
              <div className="my-auto py-10">
                {isWorkspace && (
                  <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-line bg-panel px-3 py-1.5 text-xs font-semibold text-accent">
                    <span className="size-1.5 rounded-full bg-accent" />
                    Your Birdwing Airlines assistant
                  </div>
                )}
                <h1 className={`max-w-2xl font-bold leading-[1.13] tracking-[-.04em] ${isWorkspace ? "text-3xl md:text-4xl" : "text-3xl md:text-4xl"}`}>
                  {isWorkspace ? "What would you like to know about Birdwing?" : "Ask Birdwing Airlines."}
                </h1>
                <p className="mt-3 max-w-xl text-sm leading-6 text-muted md:text-base">
                  {isWorkspace
                    ? "Get clear answers grounded in Birdwing Airlines’ knowledge."
                    : "Ask about Birdwing Airlines. This anonymous public chat won’t be saved."}
                </p>
                <div className="mt-6 grid gap-2 sm:grid-cols-2">
                  {[
                    "What is the cabin baggage allowance?",
                    "How can I change or cancel a booking?",
                    "What documents do I need to check in?",
                    "What are Birdwing’s baggage policies?",
                  ].map((suggestion) => (
                    <button
                      key={suggestion}
                      onClick={() => void send(suggestion)}
                      className="motion-hover group flex items-center justify-between rounded-xl border border-line bg-panel px-4 py-3.5 text-left text-sm font-medium hover:border-accent/40 hover:bg-[#f4f1e9]"
                    >
                      {suggestion}
                      <span className="text-lg text-muted transition group-hover:translate-x-0.5 group-hover:text-accent">
                        →
                      </span>
                    </button>
                  ))}
                </div>
                {isWorkspace && (
                  <p className="mt-5 text-xs text-muted">
                    Your conversations are private to your account.
                  </p>
                )}
              </div>
            ) : (
              <div className="space-y-7 pb-5 pt-2">
                {messages.map((message) => (
                  <article
                    key={message.id}
                    className={`group motion-rise flex gap-3 ${
                      message.role === "user" ? "justify-end" : ""
                    }`}
                  >
                    {message.role === "assistant" && (
                      <Image
                        src="/birdwing-logo.svg"
                        alt=""
                        width={36}
                        height={36}
                        className="size-9 flex-none rounded-lg bg-[#e7eeea] p-1 object-contain"
                      />
                    )}
                    <div
                      className={
                        message.role === "user"
                          ? "flex max-w-[82%] flex-col items-end gap-1.5"
                          : "min-w-0 flex-1 pt-1 text-[15px] leading-7"
                      }
                    >
                      {message.role === "user" &&
                      editingMessageId === message.id ? (
                        <div className="w-full max-w-[min(82vw,36rem)] rounded-2xl border border-line bg-panel p-3 shadow-sm">
                          <label
                            htmlFor={`edit-question-${message.id}`}
                            className="mb-2 block text-[11px] font-semibold uppercase tracking-wide text-muted"
                          >
                            Edit your question
                          </label>
                          <textarea
                            id={`edit-question-${message.id}`}
                            autoFocus
                            rows={3}
                            value={editedQuestion}
                            onChange={(event) =>
                              setEditedQuestion(event.target.value)
                            }
                            onKeyDown={(event) => {
                              if (
                                event.key === "Enter" &&
                                !event.shiftKey &&
                                !streamState.isLoading
                              ) {
                                event.preventDefault();
                                void resendEditedQuestion();
                              }
                              if (event.key === "Escape") {
                                setEditingMessageId(null);
                                setEditedQuestion("");
                              }
                            }}
                            className="w-full resize-y rounded-lg border border-line bg-white px-3 py-2 text-sm leading-6 outline-none focus:border-accent focus:ring-2 focus:ring-accent/10"
                          />
                          <p className="mt-1 text-[11px] text-muted">
                            Resending adds this as a new turn; earlier messages stay in the conversation.
                          </p>
                          <div className="mt-2 flex justify-end gap-2">
                            <button
                              type="button"
                              onClick={() => {
                                setEditingMessageId(null);
                                setEditedQuestion("");
                              }}
                              className="rounded-lg px-3 py-2 text-xs font-semibold text-muted hover:bg-panel-2 hover:text-fg"
                            >
                              Cancel
                            </button>
                            <button
                              type="button"
                              disabled={!editedQuestion.trim() || streamState.isLoading}
                              onClick={() => void resendEditedQuestion()}
                              className="rounded-lg bg-accent px-3 py-2 text-xs font-semibold text-white hover:bg-[#194744] disabled:cursor-not-allowed disabled:opacity-50"
                            >
                              {streamState.isLoading ? "Sending…" : "Resend"}
                            </button>
                          </div>
                        </div>
                      ) : message.role === "user" ? (
                        <div className="whitespace-pre-wrap rounded-2xl rounded-br-md bg-[#e7eeea] px-4 py-3 text-left text-sm leading-6 text-[#294744]">
                          {message.content}
                        </div>
                      ) : null}
                      {message.role === "user" &&
                        editingMessageId !== message.id && (
                          <button
                            type="button"
                            disabled={streamState.isLoading}
                            onClick={() => {
                              setEditedQuestion(message.content);
                              setEditingMessageId(message.id);
                            }}
                            className="rounded-md px-2 py-1 text-xs font-medium text-muted opacity-70 transition hover:bg-panel-2 hover:text-accent disabled:cursor-not-allowed disabled:opacity-40 sm:opacity-0 sm:group-hover:opacity-100"
                          >
                            Edit &amp; resend
                          </button>
                        )}
                      {message.role === "assistant" && !message.content && !message.error && streamState.isLoading && (
                        <div className="flex gap-1.5 py-3" aria-label="Assistant is responding">
                          {[0, 140, 280].map((delay) => (
                            <span
                              key={delay}
                              style={{ animationDelay: `${delay}ms` }}
                              className="size-2 animate-bounce rounded-full bg-accent/50"
                            />
                          ))}
                        </div>
                      )}
                      {message.role === "assistant" && message.content && (
                        <div className="prose prose-slate max-w-none [&_a]:text-accent [&_code]:rounded [&_code]:bg-panel-2 [&_code]:px-1 [&_pre]:overflow-x-auto [&_ul]:list-disc">
                          <ReactMarkdown>{message.content}</ReactMarkdown>
                        </div>
                      )}
                      {message.error && (
                        <div className="rounded-xl border border-rose-100 bg-danger-bg px-4 py-3 text-sm text-danger">
                          {message.error}
                        </div>
                      )}
                      {!!message.sources?.length && (
                        <div className="mt-4 border-t border-line pt-3">
                          <div className="mb-2 text-[11px] font-bold uppercase tracking-wider text-muted">
                            Sources
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {message.sources.map((source, index) => (
                              <span
                                key={`${source.source}-${index}`}
                                title={`${source.source} · pages ${source.start_page}–${source.end_page}`}
                                className="rounded-lg border border-line bg-white px-2.5 py-1.5 text-xs font-medium text-muted"
                              >
                                {source.document_name} · p. {source.start_page}
                                {source.end_page !== source.start_page &&
                                  `–${source.end_page}`}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                    {message.role === "user" && (
                      <div className="grid size-9 flex-none place-items-center rounded-full bg-fg text-xs font-bold text-white">
                        {isWorkspace ? (user?.name ?? user?.email ?? "U").slice(0, 1).toUpperCase() : "Y"}
                      </div>
                    )}
                  </article>
                ))}
                <div ref={scrollRef} />
              </div>
            )}
          </div>
        </section>

        <footer className="flex-none border-t border-line bg-white/80 px-4 pb-4 pt-4 md:px-8">
          <div className="mx-auto max-w-[820px]">
            {notice && (
              <div className="mb-3 rounded-xl border border-rose-100 bg-danger-bg px-4 py-2.5 text-sm text-danger">
                {notice}
              </div>
            )}
            <form
              onSubmit={(event) => {
                event.preventDefault();
                void send();
              }}
              className="flex items-end gap-3 rounded-2xl border border-line bg-panel p-2 pl-4 shadow-[0_4px_16px_rgba(42,54,46,.06)] transition focus-within:border-accent/50 focus-within:ring-4 focus-within:ring-accent/10"
            >
              <textarea
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    void send();
                  }
                }}
                placeholder="Ask a question about Birdwing Airlines..."
                aria-label="Your question"
                rows={1}
                className="max-h-36 min-h-11 flex-1 resize-none bg-transparent py-3 text-sm leading-5 outline-none placeholder:text-muted"
              />
              <button
                type="submit"
                disabled={!input.trim() || streamState.isLoading}
                className="mb-0.5 grid size-10 flex-none place-items-center rounded-xl bg-accent text-lg text-white transition hover:bg-[#194744] disabled:cursor-not-allowed disabled:opacity-40"
                aria-label="Send message"
              >
                ↑
              </button>
            </form>
            <p className="mt-2 text-center text-[11px] text-muted">
              {isWorkspace
                ? "Your questions are saved with your account."
                : "Anonymous chat · This conversation is only available in this browser session."}{" "}
              AI answers can make mistakes; check the cited sources.
            </p>
          </div>
        </footer>
      </main>
    </div>
  );
}

function toMessage(message: StoredChatMessage): Message {
  return {
    id: message.id,
    role: message.role,
    content: message.content,
    sources: message.sources ?? undefined,
  };
}
