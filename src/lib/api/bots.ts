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

const DEMO_STORAGE_KEY = "cortexa_demo_bots";

const DEFAULT_DEMO_BOTS: Bot[] = [
  {
    id: "bot-demo-1",
    name: "Customer Support AI",
    description: "Resolves customer queries 24/7 with instant knowledge-base answers.",
    status: "active",
    documentCount: 12,
    updatedAt: new Date(Date.now() - 3600000 * 4).toISOString(),
    avatar: "neural-core",
    widgetKey: "cx_live_support_98a72b1e",
  },
  {
    id: "bot-demo-2",
    name: "HR & Policy Navigator",
    description: "Guides employees through leaves, health benefits, and company policies.",
    status: "active",
    documentCount: 8,
    updatedAt: new Date(Date.now() - 3600000 * 24).toISOString(),
    avatar: "cyber-shield",
    widgetKey: "cx_live_hr_4f92c10b",
  },
  {
    id: "bot-demo-3",
    name: "Developer Documentation Bot",
    description: "Interactive API reference and SDK code assistant trained on developer markdown files.",
    status: "processing",
    documentCount: 5,
    updatedAt: new Date(Date.now() - 3600000 * 48).toISOString(),
    avatar: "code-sentinel",
    widgetKey: "cx_live_dev_8820c71a",
  },
];

function getLocalDemoBots(): Bot[] {
  if (typeof window === "undefined") return DEFAULT_DEMO_BOTS;
  try {
    const raw = localStorage.getItem(DEMO_STORAGE_KEY);
    if (!raw) {
      localStorage.setItem(DEMO_STORAGE_KEY, JSON.stringify(DEFAULT_DEMO_BOTS));
      return DEFAULT_DEMO_BOTS;
    }
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) && parsed.length > 0 ? parsed : DEFAULT_DEMO_BOTS;
  } catch {
    return DEFAULT_DEMO_BOTS;
  }
}

function saveLocalDemoBot(bot: Bot) {
  if (typeof window === "undefined") return;
  try {
    const bots = getLocalDemoBots();
    const updated = [bot, ...bots];
    localStorage.setItem(DEMO_STORAGE_KEY, JSON.stringify(updated));
  } catch {}
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
    avatar: (b.branding_json?.avatar as string) || "neural-core",
  };
}

export async function listBots(): Promise<Bot[]> {
  try {
    const data = await apiClient<BackendBotListResponse>("/api/v1/bots");
    return data.bots.map(mapBot);
  } catch {
    // Seamless fallback to demo bots for live Vercel showcase
    return getLocalDemoBots();
  }
}

export async function createBot(input: CreateBotInput): Promise<Bot> {
  const name = input.name.trim();
  const description = input.description.trim();
  const avatar = input.avatar || "neural-core";
  const slug = slugify(name);

  const payload = {
    name,
    slug,
    branding_json: {
      description,
      avatar,
    },
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

    const createdBot: Bot = {
      id: res.bot_id,
      name: res.name,
      description,
      status: (res.status === "active" ? "active" : "processing") as BotStatus,
      documentCount: 0,
      updatedAt: res.created_at,
      widgetKey: res.widget_key,
      avatar,
    };
    saveLocalDemoBot(createdBot);
    return createdBot;
  } catch {
    // If backend is not reached yet (pre-Render deployment), create demo bot instantly
    const demoBot: Bot = {
      id: `bot-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      name,
      description,
      status: "active",
      documentCount: 0,
      updatedAt: new Date().toISOString(),
      widgetKey: `cx_live_${Math.random().toString(36).slice(2, 10)}`,
      avatar,
    };
    saveLocalDemoBot(demoBot);
    return demoBot;
  }
}
