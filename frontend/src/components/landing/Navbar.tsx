"use client";

import Link from "next/link";
import { LineChart } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export default function Navbar() {
  return (
    <header className="sticky top-0 z-20 border-b border-border/60 bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <LineChart className="h-4.5 w-4.5" />
          </span>
          <span className="text-[15px] font-semibold tracking-tight">Market Intelligence Hub</span>
        </Link>

        <nav className="hidden items-center gap-8 text-sm text-muted-foreground md:flex">
          <a href="#fonctionnalites" className="transition hover:text-foreground">
            Fonctionnalités
          </a>
          <a href="#comment-ca-marche" className="transition hover:text-foreground">
            Comment ça marche
          </a>
        </nav>

        <div className="flex items-center gap-3">
          <Link href="/login" className={cn(buttonVariants({ variant: "ghost" }))}>
            Connexion
          </Link>
          <Link href="/signup" className={cn(buttonVariants())}>
            Commencer gratuitement
          </Link>
        </div>
      </div>
    </header>
  );
}
