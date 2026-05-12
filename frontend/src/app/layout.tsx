import type { Metadata } from "next";
import { Outfit, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import { Web3Provider } from "@/components/Web3Provider";
import ErrorBoundary from "@/components/ErrorBoundary";

const outfit = Outfit({
  variable: "--font-outfit",
  subsets: ["latin"],
});

const ibmPlexMono = IBM_Plex_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: "NodeJackPot | Secure Quadratic Elimination",
  description: "A provably-fair elimination raffle powered by Chainlink VRF 2.5.",
};

import { Toaster } from "sonner";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${outfit.variable} ${ibmPlexMono.variable} antialiased bg-black text-zinc-100 min-h-screen`}>
        <ErrorBoundary>
          <Web3Provider>
            {children}
            <Toaster theme="dark" position="bottom-right" richColors />
          </Web3Provider>
        </ErrorBoundary>
      </body>
    </html>
  );
}
