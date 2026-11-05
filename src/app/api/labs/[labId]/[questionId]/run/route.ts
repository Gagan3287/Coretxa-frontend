import { NextResponse } from "next/server";
import { runAlgorithm } from "@/lib/engine/algorithms";

export async function POST(
  request: Request,
  props: { params: Promise<{ labId: string; questionId: string }> | { labId: string; questionId: string } }
) {
  const params = await props.params;
  const { labId, questionId } = params;

  let stdin = "";
  try {
    const body = await request.json();
    if (body && typeof body.stdin === "string") {
      stdin = body.stdin;
    }
  } catch {
    stdin = "";
  }

  const result = runAlgorithm(labId, questionId, stdin);
  return NextResponse.json(result);
}
