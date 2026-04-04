"use client";

import { useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import {
  LayoutDashboard, Map, Users, CreditCard, ShieldAlert, BarChart3,
  Bell, Search, ChevronLeft, ChevronRight, Headset, Landmark, ClipboardList, LogOut,
} from "lucide-react";
import ConnectionStatus from "@/components/gridguard/ConnectionStatus";
import { ApiError, apiGet, apiPatch } from "@/lib/api";
import { getAccessToken } from "@/lib/gridguard";

const ADMIN_NAV = [
  { href: "/overview", label: "Overview", icon: LayoutDashboard },
  { href: "/admin-live-map", label: "Live Map", icon: Map },
  { href: "/partners", label: "Partners", icon: Users },
  { href: "/payouts", label: "Payouts", icon: CreditCard },
  { href: "/fraud", label: "Fraud", icon: ShieldAlert },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/support", label: "Support", icon: Headset },
  { href: "/finance", label: "Finance", icon: Landmark },
  { href: "/audit", label: "Audit", icon: ClipboardList },
];

type AuthMeResponse = {
  partner: {
    full_name: string;
    is_admin: boolean;
  };
};

type AdminNotificationSummary = {
  total: number;
  pending_fraud: number;
  processing_payouts: number;
  active_events: number;
};

type DataModeResponse = {
  mode: "real" | "demo";
};

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [accessVerified, setAccessVerified] = useState(false);
  const [adminName, setAdminName] = useState("Admin");
  const [adminInitials, setAdminInitials] = useState("AD");
  const [accessError, setAccessError] = useState("");
  const [searchValue, setSearchValue] = useState("");
  const [notificationCount, setNotificationCount] = useState(0);
  const [dataMode, setDataMode] = useState<"real" | "demo">("real");
  const [modeSaving, setModeSaving] = useState(false);

  useEffect(() => {
    const run = async () => {
      const token = getAccessToken();
      if (!token) {
        router.replace("/admin/login");
        return;
      }

      try {
        const me = await apiGet<AuthMeResponse>("/auth/me", token);
        if (!me.partner.is_admin) {
          router.replace("/admin/login");
          return;
        }

        setAdminName(me.partner.full_name);
        const parts = me.partner.full_name.split(" ").filter(Boolean);
        const initials = parts.slice(0, 2).map((part) => part[0]?.toUpperCase() || "").join("") || "AD";
        setAdminInitials(initials);
        setAccessVerified(true);
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          router.replace("/admin/login");
          return;
        }
        if (error instanceof ApiError && error.status === 403) {
          router.replace("/admin/login");
          return;
        }
        setAccessError(error instanceof ApiError ? error.message : "Unable to validate admin access.");
        setAccessVerified(true);
      }
    };

    run();
  }, [router]);

  useEffect(() => {
    if (!accessVerified) {
      return;
    }

    const fetchSummary = async () => {
      const token = getAccessToken();
      if (!token) {
        return;
      }
      try {
        const summary = await apiGet<AdminNotificationSummary>("/admin/notifications/summary", token);
        setNotificationCount(summary.total);
      } catch {
        setNotificationCount(0);
      }
    };

    const fetchDataMode = async () => {
      const token = getAccessToken();
      if (!token) {
        return;
      }

      try {
        const payload = await apiGet<DataModeResponse>("/admin/data-mode", token);
        setDataMode(payload.mode);
      } catch {
        // Keep existing mode value when endpoint is temporarily unavailable.
      }
    };

    fetchSummary();
    fetchDataMode();
    const timer = window.setInterval(fetchSummary, 30000);
    return () => window.clearInterval(timer);
  }, [accessVerified]);

  const toggleDataMode = async () => {
    const token = getAccessToken();
    if (!token || modeSaving) {
      return;
    }

    const nextMode = dataMode === "real" ? "demo" : "real";
    try {
      setModeSaving(true);
      const payload = await apiPatch<DataModeResponse>(
        "/admin/data-mode",
        { mode: nextMode },
        token,
      );
      setDataMode(payload.mode);

      if (typeof window !== "undefined") {
        window.setTimeout(() => {
          window.location.reload();
        }, 120);
      }
    } catch (error) {
      setAccessError(error instanceof ApiError ? error.message : "Unable to switch data mode.");
    } finally {
      setModeSaving(false);
    }
  };

  const runSearch = () => {
    const query = searchValue.trim();
    if (!query) {
      return;
    }

    if (query.startsWith("fraud:")) {
      router.push(`/fraud?search=${encodeURIComponent(query.replace("fraud:", "").trim())}`);
      return;
    }
    if (query.startsWith("payout:")) {
      router.push(`/payouts?search=${encodeURIComponent(query.replace("payout:", "").trim())}`);
      return;
    }

    router.push(`/partners?search=${encodeURIComponent(query)}`);
  };

  const pageLabel = useMemo(() => {
    const nav = ADMIN_NAV.find((item) => pathname === item.href || pathname.startsWith(`${item.href}/`));
    if (nav) {
      return nav.label;
    }
    const segment = pathname.split("/").filter(Boolean)[0] || "overview";
    return segment.replaceAll("-", " ");
  }, [pathname]);

  if (!accessVerified) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <div className="bg-white border border-slate-100 shadow-card rounded-2xl px-6 py-5 text-sm text-ink-muted">
          Validating admin access...
        </div>
      </div>
    );
  }

  const signOut = () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("gridguard_access_token");
      localStorage.removeItem("gridguard_refresh_token");
      localStorage.removeItem("gridguard_partner_id");
      localStorage.removeItem("gridguard_wallet_balance");
    }
    router.replace("/admin/login");
  };

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
            <span className="text-ink-primary font-medium">{adminName}</span>
            <span className="mx-2">/</span>
            <span className="capitalize">{pageLabel}</span>
          </div>

          <div className="hidden md:flex items-center gap-2 flex-1 max-w-md mx-8">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-muted" />
              <input
                value={searchValue}
                onChange={(event) => setSearchValue(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    runSearch();
                  }
                }}
                placeholder="Search partners or use fraud:/payout:"
                className="w-full h-9 pl-9 pr-4 rounded-lg bg-surface border-0 text-sm focus:ring-2 focus:ring-navy/20 outline-none"
              />
            </div>
            <button
              onClick={runSearch}
              className="h-9 px-3 rounded-lg bg-navy text-white text-sm font-medium hover:bg-navy/90"
            >
              Go
            </button>
          </div>

          <div className="flex items-center gap-4">
            <button
              onClick={toggleDataMode}
              disabled={modeSaving}
              className={`h-8 px-3 rounded-lg border text-[11px] font-semibold uppercase tracking-wide transition disabled:opacity-60 ${
                dataMode === "demo"
                  ? "border-amber-300 bg-amber-50 text-amber-700"
                  : "border-emerald-300 bg-emerald-50 text-emerald-700"
              }`}
              title="Toggle between real and demo grid data"
            >
              {modeSaving ? "Switching..." : `Data: ${dataMode}`}
            </button>
            <button onClick={() => router.push("/support")} className="relative p-2 hover:bg-surface rounded-lg transition">
              <Bell className="w-5 h-5 text-ink-muted" />
              {notificationCount > 0 && (
                <span className="absolute -top-0.5 -right-1 min-w-4 h-4 px-1 bg-red-500 rounded-full text-[10px] text-white font-bold flex items-center justify-center">
                  {notificationCount > 99 ? "99+" : notificationCount}
                </span>
              )}
            </button>
            <ConnectionStatus isLive={true} label={`${notificationCount} alerts`} />
            <div className="w-8 h-8 rounded-full bg-navy flex items-center justify-center text-xs font-bold text-white">
              {adminInitials}
            </div>
            <button
              onClick={signOut}
              className="h-8 px-2.5 rounded-lg border border-slate-200 text-xs font-semibold text-ink-muted hover:text-ink-primary hover:bg-slate-50 inline-flex items-center gap-1"
            >
              <LogOut className="w-3.5 h-3.5" /> Logout
            </button>
          </div>
        </header>

        <main className="p-6">
          {accessError && (
            <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              {accessError}
            </div>
          )}
          {children}
        </main>
      </div>
    </div>
  );
}
