export type UserRole = "admin" | "employee" | "moderator" | string;

export interface AuthUser {
  id: string;
  name: string | null;
  email: string;
  role: UserRole;
  is_verified: boolean;
}

export interface AuthResponse {
  message?: string;
}

export interface RegisterRequest {
  name: string;
  email: string;
  password: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface VerifyEmailRequest {
  token: string;
}

export interface ResendVerificationEmailRequest {
  email: string;
}

export interface AdminUserSummary {
  id: string;
  name: string | null;
  email: string;
  role: string;
  is_verified: boolean;
  is_active: boolean;
  is_restricted: boolean;
  created_at: string;
  conversation_count: number;
  message_count: number;
}

export interface AdminUserListResponse {
  items: AdminUserSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface UserRestrictionRequest {
  is_restricted: boolean;
}

export interface UserRestrictionResponse {
  user_id: string;
  is_restricted: boolean;
}

export interface AdminDashboardMetrics {
  total_users: number;
  active_users: number;
  restricted_users: number;
  total_conversations: number;
  total_messages: number;
}

export interface ChatRequest {
  conversation_id?: string | null;
  text: string;
}

export interface ChatSource {
  document_name: string;
  source: string;
  start_page: number;
  end_page: number;
}

export type ChatStreamEvent =
  | { type: "start"; conversation_id: string | null; user_message_id: string | null }
  | { type: "token"; content: string }
  | {
      type: "done";
      conversation_id: string | null;
      user_message_id: string | null;
      assistant_message_id: string | null;
      sources: ChatSource[];
    }
  | { type: "error"; message: string };

export interface ConversationSummary {
  id: string;
  title: string;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  message_count: number;
  last_message: string | null;
}

export interface ConversationListResponse {
  items: ConversationSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface StoredChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: ChatSource[] | null;
  created_at: string;
}

export interface ConversationDetailResponse {
  id: string;
  title: string;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  messages: StoredChatMessage[];
  total_messages: number;
  limit: number;
  offset: number;
}

export interface ConversationUpdateRequest {
  title?: string | null;
  is_archived?: boolean | null;
}

export interface ConversationActionResponse {
  id: string;
  title: string;
  is_archived: boolean;
  updated_at: string;
}

export interface GoogleAuthStartResponse {
  url?: string;
  authorization_url?: string;
  message?: string;
}

export interface ModerationDashboardResponse {
  message: string;
  role: string;
}
