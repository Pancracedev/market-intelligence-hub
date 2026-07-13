"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { LineChart, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { clearToken } from "@/lib/auth";

export default function Header({ email }: { email?: string }) {
  const router = useRouter();

  function handleLogout() {
    clearToken();
    router.push("/login");
  }

  return (
    <header className="sticky top-0 z-10 border-b bg-white/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <Link href="/dashboard" className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <LineChart className="h-4.5 w-4.5" />
          </span>
          <span className="text-[15px] font-semibold tracking-tight">Market Intelligence Hub</span>
        </Link>
        <div className="flex items-center gap-3">
          {email && (
            <span className="hidden rounded-full bg-secondary px-3 py-1 text-xs font-medium text-secondary-foreground sm:inline">
              {email}
            </span>
          )}
          <Button variant="outline" size="sm" onClick={handleLogout}>
            <LogOut className="h-3.5 w-3.5" />
            Déconnexion
          </Button>
        </div>
      </div>
    </header>
  );
}
