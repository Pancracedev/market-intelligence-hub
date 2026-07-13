import { CheckCircle2, XCircle } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import type { Run } from "@/lib/api";

export default function RunHistoryTable({ runs }: { runs: Run[] }) {
  if (runs.length === 0) {
    return <p className="py-6 text-center text-sm text-muted-foreground">Aucune vérification pour le moment.</p>;
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Date</TableHead>
          <TableHead>Statut</TableHead>
          <TableHead>Relevés</TableHead>
          <TableHead>Erreur</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {runs.map((run) => {
          const isSuccess = run.status === "success";
          return (
            <TableRow key={run.id}>
              <TableCell className="text-muted-foreground">
                {new Date(run.created_at).toLocaleString("fr-FR")}
              </TableCell>
              <TableCell>
                <Badge
                  variant={isSuccess ? "default" : "destructive"}
                  className={isSuccess ? "gap-1 border-transparent bg-emerald-100 text-emerald-800 hover:bg-emerald-100" : "gap-1"}
                >
                  {isSuccess ? <CheckCircle2 className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
                  {isSuccess ? "Succès" : "Échec"}
                </Badge>
              </TableCell>
              <TableCell className="text-muted-foreground">{run.records_count ?? "—"}</TableCell>
              <TableCell className="max-w-xs truncate text-red-600">{run.error_message ?? ""}</TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
