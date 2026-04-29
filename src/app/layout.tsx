import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "bsopt | Options Research Platform",
  description: "Advanced Black-Scholes Numerical Methods & MLOps Research System",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} min-h-screen bg-background text-foreground selection:bg-accent/30`}>
        {children}
      </body>
    </html>
  );
}
