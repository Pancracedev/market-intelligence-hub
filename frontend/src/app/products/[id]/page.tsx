"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, PackageCheck, PackageX, Scale, Tag, Trash2, TrendingDown, TrendingUp } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  api,
  ApiError,
  type AlertEvent,
  type ComparisonGroup,
  type Product,
  type ProductSummary,
  type PricePoint,
  type Run,
} from "@/lib/api";
import Header from "@/components/Header";
import PriceChart from "@/components/PriceChart";
import RunHistoryTable from "@/components/RunHistoryTable";
import AlertHistoryList from "@/components/AlertHistoryList";

export default function ProductDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const productId = Number(params.id);

  const [product, setProduct] = useState<Product | null>(null);
  const [history, setHistory] = useState<PricePoint[]>([]);
  const [summary, setSummary] = useState<ProductSummary | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [alerts, setAlerts] = useState<AlertEvent[]>([]);
  const [groups, setGroups] = useState<ComparisonGroup[]>([]);
  const [notFound, setNotFound] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    api.getProduct(productId).then(setProduct).catch(() => setNotFound(true));
    api.getProductHistory(productId).then(setHistory).catch(() => {});
    api.getProductSummary(productId).then((rows) => setSummary(rows[0] ?? null)).catch(() => {});
    api.listRuns(productId).then(setRuns).catch(() => {});
    api.listAlerts(productId).then(setAlerts).catch(() => {});
    api.listComparisonGroups().then(setGroups).catch(() => {});
  }, [productId]);

  async function handleGroupChange(value: string | null) {
    const groupId = !value || value === "none" ? null : Number(value);
    try {
      const updated = await api.assignProductToGroup(productId, groupId);
      setProduct(updated);
      toast.success(groupId ? "Produit assigné à la comparaison" : "Produit retiré de la comparaison");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Assignation impossible");
    }
  }

  async function handleDelete() {
    if (!confirm("Supprimer définitivement ce produit de votre veille ?")) return;
    setDeleting(true);
    try {
      await api.deleteProduct(productId);
      toast.success("Produit supprimé");
      router.push("/dashboard");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Suppression impossible");
      setDeleting(false);
    }
  }

  if (notFound) {
    return (
      <div>
        <Header />
        <main className="mx-auto max-w-4xl px-6 py-10">
          <p className="rounded-lg bg-destructive/10 px-4 py-3 text-sm text-destructive">
            Ce produit n&apos;existe pas ou ne vous appartient pas.
          </p>
        </main>
      </div>
    );
  }

  const currency = summary?.currency ?? "";
  const delta = summary?.delta;
  const hasDelta = delta !== undefined && delta !== null && !Number.isNaN(delta);

  return (
    <div>
      <Header />
      <main className="mx-auto max-w-4xl px-6 py-10">
        {!product ? (
          <div className="space-y-6">
            <Skeleton className="h-8 w-64" />
            <Skeleton className="h-32 w-full rounded-xl" />
            <Skeleton className="h-64 w-full rounded-xl" />
          </div>
        ) : (
          <>
            <Link href="/dashboard" className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
              <ArrowLeft className="h-4 w-4" />
              Retour
            </Link>

            <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
              <div>
                <h1 className="text-2xl font-semibold tracking-tight">{product.name}</h1>
                <p className="mt-1 text-sm text-muted-foreground">Vérification {product.schedule}</p>
              </div>
              <Button variant="destructive" onClick={handleDelete} disabled={deleting}>
                <Trash2 className="h-4 w-4" />
                Supprimer
              </Button>
            </div>

            {summary?.latest_value !== undefined && (
              <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-3">
                <Card>
                  <CardContent>
                    <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Prix actuel</p>
                    <p className="mt-1 text-2xl font-semibold tabular-nums">
                      {summary.latest_value} {currency}
                    </p>
                    {hasDelta && delta !== 0 && (
                      <p className={`mt-1 flex items-center gap-1 text-xs font-medium ${delta! < 0 ? "text-emerald-600" : "text-red-600"}`}>
                        {delta! < 0 ? <TrendingDown className="h-3.5 w-3.5" /> : <TrendingUp className="h-3.5 w-3.5" />}
                        {delta! > 0 ? "+" : ""}
                        {delta!.toFixed(2)} vs. dernier relevé
                      </p>
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardContent>
                    <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Disponibilité</p>
                    <div className="mt-1.5">
                      {summary.in_stock === false ? (
                        <Badge variant="destructive" className="gap-1">
                          <PackageX className="h-3 w-3" />
                          Rupture de stock
                        </Badge>
                      ) : summary.in_stock === true ? (
                        <Badge className="gap-1 border-transparent bg-emerald-100 text-emerald-800 hover:bg-emerald-100">
                          <PackageCheck className="h-3 w-3" />
                          En stock
                        </Badge>
                      ) : (
                        <span className="text-sm text-muted-foreground">Non surveillée</span>
                      )}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent>
                    <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Promotion</p>
                    <div className="mt-1.5">
                      {summary.is_promo ? (
                        <Badge className="gap-1 border-transparent bg-amber-100 text-amber-800 hover:bg-amber-100">
                          <Tag className="h-3 w-3" />
                          -{summary.discount_pct}% (au lieu de {summary.original_value} {currency})
                        </Badge>
                      ) : (
                        <span className="text-sm text-muted-foreground">Aucune en cours</span>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            <Card className="mb-6">
              <CardHeader>
                <CardTitle className="text-sm font-medium">Évolution du prix</CardTitle>
              </CardHeader>
              <CardContent>
                <PriceChart data={history} />
              </CardContent>
            </Card>

            <Card className="mb-6">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-sm font-medium">
                  <Scale className="h-4 w-4" />
                  Comparaison
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="mb-3 text-sm text-muted-foreground">
                  Regroupez ce produit avec ses équivalents chez d&apos;autres concurrents pour les
                  comparer côte à côte.
                </p>
                <Select value={product.comparison_group_id?.toString() ?? "none"} onValueChange={handleGroupChange}>
                  <SelectTrigger className="w-full sm:w-64">
                    <SelectValue placeholder="Aucune comparaison" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Aucune comparaison</SelectItem>
                    {groups.map((g) => (
                      <SelectItem key={g.id} value={g.id.toString()}>
                        {g.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {groups.length === 0 && (
                  <p className="mt-2 text-xs text-muted-foreground">
                    Aucune comparaison créée — <Link href="/comparisons" className="underline">créez-en une</Link>.
                  </p>
                )}
              </CardContent>
            </Card>

            <Card className="mb-6">
              <CardHeader>
                <CardTitle className="text-sm font-medium">Historique des vérifications</CardTitle>
              </CardHeader>
              <CardContent>
                <RunHistoryTable runs={runs} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">Alertes envoyées</CardTitle>
              </CardHeader>
              <CardContent>
                <AlertHistoryList alerts={alerts} />
              </CardContent>
            </Card>
          </>
        )}
      </main>
    </div>
  );
}
