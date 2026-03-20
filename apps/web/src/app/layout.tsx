import { Analytics } from "@vercel/analytics/next";
import { SpeedInsights } from "@vercel/speed-insights/next";
import type { Metadata } from "next";
import { Inter, Space_Grotesk } from "next/font/google";

import { MobileBottomNav } from "@/components/mobile-bottom-nav";
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
  description: "Prediction dashboards, historical explorer views, and performance analysis for jam band setlists.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html className="dark" lang="en">
      <body
        className={`${spaceGrotesk.variable} ${inter.variable} font-body antialiased`}
      >
        <div className="min-h-screen">
          <SiteHeader />
          <main className="safe-bottom-content w-full px-6 pt-24 md:px-8 lg:px-10">
            {children}
          </main>
          <MobileBottomNav />
          <Analytics />
          <SpeedInsights />
        </div>
      </body>
    </html>
  );
}
