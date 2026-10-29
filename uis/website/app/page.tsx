import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  alternates: {
    canonical: "https://brasaland.com/",
  },
};

const restaurantSchema = {
  "@context": "https://schema.org",
  "@type": "Restaurant",
  name: "Brasaland",
  description: "Grilled food restaurant chain in Colombia and the United States",
  url: "https://brasaland.com",
  foundingDate: "2008",
  servesCuisine: "Grilled food, Colombian cuisine",
  priceRange: "$$",
  address: [
    {
      "@type": "PostalAddress",
      addressCountry: "CO",
      addressLocality: "Medellín",
      addressRegion: "Antioquia",
    },
    {
      "@type": "PostalAddress",
      addressCountry: "US",
      addressLocality: "Miami",
      addressRegion: "FL",
    },
  ],
  contactPoint: {
    "@type": "ContactPoint",
    telephone: "+57-4-123-4567",
    contactType: "customer service",
    availableLanguage: "English",
  },
  sameAs: [
    "https://instagram.com/brasaland",
    "https://facebook.com/brasaland",
  ],
};

export default function HomePage() {
  return (
    <>
      <script
        type="application/ld+json"
        id="brasaland-restaurant-schema"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(restaurantSchema) }}
      />
      <main id="main" tabIndex={-1}>
        <section className="mx-auto grid max-w-6xl gap-6 px-4 py-16">
          <h1 className="max-w-3xl font-serif text-4xl leading-tight font-semibold sm:text-6xl">
            The taste of the grill, in every bite
          </h1>
          <p className="max-w-2xl text-lg leading-8 text-stone-700">
            Since 2008 serving the best grilled meats in Colombia and the United
            States. 14 locations, one passion for quality and flavor.
          </p>
          <div>
            <Link
              className="inline-flex min-h-11 items-center rounded-full bg-orange-900 px-5 py-3 text-sm font-semibold text-orange-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-900"
              href="/application"
            >
              Join Brasa Points
            </Link>
          </div>
        </section>

        <section className="mx-auto grid max-w-6xl items-center gap-8 px-4 py-8 md:grid-cols-2">
          <div>
            <h2 className="font-serif text-4xl font-semibold">Our Story</h2>
            <p className="mt-4 leading-8">
              Founded in Medellín in 2008, Brasaland began as a family dream:
              sharing the authentic taste of grilled meat with consistent quality
              and warm service. Today we are 14 restaurants in two countries, but
              we maintain the same recipe for success: fresh products,
              traditional techniques, and passion for every dish we serve.
            </p>
          </div>
          {/* eslint-disable-next-line @next/next/no-img-element -- SVG story art from the static site */}
          <img
            className="h-auto w-full rounded-3xl border border-stone-300"
            src="/story.svg"
            width={800}
            height={640}
            alt="Charcoal grill with glowing embers, the way Brasaland cooks its meats."
          />
        </section>

        <section className="mx-auto max-w-6xl px-4 py-8">
          <h2 className="font-serif text-4xl font-semibold">
            What Makes Us Unique
          </h2>
          <div className="mt-8 grid gap-4 md:grid-cols-3">
            <article className="rounded-3xl border border-stone-300 bg-white p-6">
              <h3 className="font-serif text-2xl font-semibold">
                Consistent Quality
              </h3>
              <ul className="mt-4 list-disc space-y-2 pl-5 text-stone-700">
                <li>Same recipes and standards in all locations</li>
                <li>Fresh ingredients selected daily</li>
              </ul>
            </article>
            <article className="rounded-3xl border border-stone-300 bg-white p-6">
              <h3 className="font-serif text-2xl font-semibold">
                Warm Experience
              </h3>
              <ul className="mt-4 list-disc space-y-2 pl-5 text-stone-700">
                <li>Friendly and attentive service</li>
                <li>Family atmosphere on every visit</li>
              </ul>
            </article>
            <article className="rounded-3xl border border-stone-300 bg-white p-6">
              <h3 className="font-serif text-2xl font-semibold">Speed</h3>
              <ul className="mt-4 list-disc space-y-2 pl-5 text-stone-700">
                <li>Your food ready in minutes</li>
                <li>Without sacrificing flavor or quality</li>
              </ul>
            </article>
          </div>
        </section>

        <section id="locations" className="mx-auto max-w-6xl px-4 py-8">
          <h2 className="font-serif text-4xl font-semibold">Our Locations</h2>
          <div className="mt-8 grid gap-4 md:grid-cols-2">
            <article className="rounded-3xl border border-stone-300 bg-white p-6">
              <h3 className="font-serif text-2xl font-semibold">Colombia</h3>
              <ul className="mt-4 space-y-2">
                <li>10 restaurants in Medellín, Bogotá and Cali</li>
                <li>Hours: Mon-Sun 11:00 AM - 10:00 PM</li>
              </ul>
            </article>
            <article className="rounded-3xl border border-stone-300 bg-white p-6">
              <h3 className="font-serif text-2xl font-semibold">
                United States (Florida)
              </h3>
              <ul className="mt-4 space-y-2">
                <li>4 restaurants in Miami and Orlando</li>
                <li>Hours: Mon-Sun 11:00 AM - 10:00 PM</li>
              </ul>
            </article>
          </div>
        </section>

        <section id="menu" className="mx-auto max-w-6xl px-4 py-8">
          <h2 className="font-serif text-4xl font-semibold">Menu</h2>
          <p className="mt-4 max-w-2xl leading-8">
            Grilled food and Colombian cuisine, prepared with the same recipes
            and fresh ingredients at every location.
          </p>
          <p className="mt-4 max-w-2xl rounded-3xl border border-stone-300 bg-white p-5">
            Want to place an order? Call your favorite location or visit us
            directly. Online ordering coming soon!
          </p>
        </section>

        <section id="brasa-points" className="bg-stone-950 text-stone-50">
          <div className="mx-auto grid max-w-6xl gap-6 px-4 py-16 md:grid-cols-[1.4fr_auto] md:items-center">
            <div>
              <h2 className="font-serif text-4xl font-semibold">Brasa Points</h2>
              <ul className="mt-6 list-disc space-y-2 pl-5">
                <li>Earn points with every visit</li>
                <li>Accumulate 1 point for every $10,000 COP or $5 USD</li>
                <li>Redeem your points for discounts and free dishes</li>
                <li>Exclusive offers for members</li>
                <li>100% digital registration - no more paper cards!</li>
              </ul>
            </div>
            <Link
              className="inline-flex min-h-11 items-center justify-center rounded-full bg-orange-900 px-5 py-3 text-sm font-semibold text-orange-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-50"
              href="/application"
            >
              Join Brasa Points
            </Link>
          </div>
        </section>

        <section id="contact" className="mx-auto max-w-6xl px-4 py-16">
          <h2 className="font-serif text-4xl font-semibold">Contact</h2>
          <address className="mt-6 space-y-2 not-italic">
            <p>
              Email:{" "}
              <a
                className="underline underline-offset-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-900"
                href="mailto:hello@brasaland.com"
              >
                hello@brasaland.com
              </a>
            </p>
            <p>
              Colombia:{" "}
              <a
                className="underline underline-offset-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-900"
                href="tel:+5741234567"
              >
                +57 4 123 4567
              </a>
            </p>
            <p>
              Florida:{" "}
              <a
                className="underline underline-offset-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-900"
                href="tel:+13051234567"
              >
                +1 305 123 4567
              </a>
            </p>
          </address>
        </section>
      </main>
    </>
  );
}
