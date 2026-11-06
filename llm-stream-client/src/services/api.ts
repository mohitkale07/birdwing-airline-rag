import {
  createApi,
  fetchBaseQuery,
  type FetchBaseQueryError,
} from "@reduxjs/toolkit/query/react";
import { chatStreamEventReceived } from "../features/chatSlice";
import type {
  AdminDashboardMetrics,
  AdminUserListResponse,
  AuthResponse,
  AuthUser,
  ChatRequest,
  ChatStreamEvent,
  ConversationActionResponse,
  ConversationDetailResponse,
  ConversationListResponse,
  ConversationUpdateRequest,
  GoogleAuthStartResponse,
  LoginRequest,
  ModerationDashboardResponse,
  RegisterRequest,
  ResendVerificationEmailRequest,
  UserRestrictionRequest,
  UserRestrictionResponse,
  VerifyEmailRequest,
} from "../schemas/api";

const baseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
const baseQuery = fetchBaseQuery({
  baseUrl,
  credentials: "include",
});

function parseSseChunk(chunk: string): ChatStreamEvent[] {
  return chunk
    .split(/\r?\n\r?\n/)
    .map((block) =>
      block
        .split(/\r?\n/)
        .find((line) => line.startsWith("data:"))
        ?.slice(5)
        .trim(),
    )
    .filter((data): data is string => Boolean(data))
    .map((data) => JSON.parse(data) as ChatStreamEvent);
}

export const api = createApi({
  reducerPath: "api",
  baseQuery,
  tagTypes: ["Auth", "Conversations", "AdminUsers", "AdminMetrics"],
  endpoints: (builder) => ({
    login: builder.mutation<AuthResponse, LoginRequest>({
      query: (body) => ({ url: "/auth/login", method: "POST", body }),
      invalidatesTags: ["Auth"],
    }),
    register: builder.mutation<AuthResponse, RegisterRequest>({
      query: (body) => ({ url: "/auth/register", method: "POST", body }),
    }),
    verifyEmail: builder.mutation<{ message: string }, VerifyEmailRequest>({
      query: (body) => ({ url: "/auth/verify-email", method: "POST", body }),
    }),
    resendVerificationEmail: builder.mutation<
      { message: string },
      ResendVerificationEmailRequest
    >({
      query: (body) => ({
        url: "/auth/resend-verification-email",
        method: "POST",
        body,
      }),
    }),
    getMe: builder.query<AuthUser, void>({
      query: () => "/auth/me",
      providesTags: ["Auth"],
    }),
    logout: builder.mutation<void, void>({
      query: () => ({ url: "/auth/logout", method: "POST" }),
      invalidatesTags: ["Auth"],
    }),
    getGoogleLogin: builder.query<GoogleAuthStartResponse, void>({
      query: () => ({ url: "/auth/google/login", responseHandler: "text" }),
      transformResponse: (response: string) => {
        try {
          return JSON.parse(response) as GoogleAuthStartResponse;
        } catch {
          return { message: response };
        }
      },
    }),
    getGoogleCallback: builder.query<
      AuthResponse,
      { code?: string; state?: string; error?: string }
    >({
      query: (params) => ({ url: "/auth/google/callback", params }),
      providesTags: ["Auth"],
    }),
    linkGoogle: builder.mutation<GoogleAuthStartResponse, void>({
      query: () => ({ url: "/auth/google/link", method: "POST" }),
    }),
    unlinkGoogle: builder.mutation<{ message?: string }, void>({
      query: () => ({ url: "/auth/google/unlink", method: "DELETE" }),
    }),
    getAdminDashboard: builder.query<
      { message: string; user_id: string; role: string },
      void
    >({
      query: () => "/auth/admin/dashboard",
    }),
    getModerationDashboard: builder.query<ModerationDashboardResponse, void>({
      query: () => "/auth/moderation/dashboard",
    }),
    getUsers: builder.query<
      AdminUserListResponse,
      { limit?: number; offset?: number; search?: string }
    >({
      query: ({ limit = 20, offset = 0, search }) => ({
        url: "/admin/users",
        params: { limit, offset, search },
      }),
      providesTags: (result) =>
        result
          ? [
              ...result.items.map((user) => ({
                type: "AdminUsers" as const,
                id: user.id,
              })),
              { type: "AdminUsers" as const, id: "LIST" },
            ]
          : [{ type: "AdminUsers", id: "LIST" }],
    }),
    updateUserRestriction: builder.mutation<
      UserRestrictionResponse,
      { userId: string; payload: UserRestrictionRequest }
    >({
      query: ({ userId, payload }) => ({
        url: `/admin/users/${userId}/restriction`,
        method: "PATCH",
        body: payload,
      }),
      invalidatesTags: (_result, _error, { userId }) => [
        { type: "AdminUsers", id: userId },
        { type: "AdminUsers", id: "LIST" },
        "AdminMetrics",
      ],
    }),
    getAdminMetrics: builder.query<AdminDashboardMetrics, void>({
      query: () => "/admin/metrics",
      providesTags: ["AdminMetrics"],
    }),
    getConversations: builder.query<
      ConversationListResponse,
      { limit?: number; offset?: number; include_archived?: boolean } | void
    >({
      query: (params) => ({ url: "/chat/conversations", params: params ?? {} }),
      providesTags: (result) =>
        result
          ? [
              ...result.items.map((conversation) => ({
                type: "Conversations" as const,
                id: conversation.id,
              })),
              { type: "Conversations" as const, id: "LIST" },
            ]
          : [{ type: "Conversations", id: "LIST" }],
    }),
    getConversation: builder.query<
      ConversationDetailResponse,
      { conversationId: string; limit?: number; offset?: number }
    >({
      query: ({ conversationId, ...params }) => ({
        url: `/chat/conversations/${conversationId}`,
        params,
      }),
      providesTags: (_result, _error, { conversationId }) => [
        { type: "Conversations", id: conversationId },
      ],
    }),
    updateConversation: builder.mutation<
      ConversationActionResponse,
      { conversationId: string; payload: ConversationUpdateRequest }
    >({
      query: ({ conversationId, payload }) => ({
        url: `/chat/conversations/${conversationId}`,
        method: "PATCH",
        body: payload,
      }),
      invalidatesTags: (_result, _error, { conversationId }) => [
        { type: "Conversations", id: conversationId },
        { type: "Conversations", id: "LIST" },
      ],
    }),
    deleteConversation: builder.mutation<void, string>({
      query: (conversationId) => ({
        url: `/chat/conversations/${conversationId}`,
        method: "DELETE",
      }),
      invalidatesTags: (_result, _error, conversationId) => [
        { type: "Conversations", id: conversationId },
        { type: "Conversations", id: "LIST" },
      ],
    }),
    streamChat: builder.mutation<
      { completed: boolean },
      ChatRequest & { requestId: string }
    >({
      async queryFn({ requestId, ...body }, queryApi) {
        try {
          const headers = new Headers({ "Content-Type": "application/json" });
          const response = await fetch(`${baseUrl}/chat/stream`, {
            method: "POST",
            headers,
            credentials: "include",
            body: JSON.stringify(body),
            signal: queryApi.signal,
          });
          if (!response.ok) {
            const detail = await response.text();
            return {
              error: {
                status: response.status,
                data: detail || "The chat request failed.",
              } as FetchBaseQueryError,
            };
          }
          if (!response.body) {
            return {
              error: {
                status: "CUSTOM_ERROR",
                error: "The server returned an empty chat stream.",
              },
            };
          }

          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = "";
          while (true) {
            const { done, value } = await reader.read();
            buffer += decoder.decode(value, { stream: !done });
            const split = buffer.split(/\r?\n\r?\n/);
            buffer = split.pop() ?? "";
            for (const block of split) {
              for (const event of parseSseChunk(`${block}\n\n`)) {
                queryApi.dispatch(
                  chatStreamEventReceived({ requestId, event }),
                );
              }
            }
            if (done) break;
          }
          if (buffer.trim()) {
            for (const event of parseSseChunk(`${buffer}\n\n`)) {
              queryApi.dispatch(chatStreamEventReceived({ requestId, event }));
            }
          }
          return { data: { completed: true } };
        } catch (error) {
          return {
            error: {
              status: "CUSTOM_ERROR",
              error:
                error instanceof Error ? error.message : "Chat stream failed.",
            },
          };
        }
      },
      invalidatesTags: ["Conversations"],
    }),
  }),
});

export const {
  useLoginMutation,
  useRegisterMutation,
  useVerifyEmailMutation,
  useResendVerificationEmailMutation,
  useGetMeQuery,
  useLazyGetMeQuery,
  useLogoutMutation,
  useLazyGetGoogleLoginQuery,
  useLazyGetGoogleCallbackQuery,
  useLinkGoogleMutation,
  useUnlinkGoogleMutation,
  useGetAdminDashboardQuery,
  useGetModerationDashboardQuery,
  useGetUsersQuery,
  useUpdateUserRestrictionMutation,
  useGetAdminMetricsQuery,
  useGetConversationsQuery,
  useLazyGetConversationQuery,
  useUpdateConversationMutation,
  useDeleteConversationMutation,
  useStreamChatMutation,
} = api;
