"use client";

import {
  AuthCard,
  FormError,
  SubmitButton,
  TextField,
  TextLink,
} from "@/components/AuthCard";
import { registerUser, SessionExpiredError, toErrorMessage } from "@/lib/api";
import {
  authCredentials,
  emailFieldError,
  passwordFieldError,
  withoutSecret,
} from "@/lib/credentials";
import { hasAccessToken } from "@/lib/token";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function RegisterPage() {
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
      await registerUser(credentials);
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
      title="Create a staff account"
      intro="Registration creates the user, then signs you in with the same email and password."
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
          autoComplete="new-password"
          value={password}
          error={passwordError}
          onChange={(event) => {
            setPassword(event.target.value);
            setPasswordError("");
          }}
        />
        <SubmitButton pending={pending}>Create account</SubmitButton>
      </form>
      <p className="mt-6 font-sans text-sm">
        Already registered? <TextLink href="/login">Sign in</TextLink>
      </p>
    </AuthCard>
  );
}
