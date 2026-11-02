"use client";

import { useState } from "react";
import Link from "next/link";
import { Users, UserPlus, Shield, Building2, Check, Mail } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { FooterSection } from "@/components/layout/FooterSection";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

interface Member {
  id: string;
  name: string;
  email: string;
  role: "owner" | "admin" | "member";
  status: "active" | "invited";
}

export default function OrganizationPage() {
  const [orgName, setOrgName] = useState("Acme AI Automations");
  const [inviteEmail, setInviteEmail] = useState("");
  const [members, setMembers] = useState<Member[]>([
    { id: "1", name: "Platform Admin", email: "admin@agenthub.example", role: "owner", status: "active" },
    { id: "2", name: "Sarah Jenkins", email: "sarah@acme.example", role: "admin", status: "active" },
    { id: "3", name: "Dev Team", email: "dev@acme.example", role: "member", status: "invited" },
  ]);
  const [invitedSuccess, setInvitedSuccess] = useState(false);

  const handleInvite = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail.trim()) return;
    setMembers((prev) => [
      ...prev,
      {
        id: String(Date.now()),
        name: inviteEmail.split("@")[0],
        email: inviteEmail,
        role: "member",
        status: "invited",
      },
    ]);
    setInviteEmail("");
    setInvitedSuccess(true);
    setTimeout(() => setInvitedSuccess(false), 3000);
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navbar />

      <main className="flex-1 container mx-auto px-4 py-8 max-w-4xl">
        <div className="flex items-center gap-3 mb-8">
          <div className="p-3 bg-primary/10 rounded-xl text-primary">
            <Building2 className="h-8 w-8" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Organization & Team Workspace</h1>
            <p className="text-muted-foreground">Manage multi-tenant organization boundaries, shared agent licenses, and member roles.</p>
          </div>
        </div>

        {/* Organization Details Card */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Organization Settings</CardTitle>
            <CardDescription>Workspace identity and tenancy boundary details.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-sm font-medium">Organization Name</label>
                <Input value={orgName} onChange={(e) => setOrgName(e.target.value)} />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium">Workspace Slug</label>
                <Input value="acme-automations" disabled className="bg-muted text-muted-foreground" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Team Members Management */}
        <Card>
          <CardHeader>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Users className="h-5 w-5 text-primary" /> Team Members & Seats ({members.length}/10)
                </CardTitle>
                <CardDescription>Invite team members to collaborate on agent executions.</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Invite Form */}
            <form onSubmit={handleInvite} className="flex gap-2">
              <div className="relative flex-1">
                <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  type="email"
                  placeholder="colleague@yourcompany.com"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  className="pl-9"
                  required
                />
              </div>
              <Button type="submit" className="gap-1">
                <UserPlus className="h-4 w-4" /> Invite Member
              </Button>
            </form>

            {invitedSuccess && (
              <div className="p-3 bg-green-500/10 text-green-600 border border-green-500/20 rounded-md text-sm flex items-center gap-2">
                <Check className="h-4 w-4" /> Invitation dispatched to member.
              </div>
            )}

            {/* Members Table */}
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 border-b text-muted-foreground text-xs font-semibold">
                  <tr>
                    <th className="p-3 text-left">Member</th>
                    <th className="p-3 text-left">Role</th>
                    <th className="p-3 text-left">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {members.map((m) => (
                    <tr key={m.id} className="hover:bg-muted/20">
                      <td className="p-3">
                        <div className="font-medium">{m.name}</div>
                        <div className="text-xs text-muted-foreground">{m.email}</div>
                      </td>
                      <td className="p-3">
                        <Badge variant="outline" className="capitalize text-xs">
                          {m.role}
                        </Badge>
                      </td>
                      <td className="p-3">
                        <Badge variant={m.status === "active" ? "success" : "warning"} className="text-[10px]">
                          {m.status}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </main>

      <FooterSection />
    </div>
  );
}
