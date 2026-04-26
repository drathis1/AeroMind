import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AeroMind Ops",
  description:
    "AI operations brain for air cargo — monitor autonomous agents and act when needed.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body>{children}</body>
    </html>
  );
}
