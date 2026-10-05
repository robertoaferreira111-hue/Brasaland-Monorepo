import { apiRequest } from "@/lib/httpClient";
import type { Note, NoteCreatePayload, NotesListEnvelope } from "@/types/api";

/** GET /records/:id/notes — returns plain note array. */
export async function listNotes(recordId: string): Promise<Note[]> {
  const envelope = await apiRequest<NotesListEnvelope>(
    `/records/${recordId}/notes`,
  );
  return envelope.data;
}

/** POST /records/:id/notes */
export async function addNote(
  recordId: string,
  payload: NoteCreatePayload,
): Promise<Note> {
  return apiRequest<Note>(`/records/${recordId}/notes`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/** DELETE /records/:id/notes/:note_id */
export async function deleteNote(
  recordId: string,
  noteId: string,
): Promise<void> {
  await apiRequest<void>(`/records/${recordId}/notes/${noteId}`, {
    method: "DELETE",
  });
}
