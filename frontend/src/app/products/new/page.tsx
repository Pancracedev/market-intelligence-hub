"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  BellRing,
  ChevronDown,
  PackageCheck,
  PackageX,
  ShieldAlert,
  Sparkles,
  Wand2,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Collapsible, CollapsibleContent } from "@/components/ui/collapsible";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api, ApiError, type DetectedProduct } from "@/lib/api";
import Header from "@/components/Header";

export default function NewProductPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [detecting, setDetecting] = useState(false);
  const [detected, setDetected] = useState<DetectedProduct | null>(null);
  const [detectionFailed, setDetectionFailed] = useState(false);

  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [cssSelector, setCssSelector] = useState("");
  const [stockSelector, setStockSelector] = useState("");
  const [promoSelector, setPromoSelector] = useState("");
  const [currency, setCurrency] = useState("EUR");
  const [schedule, setSchedule] = useState("@daily");
  const [alertPriceDropPct, setAlertPriceDropPct] = useState("10");
  const [alertOnStockOut, setAlertOnStockOut] = useState(true);
  const [alertOnPromo, setAlertOnPromo] = useState(true);
  const [loading, setLoading] = useState(false);

  async function handleDetect() {
    if (!url) {
      toast.error("Indiquez d'abord une URL");
      return;
    }
    setDetecting(true);
    setDetected(null);
    setDetectionFailed(false);
    try {
      const result = await api.detectProduct(url);
      setDetected(result);
      setCurrency(result.currency);
    } catch (err) {
      setDetectionFailed(true);
      setAdvancedOpen(true);
      toast.error(
        err instanceof ApiError
          ? err.message
          : "Détection automatique impossible sur cette page — utilisez les options avancées."
      );
    } finally {
      setDetecting(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const usingManualMode = advancedOpen && cssSelector.trim().length > 0;
    if (!usingManualMode && !detected) {
      toast.error("Détectez d'abord le prix, ou renseignez un sélecteur CSS dans les options avancées.");
      return;
    }

    setLoading(true);
    try {
      const product = await api.createProduct({
        name,
        url,
        mode: usingManualMode ? "manual" : "auto",
        currency,
        schedule,
        cssSelector: usingManualMode ? cssSelector : undefined,
        stockSelector: usingManualMode ? stockSelector || undefined : undefined,
        promoSelector: usingManualMode ? promoSelector || undefined : undefined,
        alertPriceDropPct: alertPriceDropPct ? Number(alertPriceDropPct) : undefined,
        alertOnStockOut,
        alertOnPromo,
      });
      toast.success("Produit ajouté à votre veille");
      router.push(`/products/${product.id}`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Création impossible");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <Header />
      <main className="mx-auto max-w-2xl px-6 py-10">
        <Link href="/dashboard" className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" />
          Retour
        </Link>

        <div className="mb-6">
          <h1 className="text-xl font-semibold tracking-tight">Suivre un nouveau produit</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Collez simplement l&apos;URL de la page produit — on détecte automatiquement le prix et
            le stock, sans configuration technique.
          </p>
        </div>

        <Alert className="mb-6">
          <ShieldAlert className="h-4 w-4" />
          <AlertDescription>
            Vous êtes responsable de vous assurer que vous avez le droit de surveiller cette page. Le
            pipeline respecte le fichier robots.txt et limite la fréquence des requêtes par domaine,
            mais ne vérifie pas la légalité du scraping vis-à-vis des conditions d&apos;utilisation du
            site ciblé.
          </AlertDescription>
        </Alert>

        <form onSubmit={handleSubmit} className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Produit à surveiller</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="name">Nom du produit</Label>
                <Input
                  id="name"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Ex : Casque audio XZ200 — Concurrent A"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="url">URL de la page produit</Label>
                <div className="flex gap-2">
                  <Input
                    id="url"
                    type="url"
                    required
                    value={url}
                    onChange={(e) => {
                      setUrl(e.target.value);
                      setDetected(null);
                      setDetectionFailed(false);
                    }}
                    placeholder="https://marketplace.exemple.com/produit/42"
                  />
                  <Button type="button" variant="outline" onClick={handleDetect} disabled={detecting}>
                    <Sparkles className="h-4 w-4" />
                    {detecting ? "Détection..." : "Détecter"}
                  </Button>
                </div>
              </div>

              {detected && (
                <div className="flex items-center gap-3 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm">
                  <span className="text-xl font-semibold tabular-nums text-emerald-900">
                    {detected.value} {detected.currency}
                  </span>
                  {detected.in_stock === false ? (
                    <span className="inline-flex items-center gap-1 text-red-700">
                      <PackageX className="h-3.5 w-3.5" />
                      Rupture de stock
                    </span>
                  ) : detected.in_stock === true ? (
                    <span className="inline-flex items-center gap-1 text-emerald-700">
                      <PackageCheck className="h-3.5 w-3.5" />
                      En stock
                    </span>
                  ) : null}
                  <span className="ml-auto text-xs text-emerald-700">Détecté automatiquement</span>
                </div>
              )}

              {detectionFailed && (
                <p className="text-sm text-amber-700">
                  Aucune donnée structurée trouvée sur cette page. Ouvrez les options avancées
                  ci-dessous pour indiquer manuellement où se trouve le prix.
                </p>
              )}
            </CardContent>
          </Card>

          <Collapsible open={advancedOpen} onOpenChange={setAdvancedOpen}>
            <Card>
              <CardHeader
                className="cursor-pointer select-none"
                onClick={() => setAdvancedOpen((open) => !open)}
              >
                <CardTitle className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-2">
                    <Wand2 className="h-4 w-4" />
                    Options avancées
                    <span className="font-normal text-muted-foreground">
                      (pour les cas où la détection automatique ne suffit pas)
                    </span>
                  </span>
                  <ChevronDown className={`h-4 w-4 transition-transform ${advancedOpen ? "rotate-180" : ""}`} />
                </CardTitle>
              </CardHeader>
              <CollapsibleContent>
                <CardContent className="space-y-4">
                  <p className="text-xs text-muted-foreground">
                    Renseignez un sélecteur CSS pour forcer une extraction manuelle du prix (utile si
                    la détection automatique se trompe ou ne trouve rien).
                  </p>
                  <div className="space-y-1.5">
                    <Label htmlFor="cssSelector">Sélecteur CSS du prix</Label>
                    <Input
                      id="cssSelector"
                      value={cssSelector}
                      onChange={(e) => setCssSelector(e.target.value)}
                      placeholder=".price, #product-price..."
                      className="font-mono"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="stockSelector">Sélecteur CSS du stock / disponibilité</Label>
                    <Input
                      id="stockSelector"
                      value={stockSelector}
                      onChange={(e) => setStockSelector(e.target.value)}
                      placeholder=".availability, #stock-status..."
                      className="font-mono"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="promoSelector">Sélecteur CSS du prix barré (avant promo)</Label>
                    <Input
                      id="promoSelector"
                      value={promoSelector}
                      onChange={(e) => setPromoSelector(e.target.value)}
                      placeholder=".was-price, .price--strikethrough..."
                      className="font-mono"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                      <Label htmlFor="currency">Devise</Label>
                      <Input id="currency" value={currency} onChange={(e) => setCurrency(e.target.value)} />
                    </div>
                  </div>
                </CardContent>
              </CollapsibleContent>
            </Card>
          </Collapsible>

          <Card>
            <CardHeader>
              <CardTitle>Fréquence de vérification</CardTitle>
            </CardHeader>
            <CardContent>
              <Select value={schedule} onValueChange={(value) => setSchedule(value ?? "@daily")}>
                <SelectTrigger id="schedule" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="@hourly">Toutes les heures</SelectItem>
                  <SelectItem value="@daily">Tous les jours</SelectItem>
                  <SelectItem value="@weekly">Toutes les semaines</SelectItem>
                </SelectContent>
              </Select>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BellRing className="h-4 w-4" />
                Alertes
              </CardTitle>
              <CardDescription>
                Soyez notifié par email (et Slack si configuré dans vos réglages) dès qu&apos;un
                changement significatif est détecté — pas besoin de revenir consulter le dashboard.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="space-y-1.5">
                <Label htmlFor="alertPriceDropPct">Alerter si le prix baisse de plus de (%)</Label>
                <Input
                  id="alertPriceDropPct"
                  type="number"
                  min={1}
                  max={100}
                  value={alertPriceDropPct}
                  onChange={(e) => setAlertPriceDropPct(e.target.value)}
                  placeholder="Ex : 10"
                  className="max-w-32"
                />
                <p className="text-xs text-muted-foreground">Laissez vide pour désactiver cette alerte.</p>
              </div>
              <div className="flex items-center justify-between">
                <Label htmlFor="alertOnStockOut" className="font-normal">
                  Alerter en cas de rupture de stock
                </Label>
                <Switch id="alertOnStockOut" checked={alertOnStockOut} onCheckedChange={setAlertOnStockOut} />
              </div>
              <div className="flex items-center justify-between">
                <Label htmlFor="alertOnPromo" className="font-normal">
                  Alerter en cas de nouvelle promotion
                </Label>
                <Switch id="alertOnPromo" checked={alertOnPromo} onCheckedChange={setAlertOnPromo} />
              </div>
            </CardContent>
          </Card>

          <Button type="submit" disabled={loading} className="w-full" size="lg">
            {loading ? "Création..." : "Commencer le suivi"}
          </Button>
        </form>
      </main>
    </div>
  );
}
