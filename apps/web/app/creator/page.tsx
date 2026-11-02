"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Plus, Bot, DollarSign, Activity, Eye, ArrowUpRight } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { FooterSection } from "@/components/layout/FooterSection";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { Agent } from "@/types";

export default function CreatorDashboardPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [balance, setBalance] = useState({ available_minor: 0, pending_minor: 0, total_earned_minor: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get<Agent[]>("/agents/my").catch(() => []),
      api.get<any>("/billing/creator/balance").catch(() => ({ available_minor: 0, pending_minor: 0, total_earned_minor: 0 })),
    ]).then(([myAgents, bal]) => {
      setAgents(myAgents);
      setBalance(bal);
    }).finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navbar />

      <main className="flex-1 container mx-auto px-4 py-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Creator Dashboard</h1>
            <p className="text-muted-foreground">Manage your published agents, track executions, and view your revenue split.</p>
          </div>
          <Link href="/creator/studio">
            <Button className="gap-2">
              <Plus className="h-4 w-4" /> Build New Agent
            </Button>
          </Link>
        </div>

        {/* Financial Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Available Payout</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">${(balance.available_minor / 100).toFixed(2)}</div>
              <p className="text-xs text-muted-foreground mt-1">Ready for settlement</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Pending Earnings</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">${(balance.pending_minor / 100).toFixed(2)}</div>
              <p className="text-xs text-muted-foreground mt-1">From recent executions (80% share)</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Lifetime Earnings</CardTitle>
              <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">${(balance.total_earned_minor / 100).toFixed(2)}</div>
              <p className="text-xs text-muted-foreground mt-1">Total revenue accrued</p>
            </CardContent>
          </Card>
        </div>

        {/* My Agents List */}
        <div className="space-y-4">
          <h2 className="text-xl font-bold">My Agents</h2>
          {agents.length === 0 ? (
            <Card className="text-center py-12">
              <CardContent className="space-y-4">
                <Bot className="h-12 w-12 text-muted-foreground mx-auto" />
                <div>
                  <h3 className="font-semibold text-lg">No agents created yet</h3>
                  <p className="text-sm text-muted-foreground">Start by configuring your first AI agent in the Creator Studio.</p>
                </div>
                <Link href="/creator/studio">
                  <Button>Launch Studio</Button>
                </Link>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {agents.map((agent) => (
                <Card key={agent.id}>
                  <CardHeader>
                    <div className="flex justify-between items-start">
                      <span className="text-2xl">{agent.icon || "🤖"}</span>
                      <Badge variant={agent.status === "approved" ? "success" : agent.status === "pending_review" ? "warning" : "secondary"}>
                        {agent.status}
                      </Badge>
                    </div>
                    <CardTitle className="mt-2">{agent.name}</CardTitle>
                    <CardDescription className="line-clamp-2">{agent.description}</CardDescription>
                  </CardHeader>
                  <CardContent className="text-xs text-muted-foreground flex justify-between border-t pt-4">
                    <span>{agent.total_executions || 0} executions</span>
                    <span>{agent.pricing_type === "free" ? "Free" : `$${(agent.price_per_execution / 100).toFixed(2)} / run`}</span>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </main>

      <FooterSection />
    </div>
  );
}
