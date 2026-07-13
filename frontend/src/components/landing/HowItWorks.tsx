const STEPS = [
  {
    number: "1",
    title: "Ajoutez un produit",
    description: "Collez l'URL de la page produit d'un concurrent et indiquez ce qu'il faut surveiller (prix, stock, promo).",
  },
  {
    number: "2",
    title: "Le pipeline vérifie automatiquement",
    description: "Selon la fréquence choisie, la page est revérifiée — dans le respect du robots.txt et sans surcharger le site.",
  },
  {
    number: "3",
    title: "Vous voyez tout dans votre tableau de bord",
    description: "Prix, historique, ruptures de stock et promotions apparaissent dès qu'ils sont détectés.",
  },
];

export default function HowItWorks() {
  return (
    <section id="comment-ca-marche" className="border-y bg-muted/30">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-semibold tracking-tight">Comment ça marche</h2>
          <p className="mt-3 text-muted-foreground">Trois étapes, aucune intervention manuelle ensuite.</p>
        </div>

        <div className="mt-12 grid grid-cols-1 gap-8 md:grid-cols-3">
          {STEPS.map((step) => (
            <div key={step.number} className="relative">
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
                {step.number}
              </span>
              <h3 className="mt-4 font-medium">{step.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{step.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
