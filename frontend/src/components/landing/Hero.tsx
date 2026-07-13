import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import ProductMockup from "./ProductMockup";

export default function Hero() {
  return (
    <section className="mx-auto grid max-w-6xl items-center gap-12 px-6 pt-16 pb-20 md:grid-cols-2 md:pt-24">
      <div>
        <span className="inline-flex items-center rounded-full border bg-muted/50 px-3 py-1 text-xs font-medium text-muted-foreground">
          Veille prix · stock · promotions
        </span>
        <h1 className="mt-5 text-4xl font-semibold leading-[1.1] tracking-tight md:text-5xl">
          La veille concurrentielle, automatisée sur les marketplaces.
        </h1>
        <p className="mt-5 max-w-lg text-lg text-muted-foreground">
          Suivez le prix, la disponibilité et les promotions de vos concurrents sans y penser.
          Ajoutez un produit, on s&apos;occupe du reste — vous êtes alerté dès qu&apos;il bouge.
        </p>
        <div className="mt-8 flex flex-wrap items-center gap-3">
          <Link href="/signup" className={cn(buttonVariants({ size: "lg" }), "gap-2")}>
            Commencer gratuitement
            <ArrowRight className="h-4 w-4" />
          </Link>
          <Link href="/login" className={buttonVariants({ variant: "outline", size: "lg" })}>
            Se connecter
          </Link>
        </div>
        <p className="mt-4 text-sm text-muted-foreground">Aucune carte bancaire requise.</p>
      </div>

      <ProductMockup />
    </section>
  );
}
