"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Camera, Mail } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import ZoneHexBadge from "@/components/gridguard/ZoneHexBadge";
import RiskTierPill from "@/components/gridguard/RiskTierPill";
import { fetchCityRiskSummary, type CityRiskSummary } from "@/lib/city-risk";
import { ApiError, apiGet, apiPatch } from "@/lib/api";
import { getAccessToken, zoneFromH3 } from "@/lib/gridguard";

const LANGUAGES = [
  { code: "en", label: "English", flag: "🇬🇧" },
  { code: "hi", label: "हिंदी", flag: "🇮🇳" },
  { code: "ta", label: "தமிழ்", flag: "🇮🇳" },
  { code: "te", label: "తెలుగు", flag: "🇮🇳" },
];

type AuthMeResponse = {
  partner: {
    id: string;
    full_name: string;
    email: string;
    device_id: string;
    city: string;
    risk_tier: string;
    primary_zone_h3: string | null;
    preferred_language: "en" | "hi" | "ta" | "te";
    auto_premium_deduction: boolean;
    is_active: boolean;
  };
  active_policy?: {
    week_start: string;
    week_end: string;
    premium_amount: number;
    risk_score: number;
    status: string;
  } | null;
};

type PreferencesResponse = {
  status: string;
  preferred_language: "en" | "hi" | "ta" | "te";
  auto_premium_deduction: boolean;
};

type PolicyHistoryResponse = {
  policies: Array<{
    id: string;
    week_start: string;
    week_end: string;
    premium_amount: number;
    status: string;
    risk_score: number;
    payout_count: number;
  }>;
};

function normalizeRiskTier(tier?: string): "low" | "medium" | "high" | "critical" {
  if (tier === "low" || tier === "medium" || tier === "high" || tier === "critical") {
    return tier;
  }
  return "high";
}

function formatWeekRange(weekStart?: string, weekEnd?: string): string {
  if (!weekStart || !weekEnd) {
    return "-";
  }
  const start = new Date(weekStart);
  const end = new Date(weekEnd);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
    return `${weekStart} – ${weekEnd}`;
  }
  const startLabel = start.toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
  const endLabel = end.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
  return `${startLabel} – ${endLabel}`;
}

export default function ProfilePage() {
  const router = useRouter();
  const [autoDeduct, setAutoDeduct] = useState(true);
  const [selectedLang, setSelectedLang] = useState("en");
  const [expandedWeek, setExpandedWeek] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [prefMessage, setPrefMessage] = useState("");
  const [profile, setProfile] = useState<AuthMeResponse | null>(null);
  const [cityRiskSummary, setCityRiskSummary] = useState<CityRiskSummary | null>(null);
  const [policyHistory, setPolicyHistory] = useState<PolicyHistoryResponse["policies"]>([]);

  useEffect(() => {
    const run = async () => {
      const token = getAccessToken();
      if (!token) {
        router.replace("/login");
        return;
      }

      try {
        setLoading(true);
        setError("");

        const me = await apiGet<AuthMeResponse>("/auth/me", token);
        const history = await apiGet<PolicyHistoryResponse>("/policies/history?limit=20", token);

        setProfile(me);
        setPolicyHistory(history.policies);
        setSelectedLang(me.partner.preferred_language || "en");
        setAutoDeduct(me.partner.auto_premium_deduction);

        const liveCityRisk = await fetchCityRiskSummary(me.partner.city).catch(() => null);
        setCityRiskSummary(liveCityRisk);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          router.replace("/login");
          return;
        }
        setError(err instanceof ApiError ? err.message : "Unable to load profile details.");
      } finally {
        setLoading(false);
      }
    };

    run();
  }, [router]);

  const savePreferences = async (payload: Partial<{ preferred_language: "en" | "hi" | "ta" | "te"; auto_premium_deduction: boolean }>) => {
    const token = getAccessToken();
    if (!token) {
      router.replace("/login");
      return;
    }

    try {
      setSaving(true);
      setPrefMessage("");
      const response = await apiPatch<PreferencesResponse>("/auth/me/preferences", payload, token);
      setSelectedLang(response.preferred_language);
      setAutoDeduct(response.auto_premium_deduction);
      setPrefMessage("Preferences saved.");
    } catch (err) {
      setPrefMessage(err instanceof ApiError ? err.message : "Unable to save preferences.");
    } finally {
      setSaving(false);
    }
  };

  const displayName = profile?.partner.full_name || "Rider";
  const initials = useMemo(() => {
    const parts = displayName.split(" ").filter(Boolean);
    return parts.slice(0, 2).map((part) => part[0]?.toUpperCase() || "").join("") || "RK";
  }, [displayName]);

  const zone = zoneFromH3(profile?.partner.primary_zone_h3) || "N/A";
  const activePolicy = profile?.active_policy || null;
  const activeRiskTier = normalizeRiskTier(cityRiskSummary?.risk_tier || profile?.partner.risk_tier);

  return (
    <div className="max-w-2xl mx-auto px-4 py-6 space-y-6">
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Avatar + Info */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center"
      >
        <div className="relative inline-block">
          <div className="w-20 h-20 rounded-full bg-navy flex items-center justify-center text-2xl font-bold text-white">
            {initials}
          </div>
          <a
            href="mailto:support@gridguard.ai?subject=GridGuard%20Profile%20Photo%20Request"
            className="absolute bottom-0 right-0 w-7 h-7 rounded-full bg-amber flex items-center justify-center shadow-md"
          >
            <Camera className="w-3.5 h-3.5 text-white" />
          </a>
        </div>
        <h2 className="text-xl font-bold text-ink-primary mt-3">{displayName}</h2>
        <div className="flex items-center justify-center gap-3 mt-2">
          <span className="px-3 py-1 rounded-lg bg-gray-100 text-xs font-mono text-ink-muted">
            {profile?.partner.device_id || "-"}
          </span>
          <ZoneHexBadge zone={zone} />
        </div>
      </motion.div>

      {/* Policy Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="relative bg-white rounded-2xl shadow-card p-6"
      >
        <span className={`absolute top-4 right-4 px-2.5 py-0.5 rounded-full text-xs font-semibold ${
          activePolicy ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-600"
        }`}>
          {activePolicy ? "Active Coverage" : "No Active Coverage"}
        </span>
        <h3 className="text-lg font-bold text-ink-primary mb-4">Your Policy</h3>
        <div className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-ink-muted">Week</span>
            <span className="text-ink-primary font-medium">
              {activePolicy ? formatWeekRange(activePolicy.week_start, activePolicy.week_end) : "-"}
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-ink-muted">Risk Tier</span>
            <RiskTierPill tier={activeRiskTier} />
          </div>
          <div className="flex justify-between">
            <span className="text-ink-muted">City Live Status</span>
            <span className="text-ink-primary font-medium capitalize">
              {cityRiskSummary
                ? `${cityRiskSummary.status} · ${(cityRiskSummary.avg_workability_score * 100).toFixed(0)}%`
                : "-"}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-ink-muted">Premium</span>
            <span className="text-ink-primary font-medium">₹{Math.round(activePolicy?.premium_amount || 0)}/week</span>
          </div>
        </div>
      </motion.div>

      {/* Auto-Deduction Toggle */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="bg-white rounded-2xl shadow-card p-6"
      >
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-ink-primary">Auto-premium deduction</p>
            <p className="text-xs text-ink-muted mt-0.5">Deducted every Monday 6:00 AM</p>
          </div>
          <Switch
            checked={autoDeduct}
            onCheckedChange={(nextValue) => {
              setAutoDeduct(nextValue);
              void savePreferences({ auto_premium_deduction: nextValue });
            }}
            className="data-[state=checked]:bg-amber"
          />
        </div>
        {prefMessage && (
          <p className={`mt-3 text-xs ${prefMessage === "Preferences saved." ? "text-green-700" : "text-red-600"}`}>
            {prefMessage}
          </p>
        )}
      </motion.div>

      {/* Coverage History */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="bg-white rounded-2xl shadow-card p-6"
      >
        <h3 className="text-lg font-bold text-ink-primary mb-4">Coverage History</h3>
        <div className="space-y-2">
          {policyHistory.map((policy) => {
            const weekLabel = formatWeekRange(policy.week_start, policy.week_end);
            return (
            <div key={policy.id} className="border border-gray-100 rounded-xl overflow-hidden">
              <button
                onClick={() => setExpandedWeek(expandedWeek === policy.id ? null : policy.id)}
                className="w-full flex items-center justify-between px-4 py-3 hover:bg-surface transition text-left"
              >
                <span className="text-sm font-medium text-ink-primary">{weekLabel}</span>
                <span className="text-xs text-ink-muted">
                  {policy.payout_count} payout{policy.payout_count > 1 ? "s" : ""}
                </span>
              </button>
              {expandedWeek === policy.id && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  className="border-t border-gray-100"
                >
                  <div className="px-4 py-3 text-sm space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-ink-muted">Premium</span>
                      <span className="font-semibold text-navy">₹{Math.round(policy.premium_amount)}/week</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-ink-muted">Status</span>
                      <span className="capitalize text-ink-primary">{policy.status}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-ink-muted">Risk Score</span>
                      <span className="font-semibold text-ink-primary">{policy.risk_score.toFixed(2)}</span>
                    </div>
                  </div>
                </motion.div>
              )}
            </div>
          );
          })}

          {!loading && policyHistory.length === 0 && (
            <div className="rounded-xl border border-dashed border-gray-300 p-4 text-sm text-ink-muted">
              No policy history available yet.
            </div>
          )}
        </div>
      </motion.div>

      {/* Language Selector */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="bg-white rounded-2xl shadow-card p-6"
      >
        <h3 className="text-sm font-semibold text-ink-primary mb-3">Language</h3>
        <div className="grid grid-cols-2 gap-2">
          {LANGUAGES.map((lang) => (
            <button
              key={lang.code}
              onClick={() => {
                if (selectedLang === lang.code || saving) {
                  return;
                }
                setSelectedLang(lang.code);
                void savePreferences({ preferred_language: lang.code as "en" | "hi" | "ta" | "te" });
              }}
              className={`flex items-center gap-2 px-4 py-3 rounded-xl text-sm font-medium transition-all
                ${selectedLang === lang.code
                  ? "bg-navy text-white"
                  : "bg-surface text-ink-primary hover:bg-gray-100"
                }`}
              disabled={saving}
            >
              <span>{lang.flag}</span>
              {lang.label}
            </button>
          ))}
        </div>
      </motion.div>

      {/* Contact Support */}
      <a
        href="mailto:support@gridguard.ai"
        className="flex items-center justify-center gap-2 w-full h-12 rounded-xl border-2 border-gray-200 text-sm font-semibold text-ink-muted hover:border-navy hover:text-navy transition-all"
      >
        <Mail className="w-4 h-4" />
        Contact Support
      </a>
    </div>
  );
}
