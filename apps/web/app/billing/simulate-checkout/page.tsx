"use client";

import { useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ShieldAlert, CheckCircle2, ArrowLeft, Loader2, CreditCard } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { FooterSection } from "@/components/layout/FooterSection";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

export default function SimulateCheckoutPage() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const sessionId = searchParams.get("session") || "sim_demo_session";
  const amountMinor = parseInt(searchParams.get("amount") || "500", 10);
  const agentId = searchParams.get("agent_id") || "";

  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSimulatePayment = async () => {
    setLoading(true);
    setError(null);

    try {
      await api.post("/billing/verify", {
        payment_id: sessionId,
        amount_minor: amountMinor,
        agent_id: agentId || undefined,
      });
      setSuccess(true);
      setTimeout(() => {
        router.push(agentId ? `/agents/${agentId}` : "/marketplace");
      }, 2500);
    } catch (err: any) {
      setError(err.message || "Simulation failed.");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navbar />

      <main className="flex-1 container mx-auto px-4 py-12 flex items-center justify-center">
        <Card className="w-full max-w-lg border-yellow-500/50 shadow-lg">
          <CardHeader className="text-center pb-4">
            <div className="mx-auto p-3 bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 rounded-full w-fit mb-3">
              <CreditCard className="h-8 w-8" />
            </div>
            <CardTitle className="text-2xl">Payment Simulator (Sandbox)</CardTitle>
            <CardDescription>
              Development Payment Gateway Adapter. No real financial transaction will occur.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            <div className="p-4 bg-muted rounded-lg text-sm space-y-2">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Session Reference:</span>
                <span className="font-mono text-xs">{sessionId}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Amount:</span>
                <span className="font-bold text-base">${(amountMinor / 100).toFixed(2)} USD</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Environment:</span>
                <span className="text-yellow-600 font-semibold">Local Development</span>
              </div>
            </div>

            {error && (
              <div className="p-3 bg-destructive/10 text-destructive text-sm rounded-md">
                {error}
              </div>
            )}

            {success ? (
              <div className="p-4 bg-green-500/10 text-green-600 border border-green-500/20 rounded-lg text-center space-y-2">
                <CheckCircle2 className="h-8 w-8 mx-auto" />
                <div className="font-semibold">Simulated Payment Successful!</div>
                <div className="text-xs text-muted-foreground">
                  Transaction recorded & creator credited. Redirecting...
                </div>
              </div>
            ) : (
              <Button
                onClick={handleSimulatePayment}
                disabled={loading}
                className="w-full h-11 text-base bg-yellow-600 hover:bg-yellow-700 text-white"
              >
                {loading ? <Loader2 className="h-5 w-5 animate-spin mr-2" /> : null}
                Authorize Simulated Payment (${(amountMinor / 100).toFixed(2)})
              </Button>
            )}
          </CardContent>

          <CardFooter className="flex justify-center border-t pt-4">
            <Link href="/marketplace" className="text-sm text-muted-foreground hover:text-foreground inline-flex items-center">
              <ArrowLeft className="h-4 w-4 mr-1" /> Return to Marketplace
            </Link>
          </CardFooter>
        </Card>
      </main>

      <FooterSection />
    </div>
  );
}
