"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type Product, type ProductSummary } from "@/lib/api";
import { getToken } from "@/lib/auth";
import Header from "@/components/Header";
import ProductCard from "@/components/ProductCard";

export default function DashboardPage() {
  const router = useRouter();
  const [products, setProducts] = useState<Product[] | null>(null);
  const [summaries, setSummaries] = useState<Record<number, ProductSummary | null>>({});
  const [email, setEmail] = useState<string>();

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }

    api.me().then((u) => setEmail(u.email)).catch(() => {});

    api
      .listProducts()
      .then(async (list) => {
        setProducts(list);
        const results = await Promise.all(
          list.map((p) =>
            api
              .getProductSummary(p.id)
              .then((rows) => [p.id, rows[0] ?? null] as const)
              .catch(() => [p.id, null] as const)
          )
        );
        setSummaries(Object.fromEntries(results));
      })
      .catch(() => toast.error("Impossible de charger vos produits suivis."));
  }, [router]);

  const activeCount = products?.filter((p) => p.is_active).length ?? 0;
  const outOfStockCount = Object.values(summaries).filter((s) => s?.in_stock === false).length;
  const promoCount = Object.values(summaries).filter((s) => s?.is_promo).length;

  return (
    <div>
      <Header email={email} />
      <main className="mx-auto max-w-5xl px-6 py-10">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Produits suivis</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {products === null
                ? "Chargement de votre veille concurrentielle..."
                : `${activeCount} produit${activeCount === 1 ? "" : "s"} actif${activeCount === 1 ? "" : "s"}${
                    outOfStockCount ? ` · ${outOfStockCount} en rupture` : ""
                  }${promoCount ? ` · ${promoCount} en promo` : ""}`}
            </p>
          </div>
          <Link href="/products/new" className={buttonVariants()}>
            <Plus className="h-4 w-4" />
            Suivre un produit
          </Link>
        </div>

        {products === null && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[...Array(3)].map((_, i) => (
              <Skeleton key={i} className="h-32 rounded-xl" />
            ))}
          </div>
        )}

        {products !== null && products.length === 0 && (
          <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed p-12 text-center">
            <p className="text-sm font-medium">Aucun produit suivi pour l&apos;instant</p>
            <p className="max-w-sm text-sm text-muted-foreground">
              Ajoutez la page produit d&apos;un concurrent pour commencer à suivre son prix, sa
              disponibilité et ses promotions.
            </p>
            <Link href="/products/new" className={cn(buttonVariants(), "mt-2")}>
              <Plus className="h-4 w-4" />
              Suivre mon premier produit
            </Link>
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {products?.map((p) => (
            <ProductCard key={p.id} product={p} summary={summaries[p.id]} />
          ))}
        </div>
      </main>
    </div>
  );
}
