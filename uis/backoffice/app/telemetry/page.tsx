import AuthGuard from "@/components/AuthGuard";
import SiteHeader from "@/components/SiteHeader";
import TelemetryDashboard from "@/components/TelemetryDashboard";

export default function TelemetryPage() {
  return (
    <AuthGuard>
      <SiteHeader current="telemetry" />
      <main id="main" tabIndex={-1}>
        <header className="page-intro">
          <h1>Telemetry report</h1>
          <p>
            Technical and operational metrics from <code>GET /telemetry/report</code>.
            This view is not a business KPI dashboard.
          </p>
        </header>
        <TelemetryDashboard />
      </main>
      <footer className="site-footer">
        <p>© 2025 Brasaland. All rights reserved.</p>
      </footer>
    </AuthGuard>
  );
}
