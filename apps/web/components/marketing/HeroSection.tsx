import Link from "next/link";
import { ArrowRight, Bot, Zap, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";

export function HeroSection() {
  return (
    <section className="relative overflow-hidden py-20 md:py-32">
      <div className="container mx-auto px-4 text-center">
        {/* Badge */}
        <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-4 py-1.5 text-sm text-primary mb-8">
          <Zap className="h-3.5 w-3.5" />
          AI agents that do real work
        </div>

        {/* Headline */}
        <h1 className="text-4xl md:text-6xl font-bold tracking-tight mb-6 max-w-4xl mx-auto">
          The App Store for{" "}
          <span className="text-primary">AI Agents</span>
        </h1>

        <p className="text-lg md:text-xl text-muted-foreground mb-10 max-w-2xl mx-auto">
          Discover, use, and build AI agents that automate real tasks. From research to customer support,
          find the right agent for your workflow — or create your own.
        </p>

        {/* Search bar placeholder */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center mb-12 max-w-lg mx-auto">
          <input
            type="text"
            placeholder="Search agents (e.g. 'research', 'email', 'documents')"
            className="flex h-12 w-full rounded-md border border-input bg-background px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
          <Link href="/marketplace">
            <Button size="lg" className="sm:w-auto w-full">
              <ArrowRight className="h-4 w-4 mr-1" />
              Explore
            </Button>
          </Link>
        </div>

        {/* Trust signals */}
        <div className="flex flex-wrap justify-center gap-6 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <Bot className="h-4 w-4 text-primary" />
            5 platform agents available
          </div>
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-primary" />
            Secure sandboxed execution
          </div>
          <div className="flex items-center gap-2">
            <Zap className="h-4 w-4 text-primary" />
            Powered by leading AI models
          </div>
        </div>
      </div>
    </section>
  );
}
