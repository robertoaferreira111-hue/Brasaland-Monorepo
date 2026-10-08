import Link from "next/link";

const fieldClassName =
  "min-h-11 w-full rounded-lg border border-stone-400 bg-white px-3 py-2 font-sans text-base text-stone-950 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-900";

export function AuthCard({
  title,
  intro,
  children,
}: {
  title: string;
  intro: string;
  children: React.ReactNode;
}) {
  return (
    <main
      id="main"
      tabIndex={-1}
      className="mx-auto flex w-full max-w-md flex-1 flex-col px-4 py-12"
    >
      <h1 className="text-3xl font-semibold">{title}</h1>
      <p className="mt-2 text-stone-700">{intro}</p>
      <div className="mt-8">{children}</div>
    </main>
  );
}

export function TextField({
  id,
  label,
  error,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement> & {
  id: string;
  label: string;
  error?: string;
}) {
  return (
    <div className="grid gap-1">
      <label className="text-sm font-medium" htmlFor={id}>
        {label}
      </label>
      <input
        id={id}
        className={fieldClassName}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : undefined}
        {...props}
      />
      {error ? (
        <p id={`${id}-error`} className="text-sm text-red-800" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

export function FormError({ message }: { message: string }) {
  if (!message) {
    return null;
  }
  return (
    <p className="rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-900" role="alert">
      {message}
    </p>
  );
}

export function SubmitButton({
  pending,
  children,
}: {
  pending: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      className="min-h-11 rounded-full bg-orange-900 px-5 py-2 font-sans text-sm font-semibold text-orange-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-900 disabled:opacity-60"
      type="submit"
      disabled={pending}
    >
      {pending ? "Please wait…" : children}
    </button>
  );
}

export function TextLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      className="font-sans text-sm font-medium text-orange-900 underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-900"
      href={href}
    >
      {children}
    </Link>
  );
}

export { fieldClassName };
