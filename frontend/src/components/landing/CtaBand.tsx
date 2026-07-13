import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export default function CtaBand() {
  return (
    <section className="mx-auto max-w-6xl px-6 py-20">
      <div className="flex flex-col items-center gap-6 rounded-3xl border bg-card px-8 py-14 text-center">
        <h2 className="text-3xl font-semibold tracking-tight">Prêt à surveiller vos concurrents ?</h2>
        <p className="max-w-md text-muted-foreground">
          Créez un compte et ajoutez votre premier produit en moins de deux minutes.
        </p>
        <Link href="/signup" className={cn(buttonVariants({ size: "lg" }), "gap-2")}>
          Commencer gratuitement
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </section>
  );
}
