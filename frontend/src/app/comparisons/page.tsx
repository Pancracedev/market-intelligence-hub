"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Plus, Scale, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiError, type ComparisonGroup } from "@/lib/api";
import { getToken } from "@/lib/auth";
import Header from "@/components/Header";

export default function ComparisonsPage() {
  const router = useRouter();
  const [groups, setGroups] = useState<ComparisonGroup[] | null>(null);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [showForm, setShowForm] = useState(false);

  function loadGroups() {
    api.listComparisonGroups().then(setGroups).catch(() => toast.error("Impossible de charger vos comparaisons."));
  }

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    loadGroups();
  }, [router]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      await api.createComparisonGroup(newName);
      setNewName("");
      setShowForm(false);
      toast.success("Comparaison créée");
      loadGroups();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Création impossible");
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Supprimer cette comparaison ? Les produits qu'elle contient ne seront pas supprimés.")) return;
    try {
      await api.deleteComparisonGroup(id);
      toast.success("Comparaison supprimée");
      loadGroups();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Suppression impossible");
    }
  }

  return (
    <div>
      <Header />
      <main className="mx-auto max-w-3xl px-6 py-10">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Comparaisons</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Regroupez plusieurs produits suivis pour comparer le même article chez différents
              concurrents d&apos;un coup d&apos;œil.
            </p>
          </div>
          <Button onClick={() => setShowForm((v) => !v)}>
            <Plus className="h-4 w-4" />
            Nouvelle comparaison
          </Button>
        </div>

        {showForm && (
          <form onSubmit={handleCreate} className="mb-6 flex gap-2">
            <Input
              autoFocus
              required
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Ex : Casque audio XZ200"
            />
            <Button type="submit" disabled={creating}>
              {creating ? "Création..." : "Créer"}
            </Button>
          </form>
        )}

        {groups === null && (
          <div className="space-y-4">
            {[...Array(2)].map((_, i) => (
              <Skeleton key={i} className="h-20 rounded-xl" />
            ))}
          </div>
        )}

        {groups !== null && groups.length === 0 && (
          <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed p-12 text-center">
            <Scale className="h-6 w-6 text-muted-foreground" />
            <p className="text-sm font-medium">Aucune comparaison pour l&apos;instant</p>
            <p className="max-w-sm text-sm text-muted-foreground">
              Créez une comparaison, puis assignez-y plusieurs produits suivis (le même article
              chez différents concurrents) depuis leur page de détail.
            </p>
          </div>
        )}

        <div className="space-y-3">
          {groups?.map((group) => (
            <Card key={group.id}>
              <CardContent className="flex items-center justify-between">
                <Link href={`/comparisons/${group.id}`} className="flex-1">
                  <p className="font-medium hover:text-primary">{group.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {group.watchers.length} produit{group.watchers.length === 1 ? "" : "s"} suivi
                    {group.watchers.length === 1 ? "" : "s"}
                  </p>
                </Link>
                <Button variant="ghost" size="icon" onClick={() => handleDelete(group.id)}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      </main>
    </div>
  );
}
