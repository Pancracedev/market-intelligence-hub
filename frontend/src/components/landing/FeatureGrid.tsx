import { LineChart, PackageSearch, Tags } from "lucide-react";

const FEATURES = [
  {
    icon: LineChart,
    title: "Suivi des prix",
    description:
      "Indiquez l'URL d'une page produit, on relève son prix automatiquement selon la fréquence que vous choisissez et on vous montre son évolution dans le temps.",
  },
  {
    icon: PackageSearch,
    title: "Alertes de rupture de stock",
    description:
      "Sachez immédiatement quand un concurrent est en rupture — une opportunité pour ajuster votre propre disponibilité ou vos prix.",
  },
  {
    icon: Tags,
    title: "Détection de promotions",
    description:
      "Le prix barré est repéré automatiquement : vous voyez apparaître les remises de vos concurrents dès qu'elles sont mises en ligne.",
  },
];

export default function FeatureGrid() {
  return (
    <section id="fonctionnalites" className="mx-auto max-w-6xl px-6 py-20">
      <div className="mx-auto max-w-2xl text-center">
        <h2 className="text-3xl font-semibold tracking-tight">Tout ce qu&apos;il faut pour surveiller un marché</h2>
        <p className="mt-3 text-muted-foreground">
          Trois signaux qui comptent vraiment, réunis dans un seul tableau de bord.
        </p>
      </div>

      <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-3">
        {FEATURES.map(({ icon: Icon, title, description }) => (
          <div key={title} className="rounded-2xl border bg-card p-6">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <Icon className="h-5 w-5" />
            </span>
            <h3 className="mt-4 font-medium">{title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{description}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
