import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import AuthGate from "@/components/auth/AuthGate";
import Navbar from "@/components/layout/Navbar";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "KaddaWeb — Speak English. Fluently. Confidently.",
  description: "AI-powered voice practice — anytime, anywhere.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.className} h-full antialiased`}>
      <body className="min-h-full flex flex-col bg-[#F8F7F4] text-[#1A1A18]">
        <AuthProvider>
          <AuthGate>
            <Navbar />
            <main className="flex-1">{children}</main>
          </AuthGate>
        </AuthProvider>
      </body>
    </html>
  );
}
