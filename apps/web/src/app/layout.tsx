import type { Metadata } from "next";
import { Inter, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "./app-providers";

// Assigned to the same --font-geist-sans slot design_system/tokens.css
// already reads as --font-sans's first choice (Section 16: "a clean
// interface typeface such as Inter" — communicates precision and
// institutional trust better than a generic geometric sans for this
// product). Geist Mono stays for amounts, dates, and audit values.
const interSans = Inter({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Relief",
  description:
    "Relief turns a financial resilience model into usable financial infrastructure — a live cash flow timeline, valid interventions, and an auditable approval workflow.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${interSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
