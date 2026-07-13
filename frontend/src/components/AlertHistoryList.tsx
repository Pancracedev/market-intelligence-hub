import { BellRing, Mail, MessageSquare } from "lucide-react";
import type { AlertEvent } from "@/lib/api";

const ALERT_LABELS: Record<AlertEvent["alert_type"], string> = {
  price_drop: "Baisse de prix",
  stock_out: "Rupture de stock",
  promo: "Promotion",
};

export default function AlertHistoryList({ alerts }: { alerts: AlertEvent[] }) {
  if (alerts.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 py-6 text-center">
        <BellRing className="h-5 w-5 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">Aucune alerte envoyée pour ce produit pour l&apos;instant.</p>
      </div>
    );
  }

  return (
    <ul className="space-y-3">
      {alerts.map((alert) => (
        <li key={alert.id} className="flex items-start gap-3 rounded-lg border p-3">
          <span className="mt-0.5 flex h-7 w-7 flex-none items-center justify-center rounded-full bg-muted">
            {alert.channel === "slack" ? <MessageSquare className="h-3.5 w-3.5" /> : <Mail className="h-3.5 w-3.5" />}
          </span>
          <div>
            <p className="text-sm font-medium">{ALERT_LABELS[alert.alert_type]}</p>
            <p className="text-sm text-muted-foreground">{alert.message}</p>
            <p className="mt-1 text-xs text-muted-foreground">{new Date(alert.sent_at).toLocaleString("fr-FR")}</p>
          </div>
        </li>
      ))}
    </ul>
  );
}
