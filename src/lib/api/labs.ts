import defaultLabs from "@/lib/data/labs.json";
import { C_SOURCES } from "@/lib/data/sources";
import { runAlgorithm } from "@/lib/engine/algorithms";

export interface InputFieldSchema {
  name: string;
  label: string;
  type: "integer" | "integer-array" | "string" | "pair-list";
  default: any;
  label1?: string;
  label2?: string;
}

export interface Question {
  id: string;
  file: string;
  title: string;
  algorithm: string;
  description: string;
  input: string;
  expectedOutput: string;
  inputSchema: InputFieldSchema[];
}

export interface Lab {
  id: string;
  title: string;
  date: string;
  topic: string;
  questions: Question[];
}

export interface RunResult {
  success: boolean;
  stage?: "compile" | "run";
  stdout?: string;
  stderr?: string;
  exitCode?: number;
  durationMs?: number;
}

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");

export function getApiBaseUrl(): string {
  return API_BASE || "Integrated Engine (Vercel Serverless / Native)";
}

export async function fetchLabs(): Promise<Lab[]> {
  try {
    const url = API_BASE ? `${API_BASE}/api/labs` : "/api/labs";
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    const data = await res.json();
    return Array.isArray(data) && data.length > 0 ? (data as Lab[]) : (defaultLabs as Lab[]);
  } catch {
    return defaultLabs as Lab[];
  }
}

export async function fetchQuestionSource(labId: string, questionId: string): Promise<string> {
  const key = `${labId}/${questionId}`;
  if (C_SOURCES[key]) {
    return C_SOURCES[key];
  }

  try {
    const url = API_BASE ? `${API_BASE}/api/labs/${labId}/${questionId}/source` : `/api/labs/${labId}/${questionId}/source`;
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    const data = await res.json();
    return data.source || "// Source file empty";
  } catch {
    return C_SOURCES[key] || "// Source code not found";
  }
}

export async function executeCode(labId: string, questionId: string, stdin: string): Promise<RunResult> {
  try {
    const url = API_BASE ? `${API_BASE}/api/labs/${labId}/${questionId}/run` : `/api/labs/${labId}/${questionId}/run`;
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ stdin }),
    });

    if (res.ok) {
      const data: RunResult = await res.json();
      return data;
    }
  } catch {
    // If external call fails, seamlessly fall back to embedded runner
  }

  return runAlgorithm(labId, questionId, stdin);
}
