import AuthGuard from "@/components/AuthGuard";
import SiteHeader from "@/components/SiteHeader";
import SupplierDirectory from "@/components/SupplierDirectory";

export default function DirectoryPage() {
  return <AuthGuard><SiteHeader current="directory" /><main id="main" tabIndex={-1}>
    <header className="page-intro"><h1>Supplier directory</h1><p>Procurement list for Lucía Fernández. Active and suspended suppliers stay in this directory. Rates and status are saved through the supplier API.</p></header>
    <SupplierDirectory />
  </main><footer className="site-footer"><p>© 2025 Brasaland. All rights reserved.</p></footer></AuthGuard>;
}
