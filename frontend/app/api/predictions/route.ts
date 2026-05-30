import { NextResponse } from "next/server";

import { fetchPredictions } from "@/lib/hopsworks";

export async function GET() {
  const data = await fetchPredictions();
  return NextResponse.json(data);
}
