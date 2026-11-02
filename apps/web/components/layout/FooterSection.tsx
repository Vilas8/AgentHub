import Link from "next/link";
import { Bot } from "lucide-react";

const footerLinks = {
  Product: [
    { label: "Marketplace", href: "/marketplace" },
    { label: "Pricing", href: "/pricing" },
    { label: "Creator Studio", href: "/creator" },
    { label: "API Docs", href: "/docs/api" },
  ],
  Company: [
    { label: "About", href: "/about" },
    { label: "Contact", href: "/contact" },
    { label: "Blog", href: "/blog" },
  ],
  Legal: [
    { label: "Terms of Service", href: "/terms" },
    { label: "Privacy Policy", href: "/privacy" },
  ],
};

export function FooterSection() {
  return (
    <footer className="border-t border-border bg-background">
      <div className="container mx-auto px-4 py-12">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="col-span-2 md:col-span-1">
            <Link href="/" className="flex items-center gap-2 font-bold text-xl mb-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
                <Bot className="h-5 w-5 text-primary-foreground" />
              </div>
              AgentHub
            </Link>
            <p className="text-sm text-muted-foreground">
              The app store for AI agents that do real work.
            </p>
          </div>

          {/* Links */}
          {Object.entries(footerLinks).map(([section, links]) => (
            <div key={section}>
              <h4 className="font-semibold text-sm mb-3">{section}</h4>
              <ul className="space-y-2">
                {links.map((link) => (
                  <li key={link.href}>
                    <Link href={link.href} className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-8 pt-8 border-t border-border flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-sm text-muted-foreground">© {new Date().getFullYear()} AgentHub. All rights reserved.</p>
          <p className="text-xs text-muted-foreground">Built with Next.js, FastAPI, and LangGraph</p>
        </div>
      </div>
    </footer>
  );
}
