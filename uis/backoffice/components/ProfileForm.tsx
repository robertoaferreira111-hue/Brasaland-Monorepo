"use client";

import { errorText } from "@/lib/session";
import { resolveApiBase } from "@/lib/apiBase";
import { getProfile, updateProfile } from "@/services/profiles";
import { useEffect, useState, type FormEvent } from "react";
import ApiLink from "./ApiLink";

type Profile = { email: string; name: string; phone: string; address: string };

export default function ProfileForm() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState(""); const [success, setSuccess] = useState(""); const [busy, setBusy] = useState(false);
  useEffect(() => {
    void (async () => {
      try {
        const response = await getProfile();
        if (!response.ok) { setError(await errorText(response)); return; }
        setProfile(await response.json() as Profile);
      } catch (caught) {
        if (!(caught instanceof Error && caught.message === "Session expired")) setError(`The API is not reachable at ${resolveApiBase()}.`);
      }
    })();
  }, []);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setSuccess(""); setBusy(true);
    const data = new FormData(event.currentTarget);
    try {
      const response = await updateProfile({ name: String(data.get("name")), phone: String(data.get("phone")), address: String(data.get("address")) });
      if (!response.ok) { setError(await errorText(response)); return; }
      setProfile(await response.json() as Profile); setSuccess("Profile saved.");
    } catch (caught) {
      if (!(caught instanceof Error && caught.message === "Session expired")) setError(`The API is not reachable at ${resolveApiBase()}.`);
    } finally { setBusy(false); }
  }
  return <><p className="status-line" role="status">{!profile && !error ? "Loading profile…" : ""}</p><section className="panel">
    {profile && <form className="register-form" noValidate onSubmit={submit}>
      <label>Email<input name="email" value={profile.email} readOnly /></label>
      <label>Name<input name="name" autoComplete="name" required value={profile.name || ""} onChange={(event) => setProfile({...profile,name:event.target.value})} /></label>
      <label>Phone<input name="phone" autoComplete="tel" required value={profile.phone || ""} onChange={(event) => setProfile({...profile,phone:event.target.value})} /></label>
      <label>Address<input name="address" autoComplete="street-address" required value={profile.address || ""} onChange={(event) => setProfile({...profile,address:event.target.value})} /></label>
      <div><button disabled={busy}>{busy ? "Saving…" : "Save profile"}</button></div>
    </form>}
    {error && <p className="message message-error" role="alert">{error}</p>}{success && <p className="message message-success" role="status">{success}</p>}
    <p><ApiLink href="/account/change-password">Change password</ApiLink></p>
  </section></>;
}
