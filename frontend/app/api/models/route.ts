import { NextResponse } from "next/server";

import { fetchRegistrySummary } from "@/lib/db";

export async function GET() {
  const data = await fetchRegistrySummary();
  return NextResponse.json(data);
}
