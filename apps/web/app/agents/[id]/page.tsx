"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  Play,
  Star,
  Shield,
  ArrowLeft,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Bookmark,
  CreditCard,
  Send,
  User,
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { FooterSection } from "@/components/layout/FooterSection";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { Agent, Execution } from "@/types";

interface Review {
  id: string;
  rating: number;
  comment: string;
  created_at: string;
}

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

  // Approval state
  const [pendingApproval, setPendingApproval] = useState<any | null>(null);

  // Bookmark state
  const [isBookmarked, setIsBookmarked] = useState(false);

  // Reviews state
  const [reviews, setReviews] = useState<Review[]>([]);
  const [userRating, setUserRating] = useState(5);
  const [reviewComment, setReviewComment] = useState("");
  const [submittingReview, setSubmittingReview] = useState(false);

  useEffect(() => {
    if (!agentId) return;
    setLoading(true);
    Promise.all([
      api.get<Agent>(`/marketplace/agents/${agentId}`),
      api.get<Review[]>(`/marketplace/agents/${agentId}/reviews`).catch(() => []),
    ])
      .then(([agentData, reviewList]) => {
        setAgent(agentData);
        setReviews(reviewList);
      })
      .catch((err) => {
        console.error(err);
        setError("Agent not found or unavailable.");
      })
      .finally(() => setLoading(false));
  }, [agentId]);

  const handleToggleBookmark = async () => {
    try {
      const res = await api.post<any>(`/marketplace/agents/${agentId}/bookmark`, {});
      setIsBookmarked(res.bookmarked);
    } catch (err) {
      console.error(err);
    }
  };

  const handleReviewSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reviewComment.trim()) return;
    setSubmittingReview(true);
    try {
      await api.post(`/marketplace/agents/${agentId}/reviews`, {
        rating: userRating,
        comment: reviewComment,
      });
      setReviews((prev) => [
        {
          id: String(Date.now()),
          rating: userRating,
          comment: reviewComment,
          created_at: new Date().toISOString(),
        },
        ...prev,
      ]);
      setReviewComment("");
    } catch (err) {
      console.error(err);
    } finally {
      setSubmittingReview(false);
    }
  };

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputQuery.trim()) return;

    setRunning(true);
    setError(null);
    setPendingApproval(null);
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
            setStreamLog((prev) => [...prev, `[Step ${payload.data.step}] Executing step: ${payload.data.type}`]);
          } else if (payload.type === "approval_requested") {
            setPendingApproval(payload.data);
            setStreamLog((prev) => [...prev, `Action paused: awaiting human approval for '${payload.data.action}'`]);
          } else if (payload.type === "step_completed") {
            setStreamLog((prev) => [...prev, `[Step ${payload.data.step}] Step output generated.`]);
          } else if (payload.type === "completed") {
            setStreamLog((prev) => [...prev, "Execution completed successfully!"]);
            setExecution((prev) => (prev ? { ...prev, status: "completed", output_data: payload.data.output } : null));
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
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleToggleBookmark}
                    className={isBookmarked ? "text-primary border-primary" : ""}
                  >
                    <Bookmark className="h-4 w-4 mr-1 fill-current" />
                    {isBookmarked ? "Saved" : "Save"}
                  </Button>
                  <Badge variant={agent.pricing_type === "free" ? "success" : "default"} className="text-sm px-3 py-1">
                    {agent.pricing_type === "free"
                      ? "Free Tier"
                      : `$${(agent.price_per_execution / 100).toFixed(2)} / Execution`}
                  </Badge>
                </div>
                {agent.pricing_type !== "free" && (
                  <Link href={`/billing/simulate-checkout?session=sim_${Date.now()}&amount=${agent.price_per_execution}&agent_id=${agent.id}`}>
                    <Button size="sm" variant="default" className="gap-1 mt-1">
                      <CreditCard className="h-3.5 w-3.5" /> Purchase Credits
                    </Button>
                  </Link>
                )}
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

        {/* Human-in-the-Loop Sensitive Approval Gate */}
        {pendingApproval && (
          <Card className="mb-8 border-yellow-500 bg-yellow-500/5">
            <CardHeader className="pb-2">
              <CardTitle className="text-base text-yellow-700 dark:text-yellow-400 flex items-center gap-2">
                <AlertCircle className="h-5 w-5" /> Human Approval Required
              </CardTitle>
              <CardDescription>
                This agent has proposed a sensitive action that requires your explicit review before proceeding.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="text-sm">
                <strong>Action:</strong> {pendingApproval.action}
              </div>
              <pre className="p-3 bg-background rounded border text-xs font-mono overflow-x-auto">
                {JSON.stringify(pendingApproval.payload, null, 2)}
              </pre>
            </CardContent>
            <CardFooter className="flex justify-end gap-2 pt-0">
              <Button size="sm" variant="destructive" onClick={() => setPendingApproval(null)}>
                Reject Action
              </Button>
              <Button size="sm" variant="default" onClick={() => setPendingApproval(null)}>
                Approve & Execute
              </Button>
            </CardFooter>
          </Card>
        )}

        {/* Execution Interactive Console */}
        <Card className="mb-8">
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

        {/* Community Reviews & Ratings Section */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Star className="h-4 w-4 text-yellow-500 fill-yellow-500" /> Community Reviews & Ratings
                </CardTitle>
                <CardDescription>
                  Overall Rating: {agent.average_rating || "5.0"} ({reviews.length} reviews)
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Submit a review */}
            <form onSubmit={handleReviewSubmit} className="space-y-3 p-4 bg-muted/40 rounded-lg border">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">Your Rating:</span>
                <div className="flex gap-1">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      type="button"
                      key={star}
                      onClick={() => setUserRating(star)}
                      className="p-1 focus:outline-none"
                    >
                      <Star
                        className={`h-4 w-4 ${
                          star <= userRating ? "text-yellow-500 fill-yellow-500" : "text-muted-foreground"
                        }`}
                      />
                    </button>
                  ))}
                </div>
              </div>
              <textarea
                placeholder="Share your experience using this agent..."
                value={reviewComment}
                onChange={(e) => setReviewComment(e.target.value)}
                className="w-full min-h-[80px] rounded-md border border-input bg-background p-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                required
              />
              <Button type="submit" size="sm" disabled={submittingReview || !reviewComment.trim()} className="gap-1">
                {submittingReview ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
                Post Review
              </Button>
            </form>

            {/* Existing Reviews */}
            <div className="space-y-3">
              {reviews.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">
                  No community reviews posted yet. Be the first to share feedback!
                </p>
              ) : (
                reviews.map((rev) => (
                  <div key={rev.id} className="p-3 border rounded-lg space-y-1">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1">
                        {[1, 2, 3, 4, 5].map((s) => (
                          <Star
                            key={s}
                            className={`h-3 w-3 ${
                              s <= rev.rating ? "text-yellow-500 fill-yellow-500" : "text-muted-foreground"
                            }`}
                          />
                        ))}
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {new Date(rev.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground">{rev.comment}</p>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </main>

      <FooterSection />
    </div>
  );
}
