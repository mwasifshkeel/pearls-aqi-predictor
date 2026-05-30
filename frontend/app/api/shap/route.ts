import { NextResponse } from "next/server";

import { fetchShapSummary } from "@/lib/hopsworks";

export async function GET() {
  const data = await fetchShapSummary();
  return NextResponse.json(data);
}
