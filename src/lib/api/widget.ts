import type { WidgetConfig } from "@/types/widget";

// MOCK DATA: replace with real API calls once the backend endpoints exist.
const store = new Map<string, WidgetConfig>();
const delay = (ms = 500) => new Promise((resolve) => setTimeout(resolve, ms));

const clone = (c: WidgetConfig): WidgetConfig => ({ ...c, allowedOrigins: [...c.allowedOrigins] });

export async function getWidgetConfig(bot: { id: string; name: string }): Promise<WidgetConfig> {
  await delay(400);
  let config = store.get(bot.id);
  if (!config) {
    config = {
      botId: bot.id,
      displayName: bot.name,
      greeting: `Hi! Ask me anything about ${bot.name}.`,
      color: "#4f46e5",
      position: "right",
      allowedOrigins: [],
      widgetKey: `pk_mock_${bot.id}`,
      hostedUrl: `https://chat.cortexa.example/b/${bot.id}`,
    };
    store.set(bot.id, config);
  }
  return clone(config);
}

export async function saveWidgetConfig(config: WidgetConfig): Promise<WidgetConfig> {
  await delay(500);
  store.set(config.botId, clone(config));
  return clone(config);
}