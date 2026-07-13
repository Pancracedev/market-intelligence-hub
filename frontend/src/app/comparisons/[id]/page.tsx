"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Trophy } from "lucide-react";
import {
  Line,
  LineChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, type ComparisonGroup, type ProductSummary } from "@/lib/api";
import Header from "@/components/Header";

const CHART_COLORS = ["#4f46e5", "#059669", "#d97706", "#dc2626", "#0891b2", "#7c3aed"];

export default function ComparisonDetailPage() {
  const params = useParams<{ id: string }>();
  const groupId = Number(params.id);

  const [group, setGroup] = useState<ComparisonGroup | null>(null);
  const [summaries, setSummaries] = useState<Record<number, ProductSummary | null>>({});
  const [history, setHistory] = useState<Record<number, { timestamp: string; value: number }[]>>({});
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    api
      .getComparisonGroup(groupId)
      .then(async (g) => {
        setGroup(g);
        const results = await Promise.all(
          g.watchers.map((w) =>
            Promise.all([api.getProductSummary(w.id).catch(() => []), api.getProductHistory(w.id).catch(() => [])])
          )
        );
        const summaryMap: Record<number, ProductSummary | null> = {};
        const historyMap: Record<number, { timestamp: string; value: number }[]> = {};
        g.watchers.forEach((w, i) => {
          summaryMap[w.id] = (results[i][0] as ProductSummary[])[0] ?? null;
          historyMap[w.id] = results[i][1] as { timestamp: string; value: number }[];
        });
        setSummaries(summaryMap);
        setHistory(historyMap);
      })
      .catch(() => setNotFound(true));
  }, [groupId]);

  const ranked = useMemo(() => {
    if (!group) return [];
    return [...group.watchers]
      .map((w) => ({ watcher: w, summary: summaries[w.id] }))
      .filter((r) => r.summary?.latest_value !== undefined)
      .sort((a, b) => (a.summary!.latest_value ?? 0) - (b.summary!.latest_value ?? 0));
  }, [group, summaries]);

  const chartData = useMemo(() => {
    const merged: Record<string, Record<string, number | string>> = {};
    group?.watchers.forEach((w) => {
      (history[w.id] ?? []).forEach((point) => {
        if (!merged[point.timestamp]) merged[point.timestamp] = { timestamp: point.timestamp };
        merged[point.timestamp][`p${w.id}`] = point.value;
      });
    });
    return Object.values(merged).sort((a, b) => String(a.timestamp).localeCompare(String(b.timestamp)));
  }, [group, history]);

  if (notFound) {
    return (
      <div>
        <Header />
        <main className="mx-auto max-w-4xl px-6 py-10">
          <p className="rounded-lg bg-destructive/10 px-4 py-3 text-sm text-destructive">
            Cette comparaison n&apos;existe pas ou ne vous appartient pas.
          </p>
        </main>
      </div>
    );
  }

  return (
    <div>
      <Header />
      <main className="mx-auto max-w-4xl px-6 py-10">
        <Link href="/comparisons" className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" />
          Retour
        </Link>

        {!group ? (
          <div className="space-y-6">
            <Skeleton className="h-8 w-64" />
            <Skeleton className="h-64 w-full rounded-xl" />
          </div>
        ) : (
          <>
            <h1 className="mb-6 text-2xl font-semibold tracking-tight">{group.name}</h1>

            {group.watchers.length === 0 ? (
              <div className="rounded-xl border border-dashed p-8 text-center text-sm text-muted-foreground">
                Aucun produit n&apos;est encore assigné à cette comparaison. Ouvrez la page d&apos;un
                produit suivi et assignez-le à « {group.name} ».
              </div>
            ) : (
              <>
                <Card className="mb-6">
                  <CardHeader>
                    <CardTitle className="text-sm font-medium">Évolution comparée</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ResponsiveContainer width="100%" height={300}>
                      <LineChart data={chartData} margin={{ top: 10, right: 20, bottom: 0, left: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                        <XAxis
                          dataKey="timestamp"
                          tickFormatter={(v) => new Date(v).toLocaleDateString("fr-FR", { day: "2-digit", month: "short" })}
                          tick={{ fontSize: 11 }}
                        />
                        <YAxis tick={{ fontSize: 11 }} width={48} />
                        <Tooltip labelFormatter={(v) => new Date(v).toLocaleString("fr-FR")} />
                        <Legend />
                        {group.watchers.map((w, i) => (
                          <Line
                            key={w.id}
                            type="monotone"
                            dataKey={`p${w.id}`}
                            name={w.name}
                            stroke={CHART_COLORS[i % CHART_COLORS.length]}
                            strokeWidth={2}
                            dot={false}
                            connectNulls
                          />
                        ))}
                      </LineChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm font-medium">Classement par prix</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead></TableHead>
                          <TableHead>Produit</TableHead>
                          <TableHead>Prix</TableHead>
                          <TableHead>Écart vs. le moins cher</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {ranked.map((r, i) => {
                          const cheapest = ranked[0].summary!.latest_value!;
                          const diff = r.summary!.latest_value! - cheapest;
                          return (
                            <TableRow key={r.watcher.id}>
                              <TableCell>
                                {i === 0 && (
                                  <Badge className="gap-1 border-transparent bg-amber-100 text-amber-800 hover:bg-amber-100">
                                    <Trophy className="h-3 w-3" />
                                    Moins cher
                                  </Badge>
                                )}
                              </TableCell>
                              <TableCell>
                                <Link href={`/products/${r.watcher.id}`} className="hover:text-primary">
                                  {r.watcher.name}
                                </Link>
                              </TableCell>
                              <TableCell className="tabular-nums">
                                {r.summary!.latest_value} {r.summary!.currency}
                              </TableCell>
                              <TableCell className="tabular-nums text-muted-foreground">
                                {diff > 0 ? `+${diff.toFixed(2)}` : "—"}
                              </TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>
              </>
            )}
          </>
        )}
      </main>
    </div>
  );
}
