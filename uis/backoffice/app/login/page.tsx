"use client";

import {
  AuthCard,
  FormError,
  SubmitButton,
  TextField,
  TextLink,
} from "@/components/AuthCard";
import { login, SessionExpiredError, toErrorMessage } from "@/lib/api";
import {
  authCredentials,
  emailFieldError,
  passwordFieldError,
  withoutSecret,
} from "@/lib/credentials";
import { hasAccessToken } from "@/lib/token";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [emailError, setEmailError] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (hasAccessToken()) {
      router.replace("/account");
    }
  }, [router]);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) {
      return;
    }
    const nextEmailError = emailFieldError(email);
    const nextPasswordError = passwordFieldError(password);
    setEmailError(nextEmailError);
    setPasswordError(nextPasswordError);
    setError("");
    if (nextEmailError || nextPasswordError) {
      document.getElementById(nextEmailError ? "email" : "password")?.focus();
      return;
    }
    const credentials = authCredentials(email, password);
    if (!credentials) {
      return;
    }
    setPending(true);
    try {
      await login(credentials.email, credentials.password);
      router.push("/account");
    } catch (caught) {
      if (!(caught instanceof SessionExpiredError)) {
        setError(withoutSecret(toErrorMessage(caught), password));
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <AuthCard
      title="Staff sign in"
      intro="Use your Brasaland account. The session token stays in this browser."
    >
      <form className="grid gap-4" noValidate onSubmit={onSubmit}>
        <FormError message={error} />
        <TextField
          id="email"
          label="Email"
          type="email"
          name="email"
          autoComplete="email"
          value={email}
          error={emailError}
          onChange={(event) => {
            setEmail(event.target.value);
            setEmailError("");
          }}
        />
        <TextField
          id="password"
          label="Password"
          type="password"
          name="password"
          autoComplete="current-password"
          value={password}
          error={passwordError}
          onChange={(event) => {
            setPassword(event.target.value);
            setPasswordError("");
          }}
        />
        <SubmitButton pending={pending}>Sign in</SubmitButton>
      </form>
      <p className="mt-6 font-sans text-sm">
        New staff member? <TextLink href="/register">Create an account</TextLink>
      </p>
    </AuthCard>
  );
}
