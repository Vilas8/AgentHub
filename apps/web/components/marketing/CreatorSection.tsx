import Link from "next/link";
import { Button } from "@/components/ui/button";
import { DollarSign, Code2, BarChart3 } from "lucide-react";

const BENEFITS = [
  { icon: <Code2 className="h-5 w-5 text-primary" />, title: "No-code agent builder", description: "Build powerful AI agents using our visual studio — no infrastructure required." },
  { icon: <DollarSign className="h-5 w-5 text-primary" />, title: "Earn 80% revenue share", description: "Keep 80% of every sale. Platform handles payments, billing, and infrastructure." },
  { icon: <BarChart3 className="h-5 w-5 text-primary" />, title: "Analytics dashboard", description: "Track executions, revenue, reviews, and user engagement in real time." },
];

export function CreatorSection() {
  return (
    <section className="py-16">
      <div className="container mx-auto px-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
          <div>
            <h2 className="text-2xl md:text-3xl font-bold mb-4">Build and monetize AI agents</h2>
            <p className="text-muted-foreground mb-8">
              Have domain expertise? Turn it into income. Build AI agents in our Creator Studio and publish them
              to thousands of users on the AgentHub marketplace.
            </p>
            <div className="space-y-5 mb-8">
              {BENEFITS.map((b) => (
                <div key={b.title} className="flex gap-4">
                  <div className="mt-0.5">{b.icon}</div>
                  <div>
                    <p className="font-medium text-sm">{b.title}</p>
                    <p className="text-sm text-muted-foreground">{b.description}</p>
                  </div>
                </div>
              ))}
            </div>
            <Link href="/creator">
              <Button size="lg">Start creating</Button>
            </Link>
          </div>
          <div className="rounded-xl border border-border bg-muted/30 p-8">
            <p className="text-sm font-mono text-muted-foreground mb-4">{"// Creator earnings example"}</p>
            <div className="space-y-3 text-sm font-mono">
              <div className="flex justify-between"><span className="text-muted-foreground">Monthly executions</span><span className="text-foreground font-semibold">2,400</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Price per execution</span><span className="text-foreground font-semibold">$0.50</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Gross revenue</span><span className="text-foreground font-semibold">$1,200</span></div>
              <div className="border-t border-border pt-3 flex justify-between"><span className="text-muted-foreground">Your earnings (80%)</span><span className="text-primary font-bold text-base">$960/month</span></div>
            </div>
            <p className="text-xs text-muted-foreground mt-4">* Illustrative example only. Actual earnings depend on your pricing and user adoption.</p>
          </div>
        </div>
      </div>
    </section>
  );
}
