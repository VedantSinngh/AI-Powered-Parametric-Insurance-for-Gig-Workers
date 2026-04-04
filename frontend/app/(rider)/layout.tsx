"use client";

import { useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { Home, Map, Clock, User, Bell, LogOut } from "lucide-react";
import { ApiError, apiGet, apiPatch } from "@/lib/api";
import { getAccessToken, zoneFromH3 } from "@/lib/gridguard";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Home", icon: Home },
  { href: "/map", label: "Map", icon: Map },
  { href: "/history", label: "History", icon: Clock },
  { href: "/profile", label: "Profile", icon: User },
];

type AuthMeResponse = {
  partner: {
    full_name: string;
    preferred_language: "en" | "hi" | "ta" | "te";
    primary_zone_h3: string | null;
  };
};

type NotificationSummaryResponse = {
  total: number;
};

type PreferencesResponse = {
  preferred_language: "en" | "hi" | "ta" | "te";
};

export default function RiderLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [lang, setLang] = useState<"en" | "hi" | "ta" | "te">("en");
  const [riderName, setRiderName] = useState("Rider");
  const [zone, setZone] = useState("N/A");
  const [notificationCount, setNotificationCount] = useState(0);
  const [languageSaving, setLanguageSaving] = useState(false);

  const initials = useMemo(() => {
    const parts = riderName.split(" ").filter(Boolean);
    return parts.slice(0, 2).map((part) => part[0]?.toUpperCase() || "").join("") || "RD";
  }, [riderName]);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      router.replace("/login");
      return;
    }

    const loadIdentity = async () => {
      try {
        const me = await apiGet<AuthMeResponse>("/auth/me", token);
        setRiderName(me.partner.full_name);
        setLang(me.partner.preferred_language || "en");
        setZone(zoneFromH3(me.partner.primary_zone_h3));
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          router.replace("/login");
        }
      }
    };

    const loadSummary = async () => {
      try {
        const summary = await apiGet<NotificationSummaryResponse>("/auth/notifications/summary", token);
        setNotificationCount(summary.total);
      } catch {
        // Keep the current count during temporary failures.
      }
    };

    void loadIdentity();
    void loadSummary();

    const timer = window.setInterval(loadSummary, 30000);
    return () => window.clearInterval(timer);
  }, [router]);

  const signOut = () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("gridguard_access_token");
      localStorage.removeItem("gridguard_refresh_token");
      localStorage.removeItem("gridguard_partner_id");
      localStorage.removeItem("gridguard_wallet_balance");
      sessionStorage.removeItem("gridguard_email");
      sessionStorage.removeItem("gridguard_name");
      sessionStorage.removeItem("gridguard_otp_session_id");
      sessionStorage.removeItem("gridguard_partner_id");
    }
    router.replace("/login");
  };

  const changeLanguage = async (nextLang: "en" | "hi") => {
    if (nextLang === lang || languageSaving) {
      return;
    }

    const token = getAccessToken();
    if (!token) {
      router.replace("/login");
      return;
    }

    try {
      setLanguageSaving(true);
      const response = await apiPatch<PreferencesResponse>(
        "/auth/me/preferences",
        { preferred_language: nextLang },
        token,
      );
      setLang(response.preferred_language);
    } catch {
      setLang(nextLang);
    } finally {
      setLanguageSaving(false);
    }
  };

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
              {initials}
            </div>
            <div>
              <p className="text-sm text-white font-medium">{riderName}</p>
              <p className="text-xs text-white/50">Zone {zone}</p>
            </div>
          </div>
          <button
            onClick={signOut}
            className="mt-3 w-full h-9 rounded-lg border border-white/15 text-white/80 hover:text-white hover:bg-white/10 text-xs font-semibold inline-flex items-center justify-center gap-1.5"
          >
            <LogOut className="w-3.5 h-3.5" /> Sign Out
          </button>
        </div>
      </aside>

      {/* Mobile Top Bar */}
      <header className="md:hidden fixed top-0 left-0 right-0 h-14 bg-white/80 backdrop-blur-lg border-b border-gray-100 z-40 flex items-center justify-between px-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-navy flex items-center justify-center text-xs font-bold text-white">
            {initials}
          </div>
          <span className="font-semibold text-sm text-ink-primary">{riderName}</span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => router.push("/history")} className="relative p-2">
            <Bell className="w-5 h-5 text-ink-muted" />
            {notificationCount > 0 && (
              <span className="absolute top-1 right-1 min-w-4 h-4 px-1 bg-red-500 rounded-full text-[10px] text-white font-bold flex items-center justify-center">
                {notificationCount > 99 ? "99+" : notificationCount}
              </span>
            )}
          </button>
          <div className="bg-gray-100 rounded-full p-0.5 flex text-xs">
            <button
              onClick={() => changeLanguage("en")}
              disabled={languageSaving}
              className={`px-2 py-0.5 rounded-full transition ${lang === "en" ? "bg-white shadow-sm font-medium" : "text-ink-muted"}`}
            >
              EN
            </button>
            <button
              onClick={() => changeLanguage("hi")}
              disabled={languageSaving}
              className={`px-2 py-0.5 rounded-full transition ${lang === "hi" ? "bg-white shadow-sm font-medium" : "text-ink-muted"}`}
            >
              हि
            </button>
          </div>
          <button onClick={signOut} className="text-[11px] font-semibold text-ink-muted hover:text-ink-primary px-1">
            Logout
          </button>
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
