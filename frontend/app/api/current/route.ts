import { NextResponse } from "next/server";

import { fetchCurrent } from "@/lib/hopsworks";

export async function GET() {
  const data = await fetchCurrent();
  return NextResponse.json(data);
}
