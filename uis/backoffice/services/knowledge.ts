import { resolveApiBase } from "@/lib/apiBase";
import { apiFetch, errorText } from "@/lib/session";

export async function askKnowledge(question: string) {
  let response: Response;
  try {
    response = await apiFetch("/knowledge/query", {
      auth: false,
      method: "POST",
      body: JSON.stringify({ question }),
    });
  } catch {
    throw new Error(`The API is not reachable at ${resolveApiBase()}.`);
  }
  if (!response.ok) throw new Error(await errorText(response));
  const body = (await response.json()) as { answer?: unknown };
  if (typeof body.answer !== "string" || !body.answer.trim()) {
    throw new Error("The knowledge service returned an empty answer.");
  }
  return body.answer;
}
