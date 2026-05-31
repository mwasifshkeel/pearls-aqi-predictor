import { NextResponse } from "next/server";

import { fetchModelMetrics } from "@/lib/hopsworks";

export async function GET() {
  const data = await fetchModelMetrics();
  return NextResponse.json(data);
}
