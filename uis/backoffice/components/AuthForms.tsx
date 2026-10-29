"use client";

import { changePassword, forgotPassword, login, register, resetPassword, type Tokens } from "@/services/auth";
import { appHref, errorText, goAfterLogin, hasAccessToken, saveTokens } from "@/lib/session";
import { resolveApiBase } from "@/lib/apiBase";
import { useEffect, useState, type FormEvent } from "react";
import ApiLink from "./ApiLink";

function apiUnavailable() { return `The API is not reachable at ${resolveApiBase()}.`; }

export function LoginForm() {
  const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  useEffect(() => { if (hasAccessToken()) goAfterLogin(); }, []);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setBusy(true);
    const data = new FormData(event.currentTarget);
    try {
      const response = await login(String(data.get("email")), String(data.get("password")));
      if (!response.ok) { setError(await errorText(response)); return; }
      const tokens = await response.json() as Tokens;
      saveTokens(tokens.access_token, tokens.refresh_token); goAfterLogin();
    } catch { setError(apiUnavailable()); } finally { setBusy(false); }
  }
  return <section className="panel"><form className="register-form" noValidate onSubmit={submit}>
    <label>Email<input name="email" type="email" autoComplete="username" required /></label>
    <label>Password<input name="password" type="password" autoComplete="current-password" required /></label>
    <div className="form-actions"><button disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button></div>
  </form>{error && <p className="message message-error" role="alert">{error}</p>}
    <p><ApiLink href="/forgot-password">Forgot your password?</ApiLink></p><p>No account yet? <ApiLink href="/register">Register</ApiLink></p></section>;
}

type FieldErrors = Partial<Record<"email" | "password" | "name" | "phone" | "address", string>>;
export function RegisterForm() {
  const [errors, setErrors] = useState<FieldErrors>({}); const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  useEffect(() => { if (hasAccessToken()) goAfterLogin(); }, []);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setErrors({}); setError("");
    const data = new FormData(event.currentTarget); const email = String(data.get("email")).trim(); const password = String(data.get("password"));
    const client: FieldErrors = {};
    if (!email) client.email = "Email is required."; else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) client.email = "Enter a valid email (example: name@email.com).";
    if (!password) client.password = "Password is required.";
    if (Object.keys(client).length) { setErrors(client); return; }
    const profile = { name: String(data.get("name")).trim(), phone: String(data.get("phone")).trim(), address: String(data.get("address")).trim() };
    setBusy(true);
    try {
      const created = await register(email, password, profile);
      if (!created.ok) {
        let payload: { detail?: unknown } | null = null; try { payload = await created.json(); } catch {}
        if (Array.isArray(payload?.detail)) {
          const fields: FieldErrors = {};
          for (const item of payload.detail as { loc?: unknown[]; msg?: string }[]) {
            const field = item.loc?.filter((part) => part !== "body")[0];
            if (typeof field === "string" && ["email","password","name","phone","address"].includes(field) && item.msg) fields[field as keyof FieldErrors] = item.msg;
          }
          if (Object.keys(fields).length) { setErrors(fields); return; }
        }
        setError(typeof payload?.detail === "string" ? payload.detail : `The API returned HTTP ${created.status}.`); return;
      }
      const signedIn = await login(email, password);
      if (!signedIn.ok) { setError(await errorText(signedIn)); return; }
      const tokens = await signedIn.json() as Tokens; saveTokens(tokens.access_token, tokens.refresh_token); goAfterLogin();
    } catch { setError(apiUnavailable()); } finally { setBusy(false); }
  }
  const field = (name: keyof FieldErrors, label: string, props: React.InputHTMLAttributes<HTMLInputElement> = {}) =>
    <label>{label}<input name={name} aria-describedby={`${name}-error`} {...props} />{errors[name] && <span id={`${name}-error`} className="field-error" role="alert">{errors[name]}</span>}</label>;
  return <section className="panel"><form className="register-form" noValidate onSubmit={submit}>
    {field("email","Email",{type:"email",autoComplete:"username",required:true})}{field("password","Password",{type:"password",autoComplete:"new-password",required:true})}
    {field("name","Name (optional)",{autoComplete:"name"})}{field("phone","Phone (optional)",{autoComplete:"tel"})}{field("address","Address (optional)",{autoComplete:"street-address"})}
    <div className="form-actions"><button disabled={busy}>{busy ? "Creating…" : "Create account"}</button></div>
  </form>{error && <p className="message message-error" role="alert">{error}</p>}<p>Already registered? <ApiLink href="/login">Sign in</ApiLink></p></section>;
}

export function ForgotPasswordForm() {
  const [error,setError]=useState(""); const [success,setSuccess]=useState(""); const [busy,setBusy]=useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setSuccess(""); setBusy(true);
    try { const response=await forgotPassword(String(new FormData(event.currentTarget).get("email")));
      if(!response.ok){setError(await errorText(response));return;} const body=await response.json() as {message?:string};
      setSuccess(body.message || "If that address is registered, you'll receive a link shortly."); event.currentTarget.reset();
    } catch {setError(apiUnavailable());} finally {setBusy(false);}
  }
  return <section className="panel"><form className="register-form" noValidate onSubmit={submit}><label>Email<input name="email" type="email" autoComplete="email" required /></label><div><button disabled={busy}>{busy?"Sending…":"Send reset link"}</button></div></form>
    {error&&<p className="message message-error" role="alert">{error}</p>}{success&&<p className="message message-success" role="status">{success}</p>}<p><ApiLink href="/login">Back to sign in</ApiLink></p></section>;
}

export function ResetPasswordForm() {
  const [token,setToken]=useState<string|null>(null); const [error,setError]=useState(""); const [success,setSuccess]=useState(""); const [fieldError,setFieldError]=useState(""); const [busy,setBusy]=useState(false);
  useEffect(()=>setToken(new URLSearchParams(window.location.search).get("token") || ""),[]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if(!token)return; setError("");setSuccess("");setFieldError("");
    const data=new FormData(event.currentTarget), password=String(data.get("new_password")), confirmation=String(data.get("confirm_password"));
    if(password.length<8){setFieldError("Password must be at least 8 characters.");return;} if(password!==confirmation){setFieldError("New password and confirmation must match.");return;}
    setBusy(true); try {const response=await resetPassword(token,password);if(!response.ok){setError(await errorText(response));return;}const body=await response.json() as {message?:string};setSuccess(body.message||"Password has been reset successfully.");setTimeout(()=>window.location.assign(appHref("/login")),1200);
    } catch {setError(apiUnavailable());} finally {setBusy(false);}
  }
  if(token===null)return <p className="status-line">Checking reset link…</p>;
  return <section className="panel">{!token?<p>This reset link is missing a token. <ApiLink href="/forgot-password">Request a new reset link</ApiLink></p>:
    !success&&<form className="register-form" noValidate onSubmit={submit}><label>New password<input name="new_password" type="password" autoComplete="new-password" minLength={8} required /></label><label>Confirm new password<input name="confirm_password" type="password" autoComplete="new-password" minLength={8} required /></label>{fieldError&&<p className="field-error" role="alert">{fieldError}</p>}<div><button disabled={busy}>{busy?"Resetting…":"Reset password"}</button></div></form>}
    {!token&&<p className="message message-error" role="alert">This reset link is missing a token. Request a new password reset email.</p>}{error&&<p className="message message-error" role="alert">{error}</p>}{success&&<p className="message message-success" role="status">{success}</p>}<p><ApiLink href="/forgot-password">Forgot your password?</ApiLink> · <ApiLink href="/login">Back to sign in</ApiLink></p></section>;
}

export function ChangePasswordForm() {
  const [error,setError]=useState("");const [success,setSuccess]=useState("");const [fieldError,setFieldError]=useState("");const [busy,setBusy]=useState(false);
  async function submit(event:FormEvent<HTMLFormElement>){event.preventDefault();setError("");setSuccess("");setFieldError("");const form=event.currentTarget,data=new FormData(form),current=String(data.get("current_password")),password=String(data.get("new_password")),confirmation=String(data.get("confirm_password"));
    if(!current){setFieldError("Enter your current password.");return;}if(password.length<8){setFieldError("Password must be at least 8 characters.");return;}if(password!==confirmation){setFieldError("New password and confirmation must match.");return;}
    setBusy(true);try{const response=await changePassword(current,password);if(!response.ok){setError(await errorText(response));return;}const body=await response.json() as {message?:string};setSuccess(body.message||"Password has been changed successfully.");form.reset();}catch(error){if(!(error instanceof Error&&error.message==="Session expired"))setError(apiUnavailable());}finally{setBusy(false);}
  }
  return <section className="panel"><form className="register-form" noValidate onSubmit={submit}><label>Current password<input name="current_password" type="password" autoComplete="current-password" required /></label><label>New password<input name="new_password" type="password" autoComplete="new-password" minLength={8} required /></label><label>Confirm new password<input name="confirm_password" type="password" autoComplete="new-password" minLength={8} required /></label>{fieldError&&<p className="field-error" role="alert">{fieldError}</p>}<div><button disabled={busy}>{busy?"Updating…":"Update password"}</button></div></form>{error&&<p className="message message-error" role="alert">{error}</p>}{success&&<p className="message message-success" role="status">{success}</p>}</section>;
}
