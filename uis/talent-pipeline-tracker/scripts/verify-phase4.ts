/**
 * Phase 4 verification with marked test records (create, PUT completeness, notes, cleanup).
 */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { ApiError } from "../types/api";
import {
  createCandidate,
  getCandidate,
  updateCandidate,
} from "../services/records";
import { addNote, deleteNote, listNotes } from "../services/notes";
import { apiRequest } from "../lib/httpClient";
import { validateCandidateForm } from "../lib/validation";

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

  const clientErrors = validateCandidateForm({
    full_name: "",
    email: "bad",
    phone: "",
    position: "",
    experience_years: Number.NaN,
  });
  console.log("client validation keys", Object.keys(clientErrors).sort());

  const marker = `[PHASE4-TEST] Brasaland cleanup ${Date.now()}`;
  const created = await createCandidate({
    full_name: marker,
    email: `phase4.test.${Date.now()}@brasaland.example`,
    phone: "+57 300 000 0004",
    position: "Executive Assistant",
    experience_years: 4,
    linkedin_url: "https://linkedin.com/in/phase4-test",
    cv_url: "https://example.com/phase4-cv.pdf",
  });
  console.log("created", created.id);

  const before = await getCandidate(created.id);
  const updated = await updateCandidate(created.id, {
    full_name: before.full_name,
    email: before.email,
    phone: "+57 300 000 0099",
    position: before.position,
    experience_years: before.experience_years,
    linkedin_url: before.linkedin_url,
    cv_url: before.cv_url,
  });
  const after = await getCandidate(created.id);
  console.log("put phone", before.phone, "->", after.phone);
  console.log(
    "put preserved linkedin",
    after.linkedin_url === before.linkedin_url,
    "cv",
    after.cv_url === before.cv_url,
    "name",
    after.full_name === before.full_name,
  );
  console.log("update response phone", updated.phone);

  const note = await addNote(created.id, {
    content: "[PHASE4-TEST] temporary note",
  });
  const notes = await listNotes(created.id);
  console.log(
    "notes count",
    notes.length,
    "order",
    notes.map((n) => n.created_at),
  );
  await deleteNote(created.id, note.id);
  console.log("notes after delete", (await listNotes(created.id)).length);

  await apiRequest(`/records/${created.id}`, { method: "DELETE" });
  try {
    await getCandidate(created.id);
    throw new Error("cleanup failed");
  } catch (err) {
    if (!(err instanceof ApiError) || err.status !== 404) throw err;
    console.log("cleanup ok");
  }
  console.log("PHASE4_VERIFY_OK");
}

main().catch((err) => {
  console.error("PHASE4_VERIFY_FAIL", err);
  process.exit(1);
});
