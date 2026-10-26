export type BotStatus = "active" | "processing" | "failed";

export interface Bot {
  id: string;
  name: string;
  description: string;
  status: BotStatus;
  documentCount: number;
  updatedAt: string;
}

export interface CreateBotInput {
  name: string;
  description: string;
}