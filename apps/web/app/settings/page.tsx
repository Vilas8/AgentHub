"use client";

import { useState } from "react";
import Link from "next/link";
import { Settings, User, Bell, Key, Shield, Save, Check } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { FooterSection } from "@/components/layout/FooterSection";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function SettingsPage() {
  const [fullName, setFullName] = useState("Platform Admin");
  const [email, setEmail] = useState("admin@agenthub.example");
  const [bio, setBio] = useState("AI agent developer and marketplace administrator.");
  const [emailNotifications, setEmailNotifications] = useState(true);
  const [saved, setSaved] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navbar />

      <main className="flex-1 container mx-auto px-4 py-8 max-w-3xl">
        <div className="flex items-center gap-3 mb-8">
          <div className="p-3 bg-primary/10 rounded-xl text-primary">
            <Settings className="h-8 w-8" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Account & Platform Settings</h1>
            <p className="text-muted-foreground">Manage your personal profile, notification preferences, and API security keys.</p>
          </div>
        </div>

        {saved && (
          <div className="mb-6 p-4 bg-green-500/10 text-green-600 border border-green-500/20 rounded-lg text-sm flex items-center gap-2">
            <Check className="h-4 w-4" /> Preferences saved successfully.
          </div>
        )}

        <form onSubmit={handleSave} className="space-y-6">
          {/* Profile Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="h-5 w-5 text-primary" /> Profile Information
              </CardTitle>
              <CardDescription>Update your public identity on the marketplace.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-1">
                <label className="text-sm font-medium">Full Name</label>
                <Input value={fullName} onChange={(e) => setFullName(e.target.value)} required />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium">Email Address</label>
                <Input value={email} onChange={(e) => setEmail(e.target.value)} disabled className="bg-muted text-muted-foreground" />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium">Creator Bio</label>
                <textarea
                  className="w-full min-h-[90px] rounded-md border border-input bg-background p-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  value={bio}
                  onChange={(e) => setBio(e.target.value)}
                />
              </div>
            </CardContent>
          </Card>

          {/* Notifications Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bell className="h-5 w-5 text-primary" /> Notification Alerts
              </CardTitle>
              <CardDescription>Choose what automated updates you receive.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <label className="flex items-center justify-between p-3 border rounded-lg cursor-pointer hover:bg-muted/30">
                <div className="text-sm">
                  <div className="font-medium">Execution Completion Alerts</div>
                  <div className="text-xs text-muted-foreground">Notify when background agent runs finish or need approval.</div>
                </div>
                <input
                  type="checkbox"
                  checked={emailNotifications}
                  onChange={(e) => setEmailNotifications(e.target.checked)}
                  className="h-4 w-4 rounded border-input"
                />
              </label>
            </CardContent>
          </Card>

          {/* API Keys Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Key className="h-5 w-5 text-primary" /> Developer API Access
              </CardTitle>
              <CardDescription>Use your API token to programmatically dispatch executions.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              <label className="text-sm font-medium">Active API Token</label>
              <Input
                value="agh_live_948f93284092b740e17f6f2a5ac9120"
                readOnly
                className="font-mono text-xs bg-muted text-muted-foreground"
              />
              <p className="text-xs text-muted-foreground">Keep your API key private. Do not share in frontend code.</p>
            </CardContent>
          </Card>

          <div className="flex justify-end">
            <Button type="submit" className="gap-2">
              <Save className="h-4 w-4" /> Save Settings
            </Button>
          </div>
        </form>
      </main>

      <FooterSection />
    </div>
  );
}
