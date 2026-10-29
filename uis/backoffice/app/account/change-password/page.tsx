import AuthGuard from "@/components/AuthGuard";
import { ChangePasswordForm } from "@/components/AuthForms";
import SiteHeader from "@/components/SiteHeader";

export default function ChangePasswordPage() {
  return <AuthGuard><SiteHeader current="password" /><main id="main" className="auth-main" tabIndex={-1}><header className="page-intro"><h1>Change password</h1><p>Update your password while signed in to the backoffice.</p></header><ChangePasswordForm /></main></AuthGuard>;
}
