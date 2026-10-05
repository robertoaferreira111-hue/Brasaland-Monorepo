"use client";

import { FormEvent, useCallback, useState } from "react";
import { FeedbackBanner } from "@/components/FeedbackBanner";
import { useAsync } from "@/hooks/useAsync";
import { addNote, deleteNote, listNotes } from "@/services/notes";
import type { Note } from "@/types/api";
import { ApiError } from "@/types/api";

/**
 * Internal notes for a candidate (detail view only).
 * Ordering: API returns notes ascending by `created_at` (oldest first); UI shows that order.
 */
export function NotesPanel({ recordId }: { recordId: string }) {
  const loader = useCallback(() => listNotes(recordId), [recordId]);
  const { data, error, status, refetch } = useAsync(loader);

  const [override, setOverride] = useState<Note[] | null>(null);
  const [overrideForId, setOverrideForId] = useState<string | null>(null);
  const list =
    override && overrideForId === recordId ? override : (data ?? []);

  const [content, setContent] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  const [mutationStatus, setMutationStatus] = useState<
    "idle" | "loading" | "success" | "error"
  >("idle");
  const [mutationError, setMutationError] = useState<string | null>(null);
  const [mutationSuccess, setMutationSuccess] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLocalError(null);
    setMutationError(null);
    setMutationSuccess(null);

    if (!content.trim()) {
      setLocalError("Note content is required.");
      return;
    }

    setMutationStatus("loading");
    try {
      await addNote(recordId, { content: content.trim() });
      const refreshed = await refetch({ keepPreviousData: true });
      if (refreshed) {
        setOverride(refreshed);
        setOverrideForId(recordId);
      }
      setContent("");
      setMutationStatus("success");
      setMutationSuccess("Note added.");
    } catch (err) {
      setMutationStatus("error");
      setMutationError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Failed to add note.",
      );
    }
  }

  async function handleDelete(noteId: string) {
    setMutationError(null);
    setMutationSuccess(null);
    setMutationStatus("loading");
    try {
      await deleteNote(recordId, noteId);
      const refreshed = await refetch({ keepPreviousData: true });
      if (refreshed) {
        setOverride(refreshed);
        setOverrideForId(recordId);
      }
      setMutationStatus("success");
      setMutationSuccess("Note deleted.");
    } catch (err) {
      setMutationStatus("error");
      setMutationError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Failed to delete note.",
      );
    }
  }

  const busy = mutationStatus === "loading";

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

      {(status === "loading" || status === "idle") && list.length === 0 ? (
        <FeedbackBanner tone="info" message="Loading notes…" />
      ) : null}

      {status === "error" && error && overrideForId !== recordId ? (
        <div className="grid gap-2">
          <FeedbackBanner tone="error" message={error} />
          <button
            type="button"
            onClick={() => void refetch()}
            className="w-fit text-sm font-medium text-[var(--accent)] underline"
          >
            Try again
          </button>
        </div>
      ) : null}

      {busy ? (
        <FeedbackBanner tone="info" message="Updating notes…" />
      ) : null}
      {mutationError ? (
        <FeedbackBanner tone="error" message={mutationError} />
      ) : null}
      {mutationSuccess ? (
        <FeedbackBanner tone="success" message={mutationSuccess} />
      ) : null}
      {localError ? <FeedbackBanner tone="error" message={localError} /> : null}

      <form onSubmit={handleSubmit} className="grid gap-2">
        <label className="grid gap-1 text-sm">
          <span className="font-medium text-[var(--ink)]">Add note</span>
          <textarea
            value={content}
            onChange={(event) => setContent(event.target.value)}
            rows={3}
            disabled={busy}
            className="rounded-md border border-[var(--border)] bg-white px-3 py-2 text-[var(--ink)] outline-none ring-[var(--accent)] focus:ring-2 disabled:opacity-60"
            placeholder="Summary of the latest conversation…"
          />
        </label>
        <button
          type="submit"
          disabled={busy}
          className="w-fit rounded-md bg-[var(--accent)] px-3 py-2 text-sm font-semibold text-white transition hover:bg-[var(--accent-strong)] disabled:opacity-60"
        >
          Add note
        </button>
      </form>

      {(status === "success" || overrideForId === recordId) &&
      list.length === 0 ? (
        <p className="text-sm text-[var(--muted)]">No notes yet.</p>
      ) : null}

      <ul className="grid gap-3">
        {list.map((note) => (
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
                onClick={() => void handleDelete(note.id)}
                disabled={busy}
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
