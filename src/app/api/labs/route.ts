import { NextResponse } from "next/server";
import defaultLabs from "@/lib/data/labs.json";

export async function GET() {
  return NextResponse.json(defaultLabs);
}
