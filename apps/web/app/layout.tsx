import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: {
    default: "AgentHub — AI Agent Marketplace",
    template: "%s | AgentHub",
  },
  description: "Discover, use, and build AI agents that do real work. AgentHub is your AI-powered app store.",
  keywords: ["AI agents", "marketplace", "automation", "artificial intelligence"],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
