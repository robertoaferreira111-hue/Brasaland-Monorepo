"use client";

import { useEffect, useRef, useState } from "react";
import {
  CITIES,
  DIETARY_OPTIONS,
  LOCATIONS,
  SOURCES,
  emptyValues,
  messageFor,
  validateAll,
  type BrasaPointsValues,
  type FieldId,
} from "@/lib/brasaPoints";

const inputClass =
  "mt-1 min-h-11 w-full rounded-2xl border border-stone-400 bg-white px-3 py-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-900";

export function BrasaPointsForm() {
  const [values, setValues] = useState<BrasaPointsValues>(emptyValues);
  const [errors, setErrors] = useState<Partial<Record<FieldId, string>>>({});
  const [submitted, setSubmitted] = useState(false);
  const successRef = useRef<HTMLDivElement>(null);
  const nameRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (submitted) {
      successRef.current?.focus();
    }
  }, [submitted]);

  function setField<K extends keyof BrasaPointsValues>(
    key: K,
    value: BrasaPointsValues[K],
  ) {
    setValues((current) => {
      const next = { ...current, [key]: value };
      if (key === "country") {
        next.city = "";
        next["favorite-location"] = "";
      }
      if (key === "city") {
        next["favorite-location"] = "";
      }
      return next;
    });
  }

  function liveValidate(id: FieldId, nextValues: BrasaPointsValues) {
    const message = messageFor(id, nextValues);
    setErrors((current) => {
      const copy = { ...current };
      if (message) copy[id] = message;
      else delete copy[id];
      return copy;
    });
  }

  function onCountryChange(country: string) {
    const hadCity = Boolean(values.city);
    const shouldCheckPhone =
      Boolean(values.phone.trim()) || Boolean(errors.phone);
    const next: BrasaPointsValues = {
      ...values,
      country,
      city: "",
      "favorite-location": "",
    };
    setValues(next);
    liveValidate("country", next);
    if (hadCity) liveValidate("city", next);
    if (shouldCheckPhone) liveValidate("phone", next);
  }

  function onCityChange(city: string) {
    const next: BrasaPointsValues = {
      ...values,
      city,
      "favorite-location": "",
    };
    setValues(next);
    liveValidate("city", next);
  }

  function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    const result = validateAll(values);
    setErrors(result.errors);
    if (result.firstInvalid) {
      setSubmitted(false);
      const node = document.getElementById(result.firstInvalid);
      node?.focus();
      return;
    }
    setSubmitted(true);
  }

  function clearForm() {
    setValues(emptyValues());
    setErrors({});
    setSubmitted(false);
    queueMicrotask(() => nameRef.current?.focus());
  }

  function toggleDietary(option: string, checked: boolean) {
    setValues((current) => {
      const dietary = checked
        ? [...current.dietary, option]
        : current.dietary.filter((item) => item !== option);
      return { ...current, dietary };
    });
  }

  const cities = CITIES[values.country] || [];
  const locations = LOCATIONS[values.city] || [];

  return (
    <>
      {submitted ? (
        <div
          id="success"
          ref={successRef}
          className="mt-8 rounded-3xl border border-stone-300 bg-white p-6"
          role="status"
          tabIndex={-1}
        >
          <h2 className="font-serif text-3xl font-semibold">
            Welcome to Brasa Points!
          </h2>
          <p className="mt-3 leading-7">
            Your registration was successful. You will receive a confirmation
            email in the next few minutes with your account details and how to
            start earning points.
          </p>
          <p className="mt-3 leading-7">
            You can now enjoy your benefits at any of our 14 locations!
          </p>
        </div>
      ) : (
        <form
          id="loyalty-form"
          className="mt-8 space-y-5"
          noValidate
          onSubmit={onSubmit}
        >
          <div>
            <label className="block text-sm font-medium" htmlFor="full-name">
              Full name
            </label>
            <input
              ref={nameRef}
              className={inputClass}
              id="full-name"
              name="full-name"
              type="text"
              autoComplete="name"
              required
              value={values["full-name"]}
              aria-invalid={errors["full-name"] ? true : undefined}
              aria-describedby={
                errors["full-name"] ? "full-name-error" : undefined
              }
              onChange={(event) => {
                const next = { ...values, "full-name": event.target.value };
                setValues(next);
                liveValidate("full-name", next);
              }}
              onBlur={() => liveValidate("full-name", values)}
            />
            <p
              className="mt-1 text-sm text-orange-900"
              id="full-name-error"
              aria-live="polite"
            >
              {errors["full-name"] || ""}
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium" htmlFor="email">
              Email
            </label>
            <input
              className={inputClass}
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              required
              value={values.email}
              aria-invalid={errors.email ? true : undefined}
              aria-describedby={errors.email ? "email-error" : undefined}
              onChange={(event) => {
                const next = { ...values, email: event.target.value };
                setValues(next);
                liveValidate("email", next);
              }}
              onBlur={() => liveValidate("email", values)}
            />
            <p
              className="mt-1 text-sm text-orange-900"
              id="email-error"
              aria-live="polite"
            >
              {errors.email || ""}
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium" htmlFor="phone">
              Phone
            </label>
            <input
              className={inputClass}
              id="phone"
              name="phone"
              type="tel"
              autoComplete="tel"
              placeholder="+57 300 123 4567"
              required
              value={values.phone}
              aria-invalid={errors.phone ? true : undefined}
              aria-describedby={errors.phone ? "phone-error" : undefined}
              onChange={(event) => {
                const next = { ...values, phone: event.target.value };
                setValues(next);
                liveValidate("phone", next);
              }}
              onBlur={() => liveValidate("phone", values)}
            />
            <p
              className="mt-1 text-sm text-orange-900"
              id="phone-error"
              aria-live="polite"
            >
              {errors.phone || ""}
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium" htmlFor="country">
              Country
            </label>
            <select
              className={inputClass}
              id="country"
              name="country"
              required
              value={values.country}
              aria-invalid={errors.country ? true : undefined}
              aria-describedby={errors.country ? "country-error" : undefined}
              onChange={(event) => onCountryChange(event.target.value)}
              onBlur={() => liveValidate("country", values)}
            >
              <option value="">Select your country</option>
              <option>Colombia</option>
              <option>United States</option>
            </select>
            <p
              className="mt-1 text-sm text-orange-900"
              id="country-error"
              aria-live="polite"
            >
              {errors.country || ""}
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium" htmlFor="city">
              City
            </label>
            <select
              className={inputClass}
              id="city"
              name="city"
              required
              value={values.city}
              aria-invalid={errors.city ? true : undefined}
              aria-describedby={errors.city ? "city-error" : undefined}
              onChange={(event) => onCityChange(event.target.value)}
              onBlur={() => liveValidate("city", values)}
            >
              <option value="">Select your city</option>
              {cities.map((city) => (
                <option key={city}>{city}</option>
              ))}
            </select>
            <p
              className="mt-1 text-sm text-orange-900"
              id="city-error"
              aria-live="polite"
            >
              {errors.city || ""}
            </p>
          </div>

          <div>
            <label
              className="block text-sm font-medium"
              htmlFor="favorite-location"
            >
              Favorite Brasaland location
            </label>
            <select
              className={inputClass}
              id="favorite-location"
              name="favorite-location"
              value={values["favorite-location"]}
              onChange={(event) =>
                setField("favorite-location", event.target.value)
              }
            >
              <option value="">Select a location (optional)</option>
              {locations.map((location) => (
                <option key={location}>{location}</option>
              ))}
            </select>
          </div>

          <fieldset className="rounded-3xl border border-stone-300 bg-white p-4">
            <legend className="px-1 text-sm font-medium">
              Dietary preferences
            </legend>
            <p className="text-sm text-stone-700" id="dietary-hint">
              Optional. Choose any that apply.
            </p>
            <div className="mt-3 grid gap-2">
              {DIETARY_OPTIONS.map((option) => {
                const id = `diet-${option.toLowerCase().replace(/\s+/g, "-")}`;
                return (
                  <label
                    key={option}
                    className="flex min-h-11 items-center gap-3"
                    htmlFor={id}
                  >
                    <input
                      className="size-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-900"
                      id={id}
                      name="dietary"
                      type="checkbox"
                      value={option}
                      checked={values.dietary.includes(option)}
                      onChange={(event) =>
                        toggleDietary(option, event.target.checked)
                      }
                    />{" "}
                    {option}
                  </label>
                );
              })}
            </div>
          </fieldset>

          <div>
            <label className="block text-sm font-medium" htmlFor="source">
              How did you find us?
            </label>
            <select
              className={inputClass}
              id="source"
              name="source"
              required
              value={values.source}
              aria-invalid={errors.source ? true : undefined}
              aria-describedby={errors.source ? "source-error" : undefined}
              onChange={(event) => {
                const next = { ...values, source: event.target.value };
                setValues(next);
                liveValidate("source", next);
              }}
              onBlur={() => liveValidate("source", values)}
            >
              <option value="">Select an option</option>
              {SOURCES.map((source) => (
                <option key={source}>{source}</option>
              ))}
            </select>
            <p
              className="mt-1 text-sm text-orange-900"
              id="source-error"
              aria-live="polite"
            >
              {errors.source || ""}
            </p>
          </div>

          <div>
            <label
              className="block text-sm font-medium"
              htmlFor="date-of-birth"
            >
              Date of birth
            </label>
            <input
              className={inputClass}
              id="date-of-birth"
              name="date-of-birth"
              type="date"
              autoComplete="bday"
              required
              value={values["date-of-birth"]}
              aria-invalid={errors["date-of-birth"] ? true : undefined}
              aria-describedby={
                errors["date-of-birth"] ? "date-of-birth-error" : undefined
              }
              onChange={(event) => {
                const next = {
                  ...values,
                  "date-of-birth": event.target.value,
                };
                setValues(next);
                liveValidate("date-of-birth", next);
              }}
              onBlur={() => liveValidate("date-of-birth", values)}
            />
            <p
              className="mt-1 text-sm text-orange-900"
              id="date-of-birth-error"
              aria-live="polite"
            >
              {errors["date-of-birth"] || ""}
            </p>
          </div>

          <div>
            <label
              className="flex min-h-11 items-start gap-3"
              htmlFor="accept-terms"
            >
              <input
                className="mt-1 size-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-900"
                id="accept-terms"
                name="accept-terms"
                type="checkbox"
                required
                checked={values["accept-terms"]}
                aria-invalid={errors["accept-terms"] ? true : undefined}
                aria-describedby={
                  errors["accept-terms"] ? "accept-terms-error" : undefined
                }
                onChange={(event) => {
                  const next = {
                    ...values,
                    "accept-terms": event.target.checked,
                  };
                  setValues(next);
                  liveValidate("accept-terms", next);
                }}
              />
              <span>I accept program terms</span>
            </label>
            <p
              className="mt-1 text-sm text-orange-900"
              id="accept-terms-error"
              aria-live="polite"
            >
              {errors["accept-terms"] || ""}
            </p>
          </div>

          <div>
            <label className="flex min-h-11 items-start gap-3" htmlFor="offers">
              <input
                className="mt-1 size-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-900"
                id="offers"
                name="offers"
                type="checkbox"
                checked={values.offers}
                onChange={(event) => setField("offers", event.target.checked)}
              />
              <span>I want to receive offers via email</span>
            </label>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              className="inline-flex min-h-11 items-center rounded-full bg-orange-900 px-5 py-3 text-sm font-semibold text-orange-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-900"
              type="submit"
            >
              Join Brasa Points
            </button>
          </div>
        </form>
      )}

      <button
        className="mt-3 inline-flex min-h-11 items-center rounded-full border border-stone-400 bg-white px-5 py-3 text-sm font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-900"
        id="clear-form"
        type="button"
        onClick={clearForm}
      >
        Clear
      </button>
    </>
  );
}
