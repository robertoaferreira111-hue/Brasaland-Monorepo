"use client";

import { useEffect, useState } from "react";
import {
  fetchTelemetryReport,
  type TelemetryReport,
} from "@/services/telemetry";

function formatPeriod(iso: string) {
  try {
    return new Date(iso).toISOString().replace(".000Z", "Z");
  } catch {
    return iso;
  }
}

function Bar({ value, max }: { value: number; max: number }) {
  const width = max > 0 ? Math.max(2, Math.round((100 * value) / max)) : 0;
  return (
    <div className="telemetry-bar-track" aria-hidden="true">
      <div className="telemetry-bar-fill" style={{ width: `${width}%` }} />
    </div>
  );
}

export default function TelemetryDashboard() {
  const [report, setReport] = useState<TelemetryReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchTelemetryReport();
        if (!cancelled) setReport(data);
      } catch (err) {
        if (!cancelled) {
          setReport(null);
          setError(err instanceof Error ? err.message : "Failed to load telemetry report");
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
    return <p className="status-line" role="status">Loading telemetry report…</p>;
  }

  if (error) {
    return (
      <div className="message message-error" role="alert">
        <p>{error}</p>
        <p className="recovery-hint">Confirm the API is running and try refreshing the page.</p>
      </div>
    );
  }

  if (!report) {
    return <p className="status-line">No telemetry report available.</p>;
  }

  const { period, metrics } = report;
  const perDay = metrics.events_per_day ?? [];
  const errorRates = metrics.error_rate_by_type ?? [];
  const byDimension = metrics.events_by_dimension ?? [];
  const authRates = metrics.auth_failure_rate ?? [];
  const maxDay = Math.max(0, ...perDay.map((row) => row.count));
  const maxDim = Math.max(0, ...byDimension.map((row) => row.count));
  const empty =
    perDay.every((row) => row.count === 0) &&
    errorRates.length === 0 &&
    byDimension.length === 0 &&
    authRates.every((row) => row.total_attempts === 0);

  return (
    <div className="telemetry-dashboard">
      <section className="panel" aria-labelledby="telemetry-period-heading">
        <h2 id="telemetry-period-heading">Reporting period</h2>
        <p className="status-line">
          <span className="sr-only">From </span>
          {formatPeriod(period.from)}
          <span aria-hidden="true"> → </span>
          <span className="sr-only"> to </span>
          {formatPeriod(period.to)}
          <span className="sr-only"> (UTC)</span>
        </p>
      </section>

      {empty && (
        <p className="message" role="status">
          No telemetry events in this period. Operational tables below stay empty until events are captured.
        </p>
      )}

      <section className="panel" aria-labelledby="events-per-day-heading">
        <h2 id="events-per-day-heading">Events per day</h2>
        {perDay.length === 0 ? (
          <p className="status-line">No daily event counts.</p>
        ) : (
          <div className="table-wrap telemetry-table-wrap">
            <table>
              <thead>
                <tr>
                  <th scope="col">Date (UTC)</th>
                  <th scope="col">Count</th>
                  <th scope="col">Volume</th>
                </tr>
              </thead>
              <tbody>
                {perDay.map((row) => (
                  <tr key={row.date}>
                    <td>{row.date}</td>
                    <td>{row.count}</td>
                    <td><Bar value={row.count} max={maxDay} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel" aria-labelledby="error-rate-heading">
        <h2 id="error-rate-heading">Error rate by event type</h2>
        {errorRates.length === 0 ? (
          <p className="status-line">No event-type error rates.</p>
        ) : (
          <div className="table-wrap telemetry-table-wrap">
            <table>
              <thead>
                <tr>
                  <th scope="col">Event type</th>
                  <th scope="col">Total</th>
                  <th scope="col">Errors</th>
                  <th scope="col">Error rate %</th>
                </tr>
              </thead>
              <tbody>
                {errorRates.map((row) => (
                  <tr key={row.event_type}>
                    <td><code>{row.event_type}</code></td>
                    <td>{row.total_events}</td>
                    <td>{row.error_events}</td>
                    <td>{row.error_rate}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel" aria-labelledby="dimension-heading">
        <h2 id="dimension-heading">Events by route</h2>
        {byDimension.length === 0 ? (
          <p className="status-line">No route dimension data.</p>
        ) : (
          <div className="table-wrap telemetry-table-wrap">
            <table>
              <thead>
                <tr>
                  <th scope="col">Route</th>
                  <th scope="col">Count</th>
                  <th scope="col">Share</th>
                </tr>
              </thead>
              <tbody>
                {byDimension.map((row) => (
                  <tr key={`${row.dimension}-${row.dimension_value ?? "null"}`}>
                    <td><code>{row.dimension_value ?? "(none)"}</code></td>
                    <td>{row.count}</td>
                    <td><Bar value={row.count} max={maxDim} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel" aria-labelledby="auth-rate-heading">
        <h2 id="auth-rate-heading">Daily authentication failure rate</h2>
        <p className="status-line">
          Based on verified <code>staff_login_failed</code> events. The catalogue has no login-success event yet, so recorded attempts are failures only.
        </p>
        {authRates.length === 0 ? (
          <p className="status-line">No authentication metrics.</p>
        ) : (
          <div className="table-wrap telemetry-table-wrap">
            <table>
              <thead>
                <tr>
                  <th scope="col">Date (UTC)</th>
                  <th scope="col">Failed</th>
                  <th scope="col">Succeeded</th>
                  <th scope="col">Total</th>
                  <th scope="col">Failure rate</th>
                </tr>
              </thead>
              <tbody>
                {authRates.map((row) => (
                  <tr key={row.date}>
                    <td>{row.date}</td>
                    <td>{row.failed_attempts}</td>
                    <td>{row.succeeded_attempts}</td>
                    <td>{row.total_attempts}</td>
                    <td>{(row.auth_failure_rate * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
