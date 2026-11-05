import { NextResponse } from "next/server";
import { C_SOURCES } from "@/lib/data/sources";

export async function GET(
  _request: Request,
  props: { params: Promise<{ labId: string; questionId: string }> | { labId: string; questionId: string } }
) {
  const params = await props.params;
  const { labId, questionId } = params;
  const key = `${labId}/${questionId}`;

  const source = C_SOURCES[key];
  if (!source) {
    return NextResponse.json({ error: "Source code not found for question" }, { status: 404 });
  }

  return NextResponse.json({ source });
}
