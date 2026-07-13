import { clearToken, getToken } from "./auth";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !(options.body instanceof URLSearchParams)) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  } catch {
    throw new ApiError(0, "Impossible de contacter le serveur. Vérifiez votre connexion.");
  }

  if (response.status === 401) {
    clearToken();
    if (typeof window !== "undefined" && window.location.pathname !== "/login") {
      window.location.href = "/login";
    }
    throw new ApiError(401, "Session expirée, merci de vous reconnecter.");
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    const detail = Array.isArray(body.detail)
      ? body.detail.map((d: { msg?: string }) => d.msg).join(", ")
      : body.detail;
    throw new ApiError(response.status, detail || "Une erreur est survenue.");
  }

  if (response.status === 204) return undefined as T;
  return response.json();
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface CurrentUser {
  id: number;
  email: string;
  slack_webhook_url: string | null;
  created_at: string;
}

export interface ProductConfig {
  type: "price";
  url: string;
  css_selector: string;
  currency: string;
  stock_selector?: string | null;
  promo_selector?: string | null;
}

export interface Product {
  id: number;
  watcher_type: "price" | "trend" | "eurostat";
  name: string;
  config: ProductConfig | Record<string, unknown>;
  is_active: boolean;
  schedule: string;
  alert_price_drop_pct: number | null;
  alert_on_stock_out: boolean;
  alert_on_promo: boolean;
  created_at: string;
  updated_at: string;
  latest_gold_timeseries_key: string | null;
  latest_gold_summary_key: string | null;
}

export interface ProductSummary {
  latest_timestamp?: string;
  latest_value?: number;
  previous_value?: number | null;
  delta?: number | null;
  currency?: string;
  in_stock?: boolean | null;
  stock_text?: string | null;
  original_value?: number | null;
  is_promo?: boolean;
  discount_pct?: number | null;
}

export interface PricePoint {
  timestamp: string;
  value: number;
  currency?: string;
  in_stock?: boolean | null;
  is_promo?: boolean;
}

export interface Run {
  id: number;
  watcher_id: number;
  run_ts: string;
  status: string;
  error_message: string | null;
  records_count: number | null;
  gold_key: string | null;
  created_at: string;
}

export interface AlertEvent {
  id: number;
  watcher_id: number;
  alert_type: "price_drop" | "stock_out" | "promo";
  channel: "email" | "slack";
  message: string;
  sent_at: string;
}

export interface Digest {
  id: number;
  content: string;
  generated_at: string;
}

export interface CreateProductInput {
  name: string;
  url: string;
  cssSelector: string;
  currency: string;
  schedule: string;
  stockSelector?: string;
  promoSelector?: string;
  alertPriceDropPct?: number;
  alertOnStockOut: boolean;
  alertOnPromo: boolean;
}

export const api = {
  signup: (email: string, password: string) =>
    request<TokenResponse>("/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  login: (email: string, password: string) => {
    const body = new URLSearchParams({ username: email, password });
    return request<TokenResponse>("/auth/login", { method: "POST", body });
  },

  me: () => request<CurrentUser>("/auth/me"),

  updateSettings: (slackWebhookUrl: string) =>
    request<CurrentUser>("/auth/me", {
      method: "PATCH",
      body: JSON.stringify({ slack_webhook_url: slackWebhookUrl || null }),
    }),

  listProducts: () => request<Product[]>("/watchers"),

  getProduct: (id: number) => request<Product>(`/watchers/${id}`),

  createProduct: (input: CreateProductInput) =>
    request<Product>("/watchers", {
      method: "POST",
      body: JSON.stringify({
        watcher_type: "price",
        name: input.name,
        schedule: input.schedule,
        alert_price_drop_pct: input.alertPriceDropPct || null,
        alert_on_stock_out: input.alertOnStockOut,
        alert_on_promo: input.alertOnPromo,
        config: {
          type: "price",
          url: input.url,
          css_selector: input.cssSelector,
          currency: input.currency,
          stock_selector: input.stockSelector || null,
          promo_selector: input.promoSelector || null,
        },
      }),
    }),

  deleteProduct: (id: number) => request<void>(`/watchers/${id}`, { method: "DELETE" }),

  getProductHistory: (id: number) => request<PricePoint[]>(`/watchers/${id}/timeseries`),

  getProductSummary: (id: number) => request<ProductSummary[]>(`/watchers/${id}/summary`),

  listRuns: (productId?: number) =>
    request<Run[]>(`/runs${productId ? `?watcher_id=${productId}` : ""}`),

  listAlerts: (productId: number) => request<AlertEvent[]>(`/watchers/${productId}/alerts`),

  listDigests: () => request<Digest[]>("/digests"),

  generateDigestNow: () => request<Digest>("/digests/generate", { method: "POST" }),
};
