/**
 * Phase 3: create a marked test candidate, PATCH status/stage via services, then delete.
 */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { ApiError } from "../types/api";
import {
  createCandidate,
  getCandidate,
  patchCandidate,
} from "../services/records";
import { apiRequest } from "../lib/httpClient";

function loadEnvLocal() {
  try {
    const raw = readFileSync(resolve(__dirname, "../.env.local"), "utf8");
    for (const line of raw.split("\n")) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#")) continue;
      const idx = trimmed.indexOf("=");
      if (idx === -1) continue;
      const key = trimmed.slice(0, idx);
      const value = trimmed.slice(idx + 1);
      if (!process.env[key]) process.env[key] = value;
    }
  } catch {
    // rely on process env
  }
}

async function main() {
  loadEnvLocal();
  const marker = `[PHASE3-TEST] Brasaland cleanup ${Date.now()}`;
  const created = await createCandidate({
    full_name: marker,
    email: `phase3.test.${Date.now()}@brasaland.example`,
    phone: "+57 300 000 0003",
    position: "Executive Assistant",
    experience_years: 3,
  });
  console.log("created", created.id, created.status, created.stage);

  const patchedStatus = await patchCandidate(created.id, {
    status: "selected",
  });
  console.log("patched status", patchedStatus.status);

  const patchedStage = await patchCandidate(created.id, {
    stage: "offer_presented",
  });
  console.log("patched stage", patchedStage.stage);

  const again = await getCandidate(created.id);
  console.log("reread", again.status, again.stage, again.full_name);

  await apiRequest(`/records/${created.id}`, { method: "DELETE" });
  try {
    await getCandidate(created.id);
    console.log("cleanup FAILED still present");
    process.exit(1);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      console.log("cleanup ok 404");
    } else {
      throw err;
    }
  }
  console.log("PHASE3_VERIFY_OK");
}

main().catch((err) => {
  console.error("PHASE3_VERIFY_FAIL", err);
  process.exit(1);
});
