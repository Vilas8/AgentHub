"use client";
import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

const FAQS = [
  {
    q: "What is AgentHub?",
    a: "AgentHub is an AI Agent Marketplace where you can discover and use AI agents that automate real tasks — from research and document processing to email drafting and customer support.",
  },
  {
    q: "Do I need to configure AI APIs myself?",
    a: "No. Platform agents use pre-configured AI infrastructure. You provide your task input; the platform handles model selection, execution, and output.",
  },
  {
    q: "How does creator monetization work?",
    a: "Creators publish agents to the marketplace and set their pricing. When customers use paid agents, the creator receives 80% of the revenue. The platform handles all billing and payouts.",
  },
  {
    q: "Is my data secure?",
    a: "Yes. Executions run in isolated workers. Creator configurations and user inputs are treated as untrusted and never mixed across tenants. Full details are in the Privacy Policy.",
  },
  {
    q: "What AI models are available?",
    a: "The platform supports Google Gemini, OpenAI, and Anthropic models via a provider-independent adapter. Creators choose models for their agents; administrators configure available providers.",
  },
  {
    q: "Can I cancel my subscription anytime?",
    a: "Yes. You can cancel your subscription at any time from the billing settings. Access continues until the end of the current billing period.",
  },
];

export function FAQSection() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <section className="py-16">
      <div className="container mx-auto px-4 max-w-2xl">
        <h2 className="text-2xl md:text-3xl font-bold mb-2 text-center">Frequently asked questions</h2>
        <p className="text-muted-foreground text-center mb-10">Have more questions? Contact us.</p>
        <div className="space-y-3">
          {FAQS.map((faq, i) => (
            <div key={i} className="border border-border rounded-lg overflow-hidden">
              <button
                onClick={() => setOpenIndex(openIndex === i ? null : i)}
                className="w-full flex items-center justify-between px-5 py-4 text-sm font-medium text-left hover:bg-muted/50 transition-colors"
                aria-expanded={openIndex === i}
              >
                {faq.q}
                <ChevronDown className={cn("h-4 w-4 transition-transform flex-shrink-0 ml-4", openIndex === i && "rotate-180")} />
              </button>
              {openIndex === i && (
                <div className="px-5 pb-4 text-sm text-muted-foreground border-t border-border pt-3">
                  {faq.a}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
