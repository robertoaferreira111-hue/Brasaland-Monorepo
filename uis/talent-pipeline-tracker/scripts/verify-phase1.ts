/**
 * Phase 1 live verification for services (run with: npx tsx scripts/verify-phase1.ts)
 * Creates a clearly marked test record, exercises writes, then deletes it.
 */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { ApiError } from "../types/api";
import {
  createCandidate,
  getCandidate,
  listCandidates,
  patchCandidate,
  updateCandidate,
} from "../services/records";
import { addNote, deleteNote, listNotes } from "../services/notes";
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
  const log: string[] = [];

  const listed = await listCandidates({ limit: 5, page: 1 });
  log.push(
    `listCandidates: total=${listed.total} page=${listed.page} items=${listed.items.length}`,
  );

  const filtered = await listCandidates({
    status: "received",
    stage: "pending",
    limit: 3,
  });
  log.push(
    `listCandidates filtered: total=${filtered.total} statuses=${[
      ...new Set(filtered.items.map((i) => i.status)),
    ].join(",")} stages=${[...new Set(filtered.items.map((i) => i.stage))].join(",")}`,
  );

  const searched = await listCandidates({ search: "michael", limit: 5 });
  log.push(
    `listCandidates search: total=${searched.total} names=${searched.items
      .map((i) => i.full_name)
      .join(" | ")}`,
  );

  const sampleId = listed.items[0]?.id;
  if (!sampleId) throw new Error("No candidates available to read");
  const one = await getCandidate(sampleId);
  log.push(`getCandidate: id=${one.id} name=${one.full_name}`);

  const existingNotes = await listNotes(sampleId);
  log.push(`listNotes: count=${existingNotes.length}`);

  try {
    await getCandidate("00000000-0000-0000-0000-000000000000");
    log.push("getCandidate 404: UNEXPECTED success");
  } catch (err) {
    if (err instanceof ApiError) {
      log.push(
        `getCandidate 404: status=${err.status} message=${err.message}`,
      );
    } else {
      throw err;
    }
  }

  const marker = `[PHASE1-TEST] Brasaland cleanup ${Date.now()}`;
  const created = await createCandidate({
    full_name: marker,
    email: `phase1.test.${Date.now()}@brasaland.example`,
    phone: "+57 300 000 0000",
    position: "Executive Assistant",
    experience_years: 1,
    linkedin_url: null,
    cv_url: null,
  });
  log.push(`createCandidate: id=${created.id}`);

  const updated = await updateCandidate(created.id, {
    full_name: marker,
    email: created.email,
    phone: "+57 300 000 0001",
    position: "Executive Assistant",
    experience_years: 2,
    linkedin_url: null,
    cv_url: null,
  });
  log.push(`updateCandidate: experience_years=${updated.experience_years}`);

  const patched = await patchCandidate(created.id, {
    status: "in_progress",
    stage: "review",
  });
  log.push(`patchCandidate: status=${patched.status} stage=${patched.stage}`);

  const note = await addNote(created.id, {
    content: "[PHASE1-TEST] temporary note — delete me",
  });
  log.push(`addNote: id=${note.id}`);

  await deleteNote(created.id, note.id);
  const notesAfter = await listNotes(created.id);
  log.push(
    `deleteNote: remaining=${notesAfter.filter((n) => n.id === note.id).length}`,
  );

  await apiRequest<void>(`/records/${created.id}`, { method: "DELETE" });
  try {
    await getCandidate(created.id);
    log.push("cleanup DELETE: UNEXPECTED still found");
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      log.push("cleanup DELETE: record removed (404)");
    } else {
      throw err;
    }
  }

  for (const line of log) console.log(line);
  console.log("PHASE1_VERIFY_OK");
}

main().catch((err) => {
  console.error("PHASE1_VERIFY_FAIL", err);
  process.exit(1);
});
