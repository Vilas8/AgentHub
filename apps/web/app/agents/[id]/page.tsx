"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Play, Star, Shield, ArrowLeft, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { FooterSection } from "@/components/layout/FooterSection";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { Agent, Execution } from "@/types";

export default function AgentDetailPage() {
  const params = useParams();
  const agentId = params.id as string;

  const [agent, setAgent] = useState<Agent | null>(null);
  const [loading, setLoading] = useState(true);
  const [inputQuery, setInputQuery] = useState("");
  const [running, setRunning] = useState(false);
  const [execution, setExecution] = useState<Execution | null>(null);
  const [streamLog, setStreamLog] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!agentId) return;
    setLoading(true);
    api.get<Agent>(`/marketplace/agents/${agentId}`)
      .then(setAgent)
      .catch((err) => {
        // Fallback or handle error
        console.error(err);
        setError("Agent not found or unavailable.");
      })
      .finally(() => setLoading(false));
  }, [agentId]);

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputQuery.trim()) return;

    setRunning(true);
    setError(null);
    setStreamLog(["Dispatching execution job..."]);

    try {
      const exec = await api.post<Execution>("/executions/", {
        agent_id: agentId,
        input_data: { query: inputQuery, text: inputQuery },
      });
      setExecution(exec);
      setStreamLog((prev) => [...prev, `Execution created (ID: ${exec.id})`, "Waiting for model runtime..."]);

      // Connect to SSE stream
      const eventSource = new EventSource(`/api/v1/executions/${exec.id}/stream`);

      eventSource.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === "step_started") {
            setStreamLog((prev) => [...prev, `[Step ${payload.data.step}] Executing model reasoning...`]);
          } else if (payload.type === "step_completed") {
            setStreamLog((prev) => [...prev, `[Step ${payload.data.step}] Step completed.`]);
          } else if (payload.type === "completed") {
            setStreamLog((prev) => [...prev, "Execution completed successfully!"]);
            setExecution((prev) => prev ? { ...prev, status: "completed", output_data: payload.data.output } : null);
            eventSource.close();
            setRunning(false);
          } else if (payload.type === "failed") {
            setStreamLog((prev) => [...prev, `Execution failed: ${payload.data.error}`]);
            setError(payload.data.error || "Execution failed.");
            eventSource.close();
            setRunning(false);
          }
        } catch (e) {
          console.error(e);
        }
      };

      eventSource.onerror = () => {
        eventSource.close();
        setRunning(false);
      };

    } catch (err: any) {
      setError(err.message || "Failed to start execution. Please ensure you are logged in.");
      setRunning(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <Navbar />
        <main className="flex-1 container mx-auto px-4 py-8 max-w-4xl space-y-4">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-64 w-full" />
        </main>
        <FooterSection />
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <Navbar />
        <main className="flex-1 container mx-auto px-4 py-16 text-center max-w-md">
          <AlertCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
          <h2 className="text-xl font-bold mb-2">Agent Not Found</h2>
          <p className="text-muted-foreground mb-6">{error || "The requested agent does not exist or has not been approved."}</p>
          <Link href="/marketplace">
            <Button>Back to Marketplace</Button>
          </Link>
        </main>
        <FooterSection />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navbar />

      <main className="flex-1 container mx-auto px-4 py-8 max-w-4xl">
        <Link href="/marketplace" className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-6">
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back to Marketplace
        </Link>

        {/* Agent Header Card */}
        <Card className="mb-8">
          <CardHeader>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <span className="text-4xl p-3 bg-muted rounded-xl">{agent.icon || "🤖"}</span>
                <div>
                  <div className="flex items-center gap-2">
                    <CardTitle className="text-2xl">{agent.name}</CardTitle>
                    {agent.is_platform_owned && <Badge variant="secondary">Official</Badge>}
                  </div>
                  <CardDescription className="mt-1">{agent.short_description || agent.description}</CardDescription>
                </div>
              </div>
              <div className="flex flex-col items-end gap-2">
                <Badge variant={agent.pricing_type === "free" ? "success" : "default"} className="text-sm px-3 py-1">
                  {agent.pricing_type === "free" ? "Free Tier" : `$${(agent.price_per_execution / 100).toFixed(2)} / Execution`}
                </Badge>
                <span className="text-xs text-muted-foreground flex items-center gap-1">
                  <Shield className="h-3.5 w-3.5 text-primary" /> Verified Runtime
                </span>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="border-t pt-4">
              <h4 className="text-sm font-semibold mb-2">Detailed Capabilities</h4>
              <p className="text-sm text-muted-foreground whitespace-pre-line">{agent.description}</p>
            </div>
          </CardContent>
        </Card>

        {/* Execution Interactive Console */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Play className="h-4 w-4 text-primary" /> Run Agent Interactive Console
            </CardTitle>
            <CardDescription>
              Provide prompt instructions or task parameters below to execute this agent.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleRun} className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-1 block">Input Task / Query</label>
                <textarea
                  className="w-full min-h-[120px] rounded-md border border-input bg-background p-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  placeholder="E.g., Analyze recent advancements in AI agent orchestration frameworks and create an executive summary..."
                  value={inputQuery}
                  onChange={(e) => setInputQuery(e.target.value)}
                  disabled={running}
                  required
                />
              </div>

              {error && (
                <div className="p-3 bg-destructive/10 text-destructive text-sm rounded-md border border-destructive/20 flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 flex-shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <Button type="submit" disabled={running || !inputQuery.trim()} className="w-full sm:w-auto">
                {running ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    Executing Agent...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 mr-2" />
                    Execute Agent
                  </>
                )}
              </Button>
            </form>

            {/* Execution Output & Event Stream */}
            {streamLog.length > 0 && (
              <div className="mt-8 border-t pt-6 space-y-4">
                <h4 className="text-sm font-semibold">Live Execution Stream</h4>
                <div className="bg-muted p-4 rounded-lg font-mono text-xs space-y-1 max-h-48 overflow-y-auto">
                  {streamLog.map((log, idx) => (
                    <div key={idx} className="text-muted-foreground">{log}</div>
                  ))}
                </div>

                {execution?.output_data && (
                  <div className="mt-4 p-4 rounded-lg border bg-card">
                    <div className="flex items-center gap-2 font-semibold text-sm mb-2 text-green-600 dark:text-green-400">
                      <CheckCircle2 className="h-4 w-4" /> Agent Response Output
                    </div>
                    <div className="text-sm whitespace-pre-wrap">
                      {typeof execution.output_data.text === "string"
                        ? execution.output_data.text
                        : JSON.stringify(execution.output_data, null, 2)}
                    </div>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </main>

      <FooterSection />
    </div>
  );
}
