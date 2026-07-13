import Link from "next/link";
import { PackageCheck, PackageX, Tag, TrendingDown, TrendingUp } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Product, ProductSummary } from "@/lib/api";

interface Props {
  product: Product;
  summary?: ProductSummary | null;
}

export default function ProductCard({ product, summary }: Props) {
  const currency = summary?.currency ?? "";
  const delta = summary?.delta;
  const hasDelta = delta !== undefined && delta !== null && !Number.isNaN(delta);

  return (
    <Link href={`/products/${product.id}`} className="block">
      <Card className="group transition hover:-translate-y-0.5 hover:shadow-md">
        <CardContent className="space-y-3">
          <div className="flex items-start justify-between gap-2">
            <h3 className="font-medium leading-snug text-foreground transition group-hover:text-primary">
              {product.name}
            </h3>
            {!product.is_active && (
              <Badge variant="secondary" className="shrink-0">
                Inactif
              </Badge>
            )}
          </div>

          {summary?.latest_value !== undefined ? (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xl font-semibold tabular-nums">
                {summary.latest_value} {currency}
              </span>
              {hasDelta && delta !== 0 && (
                <span
                  className={`inline-flex items-center gap-1 text-xs font-medium ${
                    delta! < 0 ? "text-emerald-600" : "text-red-600"
                  }`}
                >
                  {delta! < 0 ? <TrendingDown className="h-3.5 w-3.5" /> : <TrendingUp className="h-3.5 w-3.5" />}
                  {delta! > 0 ? "+" : ""}
                  {delta!.toFixed(2)}
                </span>
              )}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">En attente de la première vérification...</p>
          )}

          <div className="flex flex-wrap gap-1.5">
            {summary?.in_stock === false && (
              <Badge variant="destructive" className="gap-1">
                <PackageX className="h-3 w-3" />
                Rupture de stock
              </Badge>
            )}
            {summary?.in_stock === true && (
              <Badge className="gap-1 border-transparent bg-emerald-100 text-emerald-800 hover:bg-emerald-100">
                <PackageCheck className="h-3 w-3" />
                En stock
              </Badge>
            )}
            {summary?.is_promo && (
              <Badge className="gap-1 border-transparent bg-amber-100 text-amber-800 hover:bg-amber-100">
                <Tag className="h-3 w-3" />
                Promo{summary.discount_pct ? ` -${summary.discount_pct}%` : ""}
              </Badge>
            )}
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
