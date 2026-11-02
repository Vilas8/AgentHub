"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Search, Star, Filter } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { FooterSection } from "@/components/layout/FooterSection";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { Agent, Category, PaginatedResponse } from "@/types";

export default function MarketplacePage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedPricing, setSelectedPricing] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState<"newest" | "popular" | "rating">("popular");

  useEffect(() => {
    // Load categories
    api.get<Category[]>("/categories/")
      .then(setCategories)
      .catch((err) => console.error("Error loading categories:", err));
  }, []);

  useEffect(() => {
    setLoading(true);
    api.get<PaginatedResponse<Agent>>("/marketplace/agents", {
      params: {
        search: search || undefined,
        category_id: selectedCategory || undefined,
        pricing_type: selectedPricing || undefined,
        sort: sortBy,
      },
    })
      .then((res) => {
        setAgents(res.items || []);
      })
      .catch((err) => {
        console.error("Error loading agents:", err);
        setAgents([]);
      })
      .finally(() => setLoading(false));
  }, [search, selectedCategory, selectedPricing, sortBy]);

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navbar />

      <main className="flex-1 container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight mb-2">AI Agent Marketplace</h1>
          <p className="text-muted-foreground">Discover verified AI agents for productivity, research, coding, and business automation.</p>
        </div>

        {/* Search & Filter Bar */}
        <div className="flex flex-col md:flex-row gap-4 items-center justify-between mb-8">
          <div className="relative w-full md:max-w-md">
            <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Search by agent name or capabilities..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>

          <div className="flex flex-wrap gap-2 w-full md:w-auto items-center">
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="popular">Most Popular</option>
              <option value="rating">Highest Rated</option>
              <option value="newest">Newest First</option>
            </select>

            <select
              value={selectedPricing || ""}
              onChange={(e) => setSelectedPricing(e.target.value || null)}
              className="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="">All Pricing</option>
              <option value="free">Free</option>
              <option value="per_execution">Pay per Run</option>
              <option value="subscription">Subscription</option>
            </select>
          </div>
        </div>

        {/* Main Grid: Category Chips + Agents */}
        <div className="flex flex-wrap gap-2 mb-6">
          <Button
            variant={selectedCategory === null ? "default" : "outline"}
            size="sm"
            onClick={() => setSelectedCategory(null)}
          >
            All Categories
          </Button>
          {categories.map((cat) => (
            <Button
              key={cat.id}
              variant={selectedCategory === cat.id ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedCategory(cat.id)}
            >
              {cat.name}
            </Button>
          ))}
        </div>

        {/* Results */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="space-y-3">
                <Skeleton className="h-40 w-full" />
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
              </div>
            ))}
          </div>
        ) : agents.length === 0 ? (
          <div className="text-center py-16 border rounded-lg bg-card">
            <p className="text-lg font-medium">No agents found</p>
            <p className="text-sm text-muted-foreground mt-1">Try adjusting your filters or search terms.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {agents.map((agent) => (
              <Card key={agent.id} className="flex flex-col justify-between hover:shadow-md transition-shadow">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <span className="text-3xl">{agent.icon || "🤖"}</span>
                    <Badge variant={agent.pricing_type === "free" ? "success" : "default"}>
                      {agent.pricing_type === "free" ? "Free" : agent.pricing_type === "per_execution" ? `$${(agent.price_per_execution / 100).toFixed(2)} / run` : "Subscription"}
                    </Badge>
                  </div>
                  <h3 className="font-semibold text-lg mt-3">{agent.name}</h3>
                  <p className="text-sm text-muted-foreground line-clamp-2">{agent.short_description || agent.description}</p>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Star className="h-3.5 w-3.5 text-yellow-500 fill-yellow-500" />
                      {agent.average_rating || "5.0"}
                    </span>
                    <span>{agent.total_executions || 0} runs</span>
                    {agent.is_platform_owned && (
                      <Badge variant="secondary" className="text-[10px]">Official</Badge>
                    )}
                  </div>
                </CardContent>
                <CardFooter className="pt-0">
                  <Link href={`/agents/${agent.id}`} className="w-full">
                    <Button className="w-full" variant="outline">
                      View & Execute
                    </Button>
                  </Link>
                </CardFooter>
              </Card>
            ))}
          </div>
        )}
      </main>

      <FooterSection />
    </div>
  );
}
