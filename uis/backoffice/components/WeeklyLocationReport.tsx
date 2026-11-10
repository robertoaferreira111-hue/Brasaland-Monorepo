"use client";

import { useEffect, useState } from "react";
import {
  fetchWeeklyLocationPerformance,
  type WeeklyLocationReport,
} from "@/services/reporting";

const money = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });
const ratio = new Intl.NumberFormat("en-US", { style: "percent", maximumFractionDigits: 1 });
const weekDay = new Intl.DateTimeFormat("en-US", {
  timeZone: "UTC",
  weekday: "long",
  year: "numeric",
  month: "long",
  day: "numeric",
});

function formatWeek(weekStart: string) {
  const start = new Date(`${weekStart}T00:00:00Z`);
  if (Number.isNaN(start.getTime())) return weekStart;
  const end = new Date(start);
  end.setUTCDate(start.getUTCDate() + 6);
  return `Week of ${weekDay.format(start)} through ${weekDay.format(end)}`;
}

function formatMoney(amount: number, currency: string) {
  return `${money.format(amount)} ${currency}`;
}

export default function WeeklyLocationReport() {
  const [report, setReport] = useState<WeeklyLocationReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchWeeklyLocationPerformance();
        if (!cancelled) setReport(data);
      } catch (err) {
        if (!cancelled) {
          setReport(null);
          setError(err instanceof Error ? err.message : "The weekly report could not be loaded.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return <p className="status-line" role="status">Loading the weekly report…</p>;
  }

  if (error) {
    return (
      <div className="message message-error" role="alert">
        <p>{error}</p>
        <p className="recovery-hint">Confirm the API is running and try refreshing the page.</p>
      </div>
    );
  }

  if (!report || report.locations.length === 0) {
    return (
      <p className="message" role="status">
        No weekly report has been published yet. Locations will appear here after the Monday report is ready.
      </p>
    );
  }

  return (
    <div className="weekly-location-report">
      <section className="panel" aria-labelledby="report-week-heading">
        <h2 id="report-week-heading">Week</h2>
        <p className="status-line">{formatWeek(report.week_start)}</p>
        <p className="status-line">
          Each location stays in its own currency. COP and USD are listed side by side and are not added together.
        </p>
      </section>
      <div className="table-wrap">
        <table className="report-table">
          <caption className="sr-only">Weekly Location Cost & Waste Report</caption>
          <thead>
            <tr>
              <th scope="col">Location</th>
              <th scope="col">Country</th>
              <th scope="col">Currency</th>
              <th scope="col" className="num">Purchase Cost per Location</th>
              <th scope="col" className="num">Waste Cost per Location</th>
              <th scope="col" className="num">Waste Ratio</th>
              <th scope="col" className="num">Stockout Frequency</th>
              <th scope="col" className="num">Price Alert Frequency</th>
            </tr>
          </thead>
          <tbody>
            {report.locations.map((location) => (
              <tr key={`${location.location_id}-${report.week_start}`}>
                <th scope="row">{location.location_id}</th>
                <td>{location.country}</td>
                <td>{location.currency}</td>
                <td className="num">{formatMoney(location.total_purchase_cost, location.currency)}</td>
                <td className="num">{formatMoney(location.total_waste_cost, location.currency)}</td>
                <td className="num">{ratio.format(location.waste_ratio)}</td>
                <td className="num">{location.stockout_events_count}</td>
                <td className="num">{location.price_alert_events_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
