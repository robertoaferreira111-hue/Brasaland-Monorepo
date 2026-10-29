import AuthGuard from "@/components/AuthGuard";
import ProfileForm from "@/components/ProfileForm";
import SiteHeader from "@/components/SiteHeader";

export default function ProfilePage() {
  return <AuthGuard><SiteHeader current="account" /><main id="main" className="auth-main" tabIndex={-1}><header className="page-intro"><h1>Account</h1><p>Your email stays on the account. Update the name, phone, and address procurement can use.</p></header><ProfileForm /></main></AuthGuard>;
}
