import { NextResponse } from "next/server";

import { fetchPredictions } from "@/lib/db";

export async function GET() {
  const data = await fetchPredictions();
  return NextResponse.json(data);
}
