import defaultLabs from "@/lib/data/labs.json";

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

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000").replace(/\/$/, "");

export function getApiBaseUrl(): string {
  return API_BASE;
}

export async function fetchLabs(): Promise<Lab[]> {
  try {
    const res = await fetch(`${API_BASE}/api/labs`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    const data = await res.json();
    return Array.isArray(data) && data.length > 0 ? (data as Lab[]) : (defaultLabs as Lab[]);
  } catch {
    // Graceful offline/Vercel fallback
    return defaultLabs as Lab[];
  }
}

export async function fetchQuestionSource(labId: string, questionId: string): Promise<string> {
  try {
    const res = await fetch(`${API_BASE}/api/labs/${labId}/${questionId}/source`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    const data = await res.json();
    return data.source || "// Source file empty";
  } catch {
    return `// Source code available when connected to the local/docker Cortexa execution backend at ${API_BASE}.\n// Run 'npm start' inside the backend folder or 'docker compose up' to execute with real gcc.`;
  }
}

export async function executeCode(labId: string, questionId: string, stdin: string): Promise<RunResult> {
  try {
    const res = await fetch(`${API_BASE}/api/labs/${labId}/${questionId}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ stdin }),
    });

    if (!res.ok) {
      const text = await res.text();
      return {
        success: false,
        stage: "run",
        stderr: `Server returned status ${res.status}: ${text || "Execution failed"}`,
      };
    }

    const data: RunResult = await res.json();
    return data;
  } catch (err: unknown) {
    return {
      success: false,
      stage: "run",
      stderr:
        err instanceof Error
          ? `Could not reach Cortexa execution backend at ${API_BASE}.\nPlease ensure the backend is running (port 5000).\nDetails: ${err.message}`
          : "Backend connection error.",
    };
  }
}
