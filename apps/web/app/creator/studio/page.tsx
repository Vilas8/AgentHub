"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Plus, Check, Loader2, Sparkles } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { FooterSection } from "@/components/layout/FooterSection";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";

export default function CreatorStudioPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form State
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [icon, setIcon] = useState("🤖");
  const [pricingType, setPricingType] = useState("free");
  const [pricePerExecution, setPricePerExecution] = useState(0);

  // Version / Model State
  const [systemPrompt, setSystemPrompt] = useState("");
  const [modelProvider, setModelProvider] = useState("gemini");
  const [modelName, setModelName] = useState("gemini-1.5-flash");
  const [temperature, setTemperature] = useState(0.7);

  const handleCreate = async () => {
    setLoading(true);
    setError(null);

    try {
      // 1. Create Agent
      const agent = await api.post<any>("/agents/", {
        name,
        description,
        icon,
        pricing_type: pricingType,
        price_per_execution: pricingType === "per_execution" ? Math.round(pricePerExecution * 100) : 0,
        visibility: "public",
      });

      // 2. Create Initial Version
      await api.post(`/agents/${agent.id}/versions`, {
        system_prompt: systemPrompt || "You are an autonomous AI agent built to assist users.",
        objective: description,
        model_provider: modelProvider,
        model_name: modelName,
        temperature,
        max_tokens: 4096,
        max_steps: 10,
        max_duration_seconds: 300,
      });

      // 3. Submit for review
      await api.post(`/agents/${agent.id}/submit-review`, {});

      router.push("/creator");
    } catch (err: any) {
      setError(err.message || "Failed to create agent. Please ensure you have creator credentials.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navbar />

      <main className="flex-1 container mx-auto px-4 py-8 max-w-3xl">
        <Link href="/creator" className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-6">
          <ArrowLeft className="h-4 w-4 mr-1" /> Back to Creator Dashboard
        </Link>

        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">Agent Creation Studio</h1>
          <p className="text-muted-foreground">Configure, instruct, price, and publish your AI agent to the marketplace.</p>
        </div>

        {/* Multi-step progress indicator */}
        <div className="flex items-center justify-between mb-8 border-b pb-4">
          <div className={`text-sm font-semibold ${step >= 1 ? "text-primary" : "text-muted-foreground"}`}>
            1. Basic Info
          </div>
          <div className={`text-sm font-semibold ${step >= 2 ? "text-primary" : "text-muted-foreground"}`}>
            2. System Instructions & Model
          </div>
          <div className={`text-sm font-semibold ${step >= 3 ? "text-primary" : "text-muted-foreground"}`}>
            3. Pricing & Publish
          </div>
        </div>

        {error && (
          <div className="mb-6 p-3 bg-destructive/10 text-destructive text-sm rounded-md border border-destructive/20">
            {error}
          </div>
        )}

        {/* Step 1: Basic Info */}
        {step === 1 && (
          <Card>
            <CardHeader>
              <CardTitle>Basic Agent Information</CardTitle>
              <CardDescription>Give your agent an identity and clear value proposition.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="agent-name">Agent Name</Label>
                <Input
                  id="agent-name"
                  placeholder="E.g., Legal Document Analyzer"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="agent-icon">Icon Emoji</Label>
                <Input
                  id="agent-icon"
                  className="w-24 text-center text-2xl"
                  value={icon}
                  onChange={(e) => setIcon(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="agent-desc">Description</Label>
                <textarea
                  id="agent-desc"
                  className="w-full min-h-[100px] rounded-md border border-input bg-background p-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  placeholder="Detail what this agent does, supported inputs, and expected outputs..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  required
                />
              </div>

              <div className="pt-4 flex justify-end">
                <Button onClick={() => setStep(2)} disabled={!name.trim() || !description.trim()}>
                  Next: Instructions & Model
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 2: System Instructions & Model */}
        {step === 2 && (
          <Card>
            <CardHeader>
              <CardTitle>Model & System Instructions</CardTitle>
              <CardDescription>Define how the agent reasons, its persona, and execution constraints.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Model Provider</Label>
                  <select
                    value={modelProvider}
                    onChange={(e) => setModelProvider(e.target.value)}
                    className="w-full h-10 rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  >
                    <option value="gemini">Google Gemini</option>
                    <option value="openai">OpenAI</option>
                    <option value="anthropic">Anthropic</option>
                    <option value="ollama">Ollama (Local)</option>
                  </select>
                </div>

                <div className="space-y-2">
                  <Label>Model Name</Label>
                  <Input
                    value={modelName}
                    onChange={(e) => setModelName(e.target.value)}
                    placeholder="gemini-1.5-flash / gpt-4o / claude-3-5-sonnet"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="prompt">System Prompt</Label>
                <textarea
                  id="prompt"
                  className="w-full min-h-[160px] font-mono text-xs rounded-md border border-input bg-background p-3 focus:outline-none focus:ring-2 focus:ring-ring"
                  placeholder="You are an expert legal analyst. When given contract clauses, identify risk factors and return a structured assessment..."
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                  required
                />
              </div>

              <div className="pt-4 flex justify-between">
                <Button variant="outline" onClick={() => setStep(1)}>Back</Button>
                <Button onClick={() => setStep(3)} disabled={!systemPrompt.trim()}>
                  Next: Pricing & Publish
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 3: Pricing & Publish */}
        {step === 3 && (
          <Card>
            <CardHeader>
              <CardTitle>Monetization & Review</CardTitle>
              <CardDescription>Set your pricing model. Platform automatically allocates 80% to you.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Pricing Model</Label>
                <select
                  value={pricingType}
                  onChange={(e) => setPricingType(e.target.value)}
                  className="w-full h-10 rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="free">Free for all users</option>
                  <option value="per_execution">Pay per Execution</option>
                </select>
              </div>

              {pricingType === "per_execution" && (
                <div className="space-y-2">
                  <Label>Price per Run ($ USD)</Label>
                  <Input
                    type="number"
                    step="0.05"
                    min="0.10"
                    value={pricePerExecution}
                    onChange={(e) => setPricePerExecution(parseFloat(e.target.value) || 0)}
                  />
                  <p className="text-xs text-muted-foreground">
                    At ${pricePerExecution.toFixed(2)}, you will earn ${(pricePerExecution * 0.8).toFixed(2)} per execution.
                  </p>
                </div>
              )}

              <div className="p-4 bg-muted rounded-lg text-sm space-y-1">
                <div className="font-semibold mb-2">Publishing Summary</div>
                <div>Name: <span className="font-medium">{name}</span></div>
                <div>Provider: <span className="font-medium">{modelProvider} ({modelName})</span></div>
                <div>Pricing: <span className="font-medium">{pricingType === "free" ? "Free" : `$${pricePerExecution.toFixed(2)} / run`}</span></div>
                <div className="text-xs text-muted-foreground mt-2">
                  Once published, the agent enters the review queue for automated and admin approval.
                </div>
              </div>

              <div className="pt-4 flex justify-between">
                <Button variant="outline" onClick={() => setStep(2)}>Back</Button>
                <Button onClick={handleCreate} disabled={loading} className="gap-2">
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                  Submit Agent for Review
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </main>

      <FooterSection />
    </div>
  );
}
