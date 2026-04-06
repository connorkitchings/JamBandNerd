import { Analytics } from "@vercel/analytics/next";
import { SpeedInsights } from "@vercel/speed-insights/next";
import type { Metadata } from "next";

import { MobileBottomNav } from "@/components/mobile-bottom-nav";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://jambandnerd.com"),
  title: "JamBandNerd",
  description:
    "Prediction dashboards, historical analysis views, and performance analysis for jam band setlists.",
  openGraph: {
    siteName: "JamBandNerd",
    images: [{ url: "/logo.png", width: 1200, height: 630, alt: "JamBandNerd" }],
    type: "website",
  },
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
      <body className="font-body antialiased">
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
