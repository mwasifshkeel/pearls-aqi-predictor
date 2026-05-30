import type { Metadata } from "next";
import { Space_Grotesk, IBM_Plex_Serif } from "next/font/google";
import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-sans",
});

const plexSerif = IBM_Plex_Serif({
  subsets: ["latin"],
  weight: ["400", "600"],
  variable: "--font-serif",
});

export const metadata: Metadata = {
  title: "Rawalpindi AQI Forecast",
  description: "Serverless AQI forecasting dashboard for Rawalpindi.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${spaceGrotesk.variable} ${plexSerif.variable}`}>
      <body>
        <main>{children}</main>
      </body>
    </html>
  );
}
