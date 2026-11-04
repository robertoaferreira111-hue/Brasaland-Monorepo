import { apiFetch } from "@/lib/session";

export type TelemetryPeriod = { from: string; to: string };

export type EventsPerDay = { date: string; count: number };
export type ErrorRateByType = {
  event_type: string;
  total_events: number;
  error_events: number;
  error_rate: number;
};
export type EventsByDimension = {
  dimension: string;
  dimension_value: string | null;
  count: number;
};
export type AuthFailureRate = {
  date: string;
  failed_attempts: number;
  succeeded_attempts: number;
  total_attempts: number;
  auth_failure_rate: number;
};

export type TelemetryReport = {
  period: TelemetryPeriod;
  metrics: {
    events_per_day: EventsPerDay[];
    error_rate_by_type: ErrorRateByType[];
    events_by_dimension: EventsByDimension[];
    auth_failure_rate: AuthFailureRate[];
  };
};

export async function fetchTelemetryReport(params?: {
  start_date?: string;
  end_date?: string;
}): Promise<TelemetryReport> {
  const query = new URLSearchParams();
  if (params?.start_date) query.set("start_date", params.start_date);
  if (params?.end_date) query.set("end_date", params.end_date);
  const suffix = query.toString() ? `?${query}` : "";
  const response = await apiFetch(`/telemetry/report${suffix}`);
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null;
    throw new Error(body?.detail || `Telemetry report failed (${response.status})`);
  }
  return (await response.json()) as TelemetryReport;
}
