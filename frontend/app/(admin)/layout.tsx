"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import {
  LayoutDashboard, Map, Users, CreditCard, ShieldAlert, BarChart3,
  Bell, Search, ChevronLeft, ChevronRight,
} from "lucide-react";
import ConnectionStatus from "@/components/gridguard/ConnectionStatus";

const ADMIN_NAV = [
  { href: "/overview", label: "Overview", icon: LayoutDashboard },
  { href: "/map", label: "Live Map", icon: Map },
  { href: "/partners", label: "Partners", icon: Users },
  { href: "/payouts", label: "Payouts", icon: CreditCard },
  { href: "/fraud", label: "Fraud", icon: ShieldAlert },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="min-h-screen bg-surface flex">
      {/* Sidebar */}
      <aside
        className={`hidden md:flex fixed left-0 top-0 bottom-0 bg-navy flex-col z-40 transition-all duration-250`}
        style={{
          width: collapsed ? 64 : 240,
          transitionTimingFunction: "cubic-bezier(0.4, 0, 0.2, 1)",
        }}
      >
        <div className={`flex items-center gap-3 p-4 ${collapsed ? "justify-center" : ""}`}>
          <svg width="28" height="28" viewBox="0 0 64 64" fill="none" className="flex-shrink-0">
            <path d="M32 4L56 16V40C56 52 44 60 32 60C20 60 8 52 8 40V16L32 4Z" fill="#2A5A8E" />
            <path d="M30 24L26 36H30L28 44L38 30H33L36 24H30Z" fill="#F5A623" />
          </svg>
          {!collapsed && <span className="text-white font-bold text-lg">GridGuard</span>}
        </div>

        <nav className="flex-1 px-2 mt-2 space-y-0.5">
          {ADMIN_NAV.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all
                  ${collapsed ? "justify-center" : ""}
                  ${active
                    ? "bg-white/10 text-white border-l-4 border-amber"
                    : "text-white/50 hover:text-white hover:bg-white/5"
                  }`}
                title={collapsed ? item.label : undefined}
              >
                <item.icon className={`w-5 h-5 flex-shrink-0 ${active ? "text-amber" : ""}`} />
                {!collapsed && item.label}
              </Link>
            );
          })}
        </nav>

        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-3 m-2 rounded-lg text-white/40 hover:text-white hover:bg-white/10 transition self-end"
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </aside>

      {/* Main */}
      <div
        className="flex-1 transition-all duration-250"
        style={{
          marginLeft: collapsed ? 64 : 240,
          transitionTimingFunction: "cubic-bezier(0.4, 0, 0.2, 1)",
        }}
      >
        {/* Top bar */}
        <header className="sticky top-0 z-30 h-16 bg-white border-b border-gray-100 flex items-center justify-between px-6">
          <div className="text-sm text-ink-muted">
            <span className="text-ink-primary font-medium">Admin</span>
            <span className="mx-2">/</span>
            <span className="capitalize">{pathname.replace("/", "") || "overview"}</span>
          </div>

          <div className="hidden md:flex items-center gap-2 flex-1 max-w-md mx-8">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-muted" />
              <input
                placeholder="Search... (Cmd+K)"
                className="w-full h-9 pl-9 pr-4 rounded-lg bg-surface border-0 text-sm focus:ring-2 focus:ring-navy/20 outline-none"
              />
            </div>
          </div>

          <div className="flex items-center gap-4">
            <button className="relative p-2 hover:bg-surface rounded-lg transition">
              <Bell className="w-5 h-5 text-ink-muted" />
              <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
            </button>
            <ConnectionStatus isLive={true} label="42 live" />
            <div className="w-8 h-8 rounded-full bg-navy flex items-center justify-center text-xs font-bold text-white">
              AD
            </div>
          </div>
        </header>

        <main className="p-6">{children}</main>
      </div>
    </div>
  );
}
