import { apiClient, ApiError } from "./client";
import type { Bot, BotStatus, CreateBotInput } from "@/types/bot";

interface BackendBotDetail {
  bot_id: string;
  tenant_id: string;
  name: string;
  slug: string;
  branding_json: Record<string, unknown>;
  status: string;
  document_count: number;
  created_at: string;
}

interface BackendBotListResponse {
  bots: BackendBotDetail[];
  total: number;
}

interface BackendBotCreateResponse {
  bot_id: string;
  slug: string;
  name: string;
  status: string;
  widget_key: string;
  created_at: string;
}

function slugify(name: string): string {
  const base = name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 50);
  return base || "bot";
}

function mapBot(b: BackendBotDetail): Bot {
  return {
    id: b.bot_id,
    name: b.name,
    description: (b.branding_json?.description as string) || "",
    status: (b.status === "active" ? "active" : b.status === "processing" ? "processing" : "failed") as BotStatus,
    documentCount: b.document_count ?? 0,
    updatedAt: b.created_at,
  };
}

export async function listBots(): Promise<Bot[]> {
  try {
    const data = await apiClient<BackendBotListResponse>("/api/v1/bots");
    return data.bots.map(mapBot);
  } catch (err: unknown) {
    if (err instanceof ApiError && err.status === 404) {
      return [];
    }
    throw new Error(err instanceof Error ? err.message : "Failed to load bots.");
  }
}

export async function createBot(input: CreateBotInput): Promise<Bot> {
  const name = input.name.trim();
  const description = input.description.trim();
  const slug = slugify(name);

  const payload = {
    name,
    slug,
    branding_json: description ? { description } : {},
  };

  try {
    let res: BackendBotCreateResponse;
    try {
      res = await apiClient<BackendBotCreateResponse>("/api/v1/bots", {
        method: "POST",
        body: payload,
      });
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 409) {
        // Slug collision — retry once with a unique suffix
        const suffix = Math.random().toString(36).slice(2, 6);
        payload.slug = `${slug.slice(0, 55)}-${suffix}`;
        res = await apiClient<BackendBotCreateResponse>("/api/v1/bots", {
          method: "POST",
          body: payload,
        });
      } else {
        throw err;
      }
    }

    return {
      id: res.bot_id,
      name: res.name,
      description,
      status: (res.status === "active" ? "active" : "processing") as BotStatus,
      documentCount: 0,
      updatedAt: res.created_at,
      widgetKey: res.widget_key,
    };
  } catch (err: unknown) {
    throw new Error(err instanceof Error ? err.message : "Failed to create bot.");
  }
}