"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, ShieldAlert } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api, ApiError } from "@/lib/api";
import Header from "@/components/Header";

export default function NewProductPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [cssSelector, setCssSelector] = useState("");
  const [stockSelector, setStockSelector] = useState("");
  const [promoSelector, setPromoSelector] = useState("");
  const [currency, setCurrency] = useState("EUR");
  const [schedule, setSchedule] = useState("@daily");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const product = await api.createProduct({
        name,
        url,
        cssSelector,
        currency,
        schedule,
        stockSelector: stockSelector || undefined,
        promoSelector: promoSelector || undefined,
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
            Surveillez automatiquement le prix, le stock et les promotions d&apos;un produit chez un concurrent.
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
              <CardTitle>Informations générales</CardTitle>
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
                <Input
                  id="url"
                  type="url"
                  required
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://marketplace.exemple.com/produit/42"
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Prix</CardTitle>
              <CardDescription>
                Le sélecteur CSS identifie l&apos;élément de la page qui affiche le prix — inspectez la
                page produit chez le concurrent pour le trouver.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="cssSelector">Sélecteur CSS du prix</Label>
                <Input
                  id="cssSelector"
                  required
                  value={cssSelector}
                  onChange={(e) => setCssSelector(e.target.value)}
                  placeholder=".price, #product-price..."
                  className="font-mono"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label htmlFor="currency">Devise</Label>
                  <Input id="currency" value={currency} onChange={(e) => setCurrency(e.target.value)} />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="schedule">Fréquence de vérification</Label>
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
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>
                Stock et promotions <span className="font-normal text-muted-foreground">(optionnel)</span>
              </CardTitle>
              <CardDescription>
                Ajoutez ces sélecteurs pour être alerté d&apos;une rupture de stock ou d&apos;une promotion.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
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
