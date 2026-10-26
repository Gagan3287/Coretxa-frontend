import type { Bot, CreateBotInput } from "@/types/bot";

// MOCK DATA: replace with real API calls once the backend endpoints are connected.
const hoursAgo = (h: number) => new Date(Date.now() - h * 3600_000).toISOString();

let bots: Bot[] = [
  { id: "b1", name: "Customer Support", description: "Answers product and billing questions from your help center.", status: "active", documentCount: 12, updatedAt: hoursAgo(3) },
  { id: "b2", name: "HR Policy", description: "Helps employees find leave, benefits and policy answers.", status: "active", documentCount: 8, updatedAt: hoursAgo(26) },
  { id: "b3", name: "Product Docs", description: "Technical documentation assistant for developers.", status: "processing", documentCount: 4, updatedAt: hoursAgo(1) },
];

const delay = (ms = 600) => new Promise((resolve) => setTimeout(resolve, ms));

export async function listBots(): Promise<Bot[]> {
  await delay();
  return [...bots];
}

export async function createBot(input: CreateBotInput): Promise<Bot> {
  await delay(500);
  const name = input.name.trim();
  if (bots.some((b) => b.name.toLowerCase() === name.toLowerCase())) {
    throw new Error("A bot with this name already exists.");
  }
  const bot: Bot = {
    id: `b${Date.now()}`,
    name,
    description: input.description.trim(),
    status: "processing",
    documentCount: 0,
    updatedAt: new Date().toISOString(),
  };
  bots = [bot, ...bots];
  return bot;
}