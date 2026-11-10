import { apiFetch } from "@/lib/session";

export type WeeklyLocation = {
  location_id: string;
  country: string;
  total_purchase_cost: number;
  total_waste_cost: number;
  waste_ratio: number;
  stockout_events_count: number;
  price_alert_events_count: number;
  currency: string;
};

export type WeeklyLocationReport = {
  week_start: string;
  locations: WeeklyLocation[];
};

export async function fetchWeeklyLocationPerformance(): Promise<WeeklyLocationReport> {
  const response = await apiFetch("/reporting/weekly-location-performance");
  if (response.status === 404) {
    return { week_start: "", locations: [] };
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    const detail = typeof body?.detail === "string" ? body.detail : "";
    throw new Error(detail || `Weekly report failed (${response.status})`);
  }
  return (await response.json()) as WeeklyLocationReport;
}
