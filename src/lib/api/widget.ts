import { apiClient } from "./client";
import type { WidgetConfig } from "@/types/widget";

// Backend BotDetail branding_json maps to WidgetConfig fields
interface BackendBotDetail {
  bot_id: string;
  name: string;
  slug: string;
  branding_json: Record<string, unknown>;
  status: string;
  document_count: number;
  created_at: string;
}

function brandingToWidgetConfig(bot: BackendBotDetail): WidgetConfig {
  const b = bot.branding_json || {};
  return {
    botId: bot.bot_id,
    displayName: (b.display_name as string) || bot.name,
    greeting: (b.greeting as string) || `Hi! Ask me anything about ${bot.name}.`,
    color: (b.color as string) || "#4f46e5",
    position: ((b.position as string) === "left" ? "left" : "right") as "left" | "right",
    allowedOrigins: Array.isArray(b.allowed_origins) ? (b.allowed_origins as string[]) : [],
    // widget_key is only available at creation time — stored in session if newly created
    widgetKey: (b.widget_key_display as string) || "",
    hostedUrl: `${process.env.NEXT_PUBLIC_HOSTED_CHAT_URL || "https://chat.cortexa.io"}/b/${bot.bot_id}`,
  };
}

function widgetConfigToBranding(config: WidgetConfig): Record<string, unknown> {
  return {
    display_name: config.displayName,
    greeting: config.greeting,
    color: config.color,
    position: config.position,
    allowed_origins: config.allowedOrigins,
  };
}

export async function getWidgetConfig(bot: { id: string; name: string }): Promise<WidgetConfig> {
  const data = await apiClient<BackendBotDetail>(`/api/v1/bots/${bot.id}`);
  return brandingToWidgetConfig(data);
}

export async function saveWidgetConfig(config: WidgetConfig): Promise<WidgetConfig> {
  const data = await apiClient<BackendBotDetail>(`/api/v1/bots/${config.botId}`, {
    method: "PATCH",
    body: {
      branding_json: widgetConfigToBranding(config),
    },
  });
  return brandingToWidgetConfig(data);
}