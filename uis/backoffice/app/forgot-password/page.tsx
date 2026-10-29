import { ForgotPasswordForm } from "@/components/AuthForms";
import { PublicHeader } from "@/components/SiteHeader";

export default function ForgotPasswordPage() {
  return <><PublicHeader /><main id="main" className="auth-main" tabIndex={-1}><header className="page-intro"><h1>Forgot password</h1><p>Enter your account email. If it is registered, we will send a reset link.</p></header><ForgotPasswordForm /></main></>;
}
