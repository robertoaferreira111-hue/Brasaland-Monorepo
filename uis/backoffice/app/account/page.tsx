"use client";

import { FormError, SubmitButton, TextField } from "@/components/AuthCard";
import {
  getMe,
  logout,
  SessionExpiredError,
  toErrorMessage,
  updateProfile,
} from "@/lib/api";
import {
  addressFieldError,
  nameFieldError,
  phoneFieldError,
  profileUpdatePayload,
} from "@/lib/profile";
import { useEffect, useState } from "react";

export default function AccountPage() {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [nameError, setNameError] = useState("");
  const [phoneError, setPhoneError] = useState("");
  const [addressError, setAddressError] = useState("");
  const [loadError, setLoadError] = useState("");
  const [saveError, setSaveError] = useState("");
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    getMe()
      .then((profile) => {
        if (!active) {
          return;
        }
        setEmail(profile.email);
        setName(profile.name);
        setPhone(profile.phone);
        setAddress(profile.address);
        setLoadError("");
      })
      .catch((caught) => {
        if (!active || caught instanceof SessionExpiredError) {
          return;
        }
        setLoadError(toErrorMessage(caught));
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [reloadKey]);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) {
      return;
    }
    const nextNameError = nameFieldError(name);
    const nextPhoneError = phoneFieldError(phone);
    const nextAddressError = addressFieldError(address);
    setNameError(nextNameError);
    setPhoneError(nextPhoneError);
    setAddressError(nextAddressError);
    setSaveError("");
    setSaved(false);
    if (nextNameError || nextPhoneError || nextAddressError) {
      const focusId = nextNameError
        ? "name"
        : nextPhoneError
          ? "phone"
          : "address";
      document.getElementById(focusId)?.focus();
      return;
    }
    const payload = profileUpdatePayload({ name, phone, address });
    if (!payload) {
      return;
    }
    setPending(true);
    try {
      const profile = await updateProfile(payload, email);
      setName(profile.name);
      setPhone(profile.phone);
      setAddress(profile.address);
      setEmail(profile.email);
      setSaved(true);
    } catch (caught) {
      if (!(caught instanceof SessionExpiredError)) {
        setSaveError(toErrorMessage(caught));
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <main
      id="main"
      tabIndex={-1}
      className="mx-auto flex w-full max-w-md flex-1 flex-col px-4 py-12"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold">Your account</h1>
          <p className="mt-2 text-stone-700">
            Email comes from your user. Name, phone, and address come from your
            profile.
          </p>
        </div>
        <button
          className="min-h-11 shrink-0 rounded-full border border-stone-400 px-4 py-2 font-sans text-sm font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-900"
          type="button"
          onClick={() => {
            void logout();
          }}
        >
          Log out
        </button>
      </div>

      {loading ? (
        <p className="mt-8" role="status">
          Loading profile…
        </p>
      ) : null}

      {loadError ? (
        <div className="mt-8 grid gap-3">
          <FormError message={loadError} />
          <button
            className="min-h-11 w-fit rounded-full border border-stone-400 px-4 py-2 font-sans text-sm font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-900"
            type="button"
            onClick={() => {
              setLoading(true);
              setLoadError("");
              setSaved(false);
              setReloadKey((value) => value + 1);
            }}
          >
            Try again
          </button>
        </div>
      ) : null}

      {!loading && !loadError ? (
        <form className="mt-8 grid gap-4" noValidate onSubmit={onSubmit}>
          <TextField
            id="email"
            label="Email"
            type="email"
            name="email"
            value={email}
            readOnly
            disabled
          />
          <FormError message={saveError} />
          {saved ? (
            <p
              className="rounded-lg border border-green-300 bg-green-50 px-3 py-2 font-sans text-sm text-green-900"
              role="status"
            >
              Profile saved.
            </p>
          ) : null}
          <TextField
            id="name"
            label="Name"
            type="text"
            name="name"
            autoComplete="name"
            value={name}
            error={nameError}
            onChange={(event) => {
              setName(event.target.value);
              setNameError("");
              setSaved(false);
            }}
          />
          <TextField
            id="phone"
            label="Phone"
            type="tel"
            name="phone"
            autoComplete="tel"
            value={phone}
            error={phoneError}
            onChange={(event) => {
              setPhone(event.target.value);
              setPhoneError("");
              setSaved(false);
            }}
          />
          <TextField
            id="address"
            label="Address"
            type="text"
            name="address"
            autoComplete="street-address"
            value={address}
            error={addressError}
            onChange={(event) => {
              setAddress(event.target.value);
              setAddressError("");
              setSaved(false);
            }}
          />
          <SubmitButton pending={pending}>Save profile</SubmitButton>
        </form>
      ) : null}
    </main>
  );
}
