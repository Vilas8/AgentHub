"use client";

import { useState, useEffect, useCallback } from "react";
import { Check, X, Shield, Users, Bot, Activity, AlertCircle } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { FooterSection } from "@/components/layout/FooterSection";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { Agent } from "@/types";

export default function AdminDashboardPage() {
  const [overview, setOverview] = useState({
    total_users: 0,
    total_agents: 0,
    pending_review: 0,
    total_executions: 0,
    failed_executions: 0,
  });
  const [pendingAgents, setPendingAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const loadData = useCallback(() => {
    setLoading(true);
    Promise.all([
      api.get<any>("/admin/overview").catch(() => null),
      api.get<Agent[]>("/admin/agents/pending").catch(() => []),
    ]).then(([stats, pending]) => {
      if (stats) setOverview(stats);
      setPendingAgents(pending);
    }).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleApprove = async (id: string) => {
    try {
      await api.post(`/admin/agents/${id}/approve`, {});
      setActionMessage("Agent approved and listed on marketplace.");
      loadData();
    } catch (e: any) {
      setActionMessage(`Approval failed: ${e.message}`);
    }
  };

  const handleReject = async (id: string) => {
    try {
      await api.post(`/admin/agents/${id}/reject`, {});
      setActionMessage("Agent rejected.");
      loadData();
    } catch (e: any) {
      setActionMessage(`Rejection failed: ${e.message}`);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navbar />

      <main className="flex-1 container mx-auto px-4 py-8">
        <div className="flex items-center gap-3 mb-8">
          <Shield className="h-8 w-8 text-primary" />
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Platform Administration</h1>
            <p className="text-muted-foreground">System telemetry, marketplace governance, and agent moderation queue.</p>
          </div>
        </div>

        {actionMessage && (
          <div className="mb-6 p-4 bg-primary/10 text-primary border border-primary/20 rounded-lg text-sm flex justify-between items-center">
            <span>{actionMessage}</span>
            <button onClick={() => setActionMessage(null)} className="font-bold">&times;</button>
          </div>
        )}

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Total Users</CardDescription>
              <CardTitle className="text-2xl">{overview.total_users}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Total Agents</CardDescription>
              <CardTitle className="text-2xl">{overview.total_agents}</CardTitle>
            </CardHeader>
          </Card>
          <Card className={overview.pending_review > 0 ? "border-yellow-500" : ""}>
            <CardHeader className="pb-2">
              <CardDescription>Pending Review</CardDescription>
              <CardTitle className="text-2xl text-yellow-600 dark:text-yellow-400">{overview.pending_review}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Executions</CardDescription>
              <CardTitle className="text-2xl">{overview.total_executions}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Failed Runs</CardDescription>
              <CardTitle className="text-2xl text-destructive">{overview.failed_executions}</CardTitle>
            </CardHeader>
          </Card>
        </div>

        {/* Pending Moderation Queue */}
        <div className="space-y-4">
          <h2 className="text-xl font-bold flex items-center gap-2">
            Agent Moderation Queue
            {pendingAgents.length > 0 && <Badge variant="warning">{pendingAgents.length}</Badge>}
          </h2>

          {pendingAgents.length === 0 ? (
            <Card className="p-8 text-center text-muted-foreground">
              No agents currently pending moderation review.
            </Card>
          ) : (
            <div className="space-y-4">
              {pendingAgents.map((agent) => (
                <Card key={agent.id} className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-2xl">{agent.icon || "🤖"}</span>
                      <span className="font-semibold text-lg">{agent.name}</span>
                      <Badge variant="outline">{agent.pricing_type}</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">{agent.description}</p>
                    <div className="text-xs text-muted-foreground">Creator ID: {agent.creator_id}</div>
                  </div>

                  <div className="flex gap-2">
                    <Button size="sm" variant="default" onClick={() => handleApprove(agent.id)} className="gap-1">
                      <Check className="h-4 w-4" /> Approve
                    </Button>
                    <Button size="sm" variant="destructive" onClick={() => handleReject(agent.id)} className="gap-1">
                      <X className="h-4 w-4" /> Reject
                    </Button>
                  </div>
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
