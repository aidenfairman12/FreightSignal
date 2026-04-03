import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import NavBar from "@/components/Layout/NavBar";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "FreightSignal — Supply Chain Intelligence",
  description:
    "Ask questions about supply chain disruptions. Answers grounded in live logistics news via RAG.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-gray-950 text-white antialiased`}>
        <NavBar />
        {children}
      </body>
    </html>
  );
}
