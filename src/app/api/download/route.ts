import { NextResponse } from "next/server";

export async function GET() {
  // Direct asset download link - triggers instant download in the browser without leaving the page
  const directDownloadUrl =
    "https://github.com/Gagan3287/Coretxa-frontend/releases/download/v1.0.0/Cortexa.Setup.1.0.0.exe";

  return NextResponse.redirect(directDownloadUrl, {
    status: 302,
    headers: {
      "Content-Disposition": 'attachment; filename="Cortexa-Setup-1.0.0.exe"',
    },
  });
}
