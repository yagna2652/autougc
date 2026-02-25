import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AutoUGC",
  description: "Reference-video-to-UGC pipeline",
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
