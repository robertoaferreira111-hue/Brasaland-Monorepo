"use client";

import { askKnowledge } from "@/services/knowledge";
import { FormEvent, useState } from "react";

export default function KnowledgeQuery() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = question.trim();
    if (!text || busy) return;
    setBusy(true);
    setError("");
    setAnswer("");
    try {
      setAnswer(await askKnowledge(text));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The knowledge service is unavailable.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel" aria-busy={busy}>
      <form className="register-form" onSubmit={(event) => void submit(event)}>
        <label>
          Question
          <textarea
            name="question"
            rows={4}
            required
            value={question}
            placeholder="How many points do I need for Gold tier?"
            onChange={(event) => setQuestion(event.target.value)}
          />
        </label>
        <div>
          <button type="submit" disabled={busy || !question.trim()}>
            {busy ? "Checking the manuals…" : "Ask"}
          </button>
        </div>
      </form>
      {busy && (
        <p className="status-line" role="status">
          Checking the manuals…
        </p>
      )}
      {answer && (
        <p className="message knowledge-answer" role="status">
          {answer}
        </p>
      )}
      {error && (
        <p className="message message-error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
