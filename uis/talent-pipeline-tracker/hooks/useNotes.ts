"use client";

import { useCallback, useEffect, useState } from "react";
import { createNote, deleteNote, getNotes } from "@/lib/api";
import type { Note } from "@/types/candidate";

type AsyncStatus = "idle" | "loading" | "success" | "error";

export function useNotes(recordId: string) {
  const [notes, setNotes] = useState<Note[]>([]);
  const [status, setStatus] = useState<AsyncStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [mutationStatus, setMutationStatus] = useState<AsyncStatus>("idle");
  const [mutationError, setMutationError] = useState<string | null>(null);
  const [mutationSuccess, setMutationSuccess] = useState<string | null>(null);

  const load = useCallback(async () => {
    setStatus("loading");
    setError(null);
    try {
      const response = await getNotes(recordId);
      setNotes(response.data);
      setStatus("success");
    } catch (err) {
      setNotes([]);
      setStatus("error");
      setError(err instanceof Error ? err.message : "Failed to load notes.");
    }
  }, [recordId]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  const addNote = useCallback(
    async (content: string) => {
      setMutationStatus("loading");
      setMutationError(null);
      setMutationSuccess(null);
      try {
        const note = await createNote(recordId, content);
        setNotes((current) => [note, ...current]);
        setMutationStatus("success");
        setMutationSuccess("Note added.");
        return true;
      } catch (err) {
        setMutationStatus("error");
        setMutationError(
          err instanceof Error ? err.message : "Failed to add note.",
        );
        return false;
      }
    },
    [recordId],
  );

  const removeNote = useCallback(
    async (noteId: string) => {
      setMutationStatus("loading");
      setMutationError(null);
      setMutationSuccess(null);
      try {
        await deleteNote(recordId, noteId);
        setNotes((current) => current.filter((note) => note.id !== noteId));
        setMutationStatus("success");
        setMutationSuccess("Note deleted.");
        return true;
      } catch (err) {
        setMutationStatus("error");
        setMutationError(
          err instanceof Error ? err.message : "Failed to delete note.",
        );
        return false;
      }
    },
    [recordId],
  );

  return {
    notes,
    status,
    error,
    mutationStatus,
    mutationError,
    mutationSuccess,
    addNote,
    removeNote,
    reload: load,
  };
}
