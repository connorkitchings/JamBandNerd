import { Analytics } from "@vercel/analytics/next";
import { SpeedInsights } from "@vercel/speed-insights/next";
import type { Metadata } from "next";
import { Inter, Space_Grotesk } from "next/font/google";

import { MobileBottomNav } from "@/components/mobile-bottom-nav";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
});

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "JamBandNerd",
  description: "Prediction dashboards, historical analysis views, and performance analysis for jam band setlists.",
};

export const viewport = {
  themeColor: "#111316",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html className="dark" lang="en">
      <body
        className={`${spaceGrotesk.variable} ${inter.variable} font-body antialiased`}
      >
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-[100] focus:rounded-lg focus:bg-surface-container-high focus:px-4 focus:py-2 focus:text-sm focus:text-primary focus:ring-2 focus:ring-primary"
        >
          Skip to main content
        </a>
        <div className="flex min-h-screen flex-col">
          <SiteHeader />
          <main
            id="main-content"
            className="safe-bottom-content w-full flex-1 px-6 pt-24 md:px-8 lg:px-10"
          >
            {children}
          </main>
          <SiteFooter />
          <MobileBottomNav />
          <Analytics />
          <SpeedInsights />
        </div>
      </body>
    </html>
  );
}
