"use client";

import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import type { PricePoint } from "@/lib/api";

export default function PriceChart({ data }: { data: PricePoint[] }) {
  if (data.length === 0) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-2 rounded-xl border border-dashed text-center">
        <p className="text-sm font-medium text-foreground">Pas encore de relevé de prix</p>
        <p className="max-w-xs text-xs text-muted-foreground">
          La première vérification n&apos;a pas encore eu lieu. Elle se fera automatiquement selon
          la fréquence choisie, ou déclenchez-la manuellement depuis Airflow.
        </p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={data} margin={{ top: 10, right: 12, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="fillPrice" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--primary)" stopOpacity={0.28} />
            <stop offset="100%" stopColor="var(--primary)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
        <XAxis
          dataKey="timestamp"
          tickFormatter={(v) => new Date(v).toLocaleDateString("fr-FR", { day: "2-digit", month: "short" })}
          tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
          tickLine={false}
          axisLine={{ stroke: "var(--border)" }}
        />
        <YAxis tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} tickLine={false} axisLine={false} width={48} />
        <Tooltip
          labelFormatter={(v) => new Date(v).toLocaleString("fr-FR")}
          contentStyle={{ borderRadius: 12, border: "1px solid var(--border)", fontSize: 12 }}
        />
        <Area type="monotone" dataKey="value" stroke="var(--primary)" strokeWidth={2.25} fill="url(#fillPrice)" dot={false} activeDot={{ r: 4 }} />
      </AreaChart>
    </ResponsiveContainer>
  );
}
