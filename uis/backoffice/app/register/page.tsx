import { RegisterForm } from "@/components/AuthForms";
import { PublicHeader } from "@/components/SiteHeader";

export default function RegisterPage() {
  return <><PublicHeader /><main id="main" className="auth-main" tabIndex={-1}><header className="page-intro"><h1>Register</h1><p>Create a staff account, then continue to the supplier directory.</p></header><RegisterForm /></main></>;
}
