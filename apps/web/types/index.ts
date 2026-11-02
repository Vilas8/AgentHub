export interface User {
  id: string;
  email: string;
  full_name: string;
  role: "guest" | "customer" | "business" | "creator" | "admin" | "super_admin";
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface Agent {
  id: string;
  name: string;
  slug: string;
  description: string;
  short_description?: string;
  icon?: string;
  tags?: string[];
  status: "draft" | "pending_review" | "approved" | "rejected" | "suspended" | "archived";
  visibility: "public" | "unlisted" | "private";
  pricing_type: "free" | "subscription" | "per_execution";
  price_per_execution: number;
  total_executions: number;
  average_rating: number;
  review_count: number;
  is_platform_owned: boolean;
  creator_id: string;
  category_id?: string;
}

export interface Category {
  id: string;
  name: string;
  slug: string;
  description?: string;
  icon?: string;
}

export interface Execution {
  id: string;
  user_id: string;
  agent_id: string;
  agent_version_id?: string;
  status: "queued" | "initializing" | "running" | "awaiting_approval" | "completed" | "failed" | "cancelled" | "timed_out";
  input_data?: Record<string, unknown>;
  output_data?: Record<string, unknown>;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
  duration_seconds?: number;
  input_tokens: number;
  output_tokens: number;
  total_cost_minor: number;
  model_provider?: string;
  model_name?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}
