import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Check } from "lucide-react";

const PLANS = [
  {
    name: "Free",
    price: "$0",
    description: "Try platform agents at no cost",
    badge: null,
    features: ["Access to free agents", "10 executions/month", "Execution history", "Community support"],
    cta: "Get started free",
    href: "/auth/register",
    variant: "outline" as const,
  },
  {
    name: "Pro",
    price: "$19",
    period: "/month",
    description: "For individuals and professionals",
    badge: "Most popular",
    features: ["All free features", "200 executions/month", "Priority execution", "File uploads up to 50MB", "Email support"],
    cta: "Start Pro",
    href: "/auth/register",
    variant: "default" as const,
  },
  {
    name: "Business",
    price: "$79",
    period: "/month",
    description: "For teams and businesses",
    badge: null,
    features: ["All Pro features", "1,000 executions/month", "Team seats (5)", "Custom agents", "API access", "Priority support"],
    cta: "Start Business",
    href: "/auth/register",
    variant: "outline" as const,
  },
];

export function PricingPreview() {
  return (
    <section className="py-16 bg-muted/30">
      <div className="container mx-auto px-4">
        <h2 className="text-2xl md:text-3xl font-bold mb-2 text-center">Simple, transparent pricing</h2>
        <p className="text-muted-foreground text-center mb-12">Start free. Upgrade as you grow.</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
          {PLANS.map((plan) => (
            <Card key={plan.name} className={plan.badge ? "border-primary shadow-md" : ""}>
              <CardHeader className="pb-4">
                <div className="flex items-center justify-between mb-1">
                  <h3 className="font-bold text-lg">{plan.name}</h3>
                  {plan.badge && <Badge>{plan.badge}</Badge>}
                </div>
                <div className="flex items-baseline gap-1">
                  <span className="text-3xl font-bold">{plan.price}</span>
                  {plan.period && <span className="text-muted-foreground text-sm">{plan.period}</span>}
                </div>
                <p className="text-sm text-muted-foreground">{plan.description}</p>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 mb-6">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-center gap-2 text-sm">
                      <Check className="h-4 w-4 text-primary flex-shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
                <Link href={plan.href}>
                  <Button variant={plan.variant} className="w-full">{plan.cta}</Button>
                </Link>
              </CardContent>
            </Card>
          ))}
        </div>
        <p className="text-xs text-muted-foreground text-center mt-6">
          * Pricing shown is illustrative. Final pricing will be confirmed at launch.
        </p>
      </div>
    </section>
  );
}
