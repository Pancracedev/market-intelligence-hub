import { PackageCheck, Tag, TrendingDown } from "lucide-react";

export default function ProductMockup() {
  return (
    <div className="relative mx-auto w-full max-w-md">
      <div className="absolute -inset-6 -z-10 rounded-[2rem] bg-gradient-to-br from-primary/15 via-primary/5 to-transparent blur-2xl" />
      <div className="overflow-hidden rounded-2xl border bg-card shadow-xl ring-1 ring-foreground/5">
        <div className="flex items-center gap-1.5 border-b bg-muted/40 px-4 py-2.5">
          <span className="h-2.5 w-2.5 rounded-full bg-red-400" />
          <span className="h-2.5 w-2.5 rounded-full bg-amber-400" />
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
          <span className="ml-3 text-xs text-muted-foreground">Casque audio XZ200 — Concurrent A</span>
        </div>
        <div className="space-y-4 p-5">
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-semibold tabular-nums">89,90 €</span>
            <span className="flex items-center gap-1 text-sm font-medium text-emerald-600">
              <TrendingDown className="h-4 w-4" />
              -12,3%
            </span>
          </div>

          <svg viewBox="0 0 300 70" className="h-16 w-full text-primary" preserveAspectRatio="none">
            <defs>
              <linearGradient id="mockupFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="currentColor" stopOpacity="0.25" />
                <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
              </linearGradient>
            </defs>
            <path
              d="M0,45 L30,42 L60,48 L90,30 L120,34 L150,20 L180,26 L210,15 L240,22 L270,10 L300,14"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path
              d="M0,45 L30,42 L60,48 L90,30 L120,34 L150,20 L180,26 L210,15 L240,22 L270,10 L300,14 L300,70 L0,70 Z"
              fill="url(#mockupFill)"
              stroke="none"
            />
          </svg>

          <div className="flex flex-wrap gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-800">
              <PackageCheck className="h-3.5 w-3.5" />
              En stock
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-800">
              <Tag className="h-3.5 w-3.5" />
              Promo -12%
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
