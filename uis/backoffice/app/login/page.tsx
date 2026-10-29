import { LoginForm } from "@/components/AuthForms";
import { PublicHeader } from "@/components/SiteHeader";

export default function LoginPage() {
  return <><PublicHeader /><main id="main" className="auth-main" tabIndex={-1}><header className="page-intro"><h1>Sign in</h1><p>Staff access for the supplier directory and your account profile.</p></header><LoginForm /></main></>;
}
