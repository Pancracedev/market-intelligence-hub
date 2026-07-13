"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, MessageSquare } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";
import { getToken } from "@/lib/auth";
import Header from "@/components/Header";

export default function SettingsPage() {
  const router = useRouter();
  const [email, setEmail] = useState<string>();
  const [slackWebhookUrl, setSlackWebhookUrl] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    api
      .me()
      .then((user) => {
        setEmail(user.email);
        setSlackWebhookUrl(user.slack_webhook_url ?? "");
      })
      .catch(() => {});
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      await api.updateSettings(slackWebhookUrl);
      toast.success("Réglages enregistrés");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Enregistrement impossible");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <Header email={email} />
      <main className="mx-auto max-w-2xl px-6 py-10">
        <Link href="/dashboard" className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" />
          Retour
        </Link>

        <div className="mb-6">
          <h1 className="text-xl font-semibold tracking-tight">Réglages de notification</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Les alertes email utilisent toujours l&apos;adresse de votre compte. Ajoutez un webhook
            Slack pour les recevoir aussi sur un canal de votre choix.
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MessageSquare className="h-4 w-4" />
                Webhook Slack
              </CardTitle>
              <CardDescription>
                Créez un{" "}
                <a
                  href="https://api.slack.com/messaging/webhooks"
                  target="_blank"
                  rel="noreferrer"
                  className="underline hover:text-foreground"
                >
                  webhook entrant Slack
                </a>{" "}
                pour votre canal, puis collez son URL ci-dessous.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="slackWebhookUrl">URL du webhook</Label>
                <Input
                  id="slackWebhookUrl"
                  type="url"
                  value={slackWebhookUrl}
                  onChange={(e) => setSlackWebhookUrl(e.target.value)}
                  placeholder="https://hooks.slack.com/services/..."
                  className="font-mono"
                />
              </div>
              <Button type="submit" disabled={loading}>
                {loading ? "Enregistrement..." : "Enregistrer"}
              </Button>
            </CardContent>
          </Card>
        </form>
      </main>
    </div>
  );
}
