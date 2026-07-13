import Link from "next/link";
import { LineChart } from "lucide-react";

export default function Footer() {
  return (
    <footer className="border-t">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 py-8 text-sm text-muted-foreground sm:flex-row">
        <Link href="/" className="flex items-center gap-2">
          <LineChart className="h-4 w-4" />
          <span>Market Intelligence Hub</span>
        </Link>
        <a
          href="https://github.com/Pancracedev/market-intelligence-hub"
          target="_blank"
          rel="noreferrer"
          className="transition hover:text-foreground"
        >
          Code source sur GitHub
        </a>
      </div>
    </footer>
  );
}
