import { ResetPasswordForm } from "@/components/AuthForms";
import { PublicHeader } from "@/components/SiteHeader";

export default function ResetPasswordPage() {
  return <><PublicHeader /><main id="main" className="auth-main" tabIndex={-1}><header className="page-intro"><h1>Reset password</h1><p>Choose a new password for your Brasaland account.</p></header><ResetPasswordForm /></main></>;
}
