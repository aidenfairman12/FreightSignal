"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/search", label: "Search" },
  { href: "/about",  label: "How it works" },
];

export default function NavBar() {
  const pathname = usePathname();
  if (pathname === "/") return null;

  return (
    <nav className="sticky top-0 z-50 border-b border-gray-800 bg-gray-950/90 backdrop-blur-sm">
      <div className="mx-auto max-w-3xl px-4 h-14 flex items-center justify-between">
        <Link href="/" className="text-sm font-bold text-white tracking-tight hover:text-emerald-400 transition-colors">
          FreightSignal
        </Link>
        <div className="flex items-center gap-6">
          {links.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={`text-sm transition-colors ${
                pathname === href
                  ? "text-emerald-400 font-medium"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              {label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}
