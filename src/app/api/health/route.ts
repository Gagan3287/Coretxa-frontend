import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    status: "ok",
    service: "cortexa-embedded-engine",
    version: "1.0.0",
    runtime: "nextjs-integrated",
  });
}
