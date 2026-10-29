import type { Metadata } from "next";
import { BrasaPointsForm } from "@/components/BrasaPointsForm";

export const metadata: Metadata = {
  title: "Join Brasa Points",
  description:
    "Register for Brasa Points, the Brasaland loyalty program. Earn points at 14 locations in Colombia and Florida. Customers must be 18 or older.",
  alternates: {
    canonical: "https://brasaland.com/application",
  },
};

export default function ApplicationPage() {
  return (
    <main id="main" className="mx-auto max-w-3xl px-4 py-12" tabIndex={-1}>
      <h1 className="font-serif text-4xl font-semibold sm:text-5xl">
        Join Brasa Points
      </h1>
      <p className="mt-4 leading-7 text-stone-700">
        Customers must be 18 or older. This form registers you for the loyalty
        program. It does not place an order or a reservation.
      </p>
      <ul className="mt-4 list-disc space-y-2 pl-5">
        <li>Earn points with every visit</li>
        <li>Accumulate 1 point for every $10,000 COP or $5 USD</li>
        <li>Redeem your points for discounts and free dishes</li>
        <li>Exclusive offers for members</li>
        <li>100% digital registration - no more paper cards!</li>
      </ul>
      <BrasaPointsForm />
    </main>
  );
}
