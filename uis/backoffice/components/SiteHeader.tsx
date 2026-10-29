"use client";

import { logout } from "@/lib/session";
import { useState } from "react";
import ApiLink from "./ApiLink";

export default function SiteHeader({ current }: { current?: "directory" | "account" | "password" }) {
  const [open, setOpen] = useState(false);
  return (
    <header className="site-header">
      <div className="header-bar">
        <ApiLink className="brand" href="/">Brasaland</ApiLink>
        <button className="nav-toggle" type="button" aria-expanded={open} aria-controls="site-nav" onClick={() => setOpen(!open)}>
          {open ? "Close navigation" : "Open navigation"}
        </button>
      </div>
      <nav id="site-nav" className={`site-nav ${open ? "is-open" : ""}`} aria-label="Primary">
        <ApiLink href="/" aria-current={current === "directory" ? "page" : undefined}>Supplier directory</ApiLink>
        <ApiLink href="/account/profile" aria-current={current === "account" ? "page" : undefined}>Account</ApiLink>
        {current === "password" && <ApiLink href="/account/change-password" aria-current="page">Change password</ApiLink>}
        <button className="nav-logout" type="button" onClick={() => void logout()}>Log out</button>
      </nav>
    </header>
  );
}

export function PublicHeader() {
  return <header className="site-header"><div className="header-bar"><ApiLink className="brand" href="/">Brasaland</ApiLink></div></header>;
}
