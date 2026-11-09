import AuthGuard from "@/components/AuthGuard";
import SiteHeader from "@/components/SiteHeader";
import WeeklyLocationReport from "@/components/WeeklyLocationReport";

export default function ReportingPage() {
  return (
    <AuthGuard>
      <SiteHeader current="reporting" />
      <main id="main" tabIndex={-1}>
        <header className="page-intro">
          <h1>Weekly Location Cost & Waste Report</h1>
          <p>
            For the CEO and the Operations Director. Compare purchase cost, waste, stockouts, and price alerts for each location for the week shown below.
          </p>
        </header>
        <WeeklyLocationReport />
      </main>
      <footer className="site-footer">
        <p>© 2025 Brasaland. All rights reserved.</p>
      </footer>
    </AuthGuard>
  );
}
