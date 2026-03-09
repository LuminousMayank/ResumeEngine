import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Caarya AI Job Fit Engine",
  description: "Upload your resume and get AI-powered job fit recommendations from Caarya.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
