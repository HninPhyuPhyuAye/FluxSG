import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./styles.css";

const sans = Geist({ subsets: ["latin"], variable: "--font-sans" });
const mono = Geist_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: "FluxSG — Singapore movement intelligence",
  description: "Air-aware Singapore mobility, live arrivals, haze watch, and guarded forecasts.",
  manifest: "./manifest.webmanifest",
  icons: {
    icon: "./icon.svg",
    apple: "./icon.svg",
  },
  appleWebApp: {
    capable: true,
    title: "FluxSG",
    statusBarStyle: "black-translucent",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${sans.variable} ${mono.variable}`}>{children}</body>
    </html>
  );
}

