import { SessionRedirect } from "@/components/SessionRedirect";
import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Brasaland staff",
  description: "Staff sign-in and account for Brasaland.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex min-h-full flex-col bg-stone-100 font-serif text-stone-950">
        <a
          className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:rounded-full focus:bg-orange-900 focus:px-4 focus:py-2 focus:text-orange-50 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-orange-900"
          href="#main"
        >
          Skip to content
        </a>
        <SessionRedirect />
        <header className="border-b border-stone-300 bg-stone-100">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3">
            <Link
              className="text-2xl font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-900"
              href="/"
            >
              Brasaland
            </Link>
            <p className="font-sans text-sm text-stone-700">Staff</p>
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}
