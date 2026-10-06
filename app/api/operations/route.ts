import { NextResponse } from "next/server";
import { z } from "zod";
import { getOperationsStore } from "@/lib/operations/store";
import { operationsConfig } from "@/lib/operations/features";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const actionSchema = z.object({
  action: z.literal("run-synthetic-vertical-slice"),
});

function errorResponse(error: unknown) {
  const message = error instanceof Error ? error.message : "operations request failed";
  const status =
    message === "operations module disabled" || message.includes("blocked") ? 503 :
    message === "authentication required" ? 401 :
    message === "forbidden" || message.includes("tenant isolation") ? 403 :
    400;
  return NextResponse.json(
    {
      ok: false,
      error: message,
      mode: operationsConfig.mode,
      synthetic: operationsConfig.mode === "mock",
    },
    { status },
  );
}

export async function GET() {
  return NextResponse.json({
    ok: operationsConfig.enabled && operationsConfig.mode !== "blocked",
    mode: operationsConfig.mode,
    featureFlags: operationsConfig.features,
    sensitiveModulesDefaultOff:
      !operationsConfig.features.voice &&
      !operationsConfig.features.dispatch &&
      !operationsConfig.features.forensicAnalysis &&
      !operationsConfig.features.lpr &&
      !operationsConfig.features.biometricVerification,
  });
}

export async function POST(request: Request) {
  try {
    const input = actionSchema.parse(await request.json());
    if (input.action !== "run-synthetic-vertical-slice") throw new Error("unsupported action");
    if (operationsConfig.mode !== "mock") {
      throw new Error("operations module blocked from live execution until authenticated identity and durable persistence adapters are configured");
    }
    return NextResponse.json({ ok: true, ...(await getOperationsStore().runSyntheticVerticalSlice()) });
  } catch (error) {
    return errorResponse(error);
  }
}
