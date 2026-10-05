"use client";

import { FormEvent, useState } from "react";
import { FeedbackBanner } from "@/components/FeedbackBanner";
import { useNotes } from "@/hooks/useNotes";

export function NotesPanel({ recordId }: { recordId: string }) {
  const {
    notes,
    status,
    error,
    mutationStatus,
    mutationError,
    mutationSuccess,
    addNote,
    removeNote,
  } = useNotes(recordId);
  const [content, setContent] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLocalError(null);
    if (!content.trim()) {
      setLocalError("Note content is required.");
      return;
    }
    const ok = await addNote(content.trim());
    if (ok) setContent("");
  }

  return (
    <section className="grid gap-3 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
      <div>
        <h2 className="text-lg font-semibold text-[var(--ink)]">
          Internal notes
        </h2>
        <p className="text-sm text-[var(--muted)]">
          Private notes after calls and interviews.
        </p>
      </div>

      {status === "loading" && (
        <FeedbackBanner tone="info" message="Loading notes…" />
      )}
      {status === "error" && error && (
        <FeedbackBanner tone="error" message={error} />
      )}
      {mutationStatus === "loading" && (
        <FeedbackBanner tone="info" message="Updating notes…" />
      )}
      {mutationError && <FeedbackBanner tone="error" message={mutationError} />}
      {mutationSuccess && (
        <FeedbackBanner tone="success" message={mutationSuccess} />
      )}
      {localError && <FeedbackBanner tone="error" message={localError} />}

      <form onSubmit={handleSubmit} className="grid gap-2">
        <label className="grid gap-1 text-sm">
          <span className="font-medium text-[var(--ink)]">Add note</span>
          <textarea
            value={content}
            onChange={(event) => setContent(event.target.value)}
            rows={3}
            className="rounded-md border border-[var(--border)] bg-white px-3 py-2 text-[var(--ink)] outline-none ring-[var(--accent)] focus:ring-2"
            placeholder="Summary of the latest conversation…"
          />
        </label>
        <button
          type="submit"
          disabled={mutationStatus === "loading"}
          className="w-fit rounded-md bg-[var(--accent)] px-3 py-2 text-sm font-semibold text-white transition hover:bg-[var(--accent-strong)] disabled:opacity-60"
        >
          Add note
        </button>
      </form>

      {status === "success" && notes.length === 0 && (
        <p className="text-sm text-[var(--muted)]">No notes yet.</p>
      )}

      <ul className="grid gap-3">
        {notes.map((note) => (
          <li
            key={note.id}
            className="rounded-md border border-[var(--border)] bg-[var(--surface-muted)] p-3"
          >
            <div className="mb-2 flex items-start justify-between gap-3">
              <time className="text-xs text-[var(--muted)]">
                {new Date(note.created_at).toLocaleString()}
              </time>
              <button
                type="button"
                onClick={() => void removeNote(note.id)}
                disabled={mutationStatus === "loading"}
                className="text-xs font-medium text-red-700 hover:underline disabled:opacity-60"
              >
                Delete
              </button>
            </div>
            <p className="whitespace-pre-wrap text-sm text-[var(--ink)]">
              {note.content}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}
