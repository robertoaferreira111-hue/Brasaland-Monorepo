import type { Metadata } from "next";
import { Fraunces, Source_Sans_3 } from "next/font/google";
import { OrderBanner } from "@/components/OrderBanner";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import "./globals.css";

const sourceSans = Source_Sans_3({
  variable: "--font-source-sans",
  subsets: ["latin"],
});

const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "Brasaland | The taste of the grill",
    template: "%s | Brasaland",
  },
  description:
    "Since 2008 serving the best grilled meats in Colombia and the United States. 14 locations, one passion for quality and flavor.",
  icons: {
    icon: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${sourceSans.variable} ${fraunces.variable}`}>
      <body className="bg-stone-100 text-stone-950 antialiased">
        <a
          className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:rounded-full focus:bg-orange-900 focus:px-4 focus:py-2 focus:text-orange-50 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-orange-900"
          href="#main"
        >
          Skip to content
        </a>
        <SiteHeader />
        <OrderBanner />
        {children}
        <SiteFooter />
      </body>
    </html>
  );
}
