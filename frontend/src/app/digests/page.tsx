"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Sparkles } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiError, type Digest } from "@/lib/api";
import { getToken } from "@/lib/auth";
import Header from "@/components/Header";

export default function DigestsPage() {
  const router = useRouter();
  const [digests, setDigests] = useState<Digest[] | null>(null);
  const [generating, setGenerating] = useState(false);

  function loadDigests() {
    api.listDigests().then(setDigests).catch(() => toast.error("Impossible de charger vos résumés."));
  }

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    loadDigests();
  }, [router]);

  async function handleGenerate() {
    setGenerating(true);
    try {
      await api.generateDigestNow();
      toast.success("Résumé généré et envoyé par email");
      loadDigests();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Génération impossible");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div>
      <Header />
      <main className="mx-auto max-w-3xl px-6 py-10">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Résumés hebdomadaires</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Chaque semaine, l&apos;IA interprète l&apos;activité de vos produits suivis et vous
              envoie un résumé par email — plutôt qu&apos;une liste de chiffres à recouper vous-même.
            </p>
          </div>
          <Button onClick={handleGenerate} disabled={generating}>
            <Sparkles className="h-4 w-4" />
            {generating ? "Génération..." : "Générer maintenant"}
          </Button>
        </div>

        {digests === null && (
          <div className="space-y-4">
            {[...Array(2)].map((_, i) => (
              <Skeleton key={i} className="h-28 rounded-xl" />
            ))}
          </div>
        )}

        {digests !== null && digests.length === 0 && (
          <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed p-12 text-center">
            <Sparkles className="h-6 w-6 text-muted-foreground" />
            <p className="text-sm font-medium">Aucun résumé pour l&apos;instant</p>
            <p className="max-w-sm text-sm text-muted-foreground">
              Générez votre premier résumé dès que vous avez au moins un produit suivi actif.
            </p>
          </div>
        )}

        <div className="space-y-4">
          {digests?.map((d) => (
            <Card key={d.id}>
              <CardContent>
                <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  {new Date(d.generated_at).toLocaleString("fr-FR")}
                </p>
                <p className="whitespace-pre-line text-sm leading-relaxed">{d.content}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </main>
    </div>
  );
}
