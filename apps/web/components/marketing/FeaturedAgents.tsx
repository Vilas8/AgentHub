import Link from "next/link";
import { ArrowRight, Star } from "lucide-react";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const SAMPLE_AGENTS = [
  {
    id: "research-agent",
    name: "Research Agent",
    description: "Research any topic and produce structured reports with source references.",
    category: "Research",
    pricing_type: "free",
    rating: 4.8,
    executions: 1240,
    icon: "🔍",
  },
  {
    id: "document-agent",
    name: "Document Agent",
    description: "Upload PDFs, DOCX, or CSV files and get summaries, Q&A, and structured output.",
    category: "Document Processing",
    pricing_type: "free",
    rating: 4.7,
    executions: 980,
    icon: "📄",
  },
  {
    id: "email-assistant",
    name: "Email Assistant",
    description: "Draft, summarize, categorize, and reply to emails with AI assistance.",
    category: "Email",
    pricing_type: "free",
    rating: 4.6,
    executions: 2100,
    icon: "✉️",
  },
];

export function FeaturedAgents() {
  return (
    <section className="py-16 bg-muted/30">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl md:text-3xl font-bold mb-2">Featured Agents</h2>
            <p className="text-muted-foreground">Platform-built agents ready to use</p>
          </div>
          <Link href="/marketplace">
            <Button variant="outline">
              View all <ArrowRight className="h-4 w-4 ml-1" />
            </Button>
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {SAMPLE_AGENTS.map((agent) => (
            <Card key={agent.id} className="group hover:shadow-md transition-shadow">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="text-3xl mb-2">{agent.icon}</div>
                  <Badge variant={agent.pricing_type === "free" ? "success" : "default"}>
                    {agent.pricing_type === "free" ? "Free" : "Paid"}
                  </Badge>
                </div>
                <h3 className="font-semibold text-lg group-hover:text-primary transition-colors">
                  {agent.name}
                </h3>
                <p className="text-sm text-muted-foreground line-clamp-2">{agent.description}</p>
              </CardHeader>
              <CardContent className="pb-3">
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <Star className="h-3.5 w-3.5 text-yellow-500 fill-yellow-500" />
                    {agent.rating}
                  </div>
                  <span>{agent.executions.toLocaleString()} runs</span>
                  <Badge variant="outline" className="text-xs">{agent.category}</Badge>
                </div>
              </CardContent>
              <CardFooter>
                <Link href={`/agents/${agent.id}`} className="w-full">
                  <Button variant="outline" className="w-full">Try agent</Button>
                </Link>
              </CardFooter>
            </Card>
          ))}
        </div>
        <p className="text-xs text-muted-foreground mt-4 text-center">
          * Ratings and run counts are sample data. Live statistics will display after users interact with agents.
        </p>
      </div>
    </section>
  );
}
