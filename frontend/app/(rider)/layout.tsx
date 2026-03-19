"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { Home, Map, Clock, User, Bell } from "lucide-react";
import { useState } from "react";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Home", icon: Home },
  { href: "/map", label: "Map", icon: Map },
  { href: "/history", label: "History", icon: Clock },
  { href: "/profile", label: "Profile", icon: User },
];

export default function RiderLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [lang, setLang] = useState<"en" | "hi">("en");

  return (
    <div className="min-h-screen bg-surface">
      {/* Desktop Sidebar */}
      <aside className="hidden md:flex fixed left-0 top-0 bottom-0 w-60 bg-navy flex-col z-40">
        <div className="p-6">
          <div className="flex items-center gap-3">
            <svg width="32" height="32" viewBox="0 0 64 64" fill="none">
              <path d="M32 4L56 16V40C56 52 44 60 32 60C20 60 8 52 8 40V16L32 4Z" fill="#2A5A8E" />
              <path d="M30 24L26 36H30L28 44L38 30H33L36 24H30Z" fill="#F5A623" />
            </svg>
            <span className="text-white font-bold text-lg">GridGuard</span>
          </div>
        </div>
        <nav className="flex-1 px-3 space-y-1 mt-4">
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all
                  ${active
                    ? "bg-white/10 text-amber border-l-4 border-amber -ml-px"
                    : "text-white/60 hover:text-white hover:bg-white/5"
                  }`}
              >
                <item.icon className="w-5 h-5" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="p-4 border-t border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center text-sm font-bold text-white">
              RK
            </div>
            <div>
              <p className="text-sm text-white font-medium">Rajesh K.</p>
              <p className="text-xs text-white/50">Zone B4F2</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Mobile Top Bar */}
      <header className="md:hidden fixed top-0 left-0 right-0 h-14 bg-white/80 backdrop-blur-lg border-b border-gray-100 z-40 flex items-center justify-between px-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-navy flex items-center justify-center text-xs font-bold text-white">
            RK
          </div>
          <span className="font-semibold text-sm text-ink-primary">Rajesh K.</span>
        </div>
        <div className="flex items-center gap-2">
          <button className="relative p-2">
            <Bell className="w-5 h-5 text-ink-muted" />
            <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
          </button>
          <div className="bg-gray-100 rounded-full p-0.5 flex text-xs">
            <button
              onClick={() => setLang("en")}
              className={`px-2 py-0.5 rounded-full transition ${lang === "en" ? "bg-white shadow-sm font-medium" : "text-ink-muted"}`}
            >
              EN
            </button>
            <button
              onClick={() => setLang("hi")}
              className={`px-2 py-0.5 rounded-full transition ${lang === "hi" ? "bg-white shadow-sm font-medium" : "text-ink-muted"}`}
            >
              हि
            </button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="md:ml-60 pt-14 md:pt-0 pb-20 md:pb-0">
        {children}
      </main>

      {/* Mobile Bottom Nav */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-gray-100 shadow-lg z-40">
        <div className="flex items-center justify-around h-16">
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className="flex flex-col items-center justify-center gap-1 py-2"
              >
                <item.icon className={`w-5 h-5 transition-colors ${active ? "text-amber" : "text-ink-muted"}`} />
                <span className={`text-[10px] font-medium ${active ? "text-amber" : "text-ink-muted"}`}>
                  {item.label}
                </span>
                {active && (
                  <span className="w-1 h-1 rounded-full bg-amber absolute bottom-2" />
                )}
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
}
