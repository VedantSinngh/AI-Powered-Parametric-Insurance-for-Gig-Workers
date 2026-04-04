"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Activity, Bell, MapPin, ShieldAlert } from "lucide-react";
import WorkabilityGauge from "@/components/gridguard/WorkabilityGauge";
import ConnectionStatus from "@/components/gridguard/ConnectionStatus";
import MockWalletBadge from "@/components/gridguard/MockWalletBadge";
import PayoutCard from "@/components/gridguard/PayoutCard";
import { ApiError, apiGet, apiPost } from "@/lib/api";
import type { Payout } from "@/lib/mock-data";
import { weeklyForecast } from "@/lib/mock-data";
import {
  formatDurationHours,
  formatIsoToUi,
  getAccessToken,
  toEventLabel,
  toUiEventType,
  zoneFromH3,
} from "@/lib/gridguard";

type AuthMeResponse = {
  partner: {
    id: string;
    full_name: string;
    city: string;
    primary_zone_h3: string | null;
    mock_wallet_balance: number;
    upi_handle?: string | null;
  };
  active_policy?: {
    premium_amount: number;
  } | null;
};

type WorkabilityResponse = {
  h3_cell: string;
  workability_score: number;
  status: "safe" | "caution" | "disrupted";
  area_name?: string;
  risk_code?: string;
  timestamp: string;
  active_events: Array<{
    event_type: string;
  }>;
  payout_rate_hr: number;
};

type PayoutHistoryResponse = {
  payouts: Array<{
    id: string;
    amount: number;
    status: string;
    mock_reference: string;
    provider?: string;
    created_at: string;
    duration_hours: number;
    event_type?: string;
    h3_cell?: string;
  }>;
};

type NotificationSummaryResponse = {
  total: number;
};

type WalletActionResponse = {
  status: string;
  reference: string;
  balance: number;
  destination?: string;
};

type PricingTier = {
  tier: string;
  premium_amount: number;
  risk_band: string;
  note: string;
};

type PricingWeekPlan = {
  week_start: string;
  week_end: string;
  premium_amount: number;
  risk_score: number;
  risk_tier: "low" | "medium" | "high" | "critical";
  status: string;
  source: string;
  note?: string;
};

type PricingSummaryResponse = {
  as_of: string;
  message: string;
  current_week: PricingWeekPlan | null;
  next_week: PricingWeekPlan | null;
  pricing_tiers: PricingTier[];
};

type WalletLedgerResponse = {
  balance: number;
  summary: {
    payout_credits: number;
    manual_additions: number;
    premium_deductions: number;
    withdrawals: number;
  };
  transactions: Array<{
    id: string;
    type: "credit" | "debit";
    category: string;
    amount: number;
    description: string;
    reference: string;
    balance_after: number;
    created_at: string;
  }>;
};

const FALLBACK_TIERS: PricingTier[] = [
  { tier: "Tier 1", premium_amount: 12, risk_band: "0.00 - 0.20", note: "Stable zones" },
  { tier: "Tier 2", premium_amount: 18, risk_band: "0.20 - 0.40", note: "Low disruption" },
  { tier: "Tier 3", premium_amount: 24, risk_band: "0.40 - 0.60", note: "Moderate risk" },
  { tier: "Tier 4", premium_amount: 36, risk_band: "0.60 - 0.80", note: "High disruption" },
  { tier: "Tier 5", premium_amount: 48, risk_band: "0.80 - 1.00", note: "Severe risk" },
];

function fallbackRiskCode(score: number): string {
  if (score >= 0.7) return "R1";
  if (score >= 0.4) return "R2";
  if (score >= 0.2) return "R3";
  return "R4";
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
  const endLabel = end.toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
  return `${startLabel} – ${endLabel}`;
}

function walletCategoryLabel(category: string): string {
  if (category === "payout_credit") return "Payout";
  if (category === "manual_addition") return "Added Money";
  if (category === "premium_deduction") return "Premium";
  if (category === "withdrawal") return "Withdrawal";
  if (category === "signup_bonus") return "Signup Bonus";
  return "Adjustment";
}

function toUiPayouts(raw: PayoutHistoryResponse["payouts"], fallbackZone: string, city: string, partnerId: string, partnerName: string): Payout[] {
  return raw.map((payout) => {
    const uiEventType = toUiEventType(payout.event_type);
    const uiStatus = payout.status === "paid" ? "paid" : payout.status === "failed" ? "flagged" : "pending";

    return {
      id: payout.id,
      partnerId: partnerId,
      partnerName: partnerName,
      zone: zoneFromH3(payout.h3_cell) || fallbackZone,
      eventType: uiEventType,
      eventName: toEventLabel(payout.event_type),
      amount: Math.round(payout.amount),
      timestamp: formatIsoToUi(payout.created_at),
      status: uiStatus,
      txHash: payout.mock_reference || payout.id,
      city: city,
      duration: formatDurationHours(payout.duration_hours),
      provider: payout.provider,
    };
  });
}

export default function DashboardPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const [partnerName, setPartnerName] = useState("Rider");
  const [city, setCity] = useState("Bengaluru");
  const [zone, setZone] = useState("N/A");
  const [walletBalance, setWalletBalance] = useState(0);
  const [upiHandle, setUpiHandle] = useState<string | null>(null);
  const [workabilityScore, setWorkabilityScore] = useState(0.72);
  const [workabilityStatus, setWorkabilityStatus] = useState<"safe" | "caution" | "disrupted">("safe");
  const [areaName, setAreaName] = useState("Unknown area");
  const [riskCode, setRiskCode] = useState("R1");
  const [activeSignalCount, setActiveSignalCount] = useState(0);
  const [livePayoutRate, setLivePayoutRate] = useState(0);
  const [lastUpdated, setLastUpdated] = useState("Unknown");
  const [recentPayouts, setRecentPayouts] = useState<Payout[]>([]);
  const [notificationCount, setNotificationCount] = useState(0);
  const [walletAmount, setWalletAmount] = useState("300");
  const [walletPending, setWalletPending] = useState(false);
  const [walletError, setWalletError] = useState("");
  const [walletSuccess, setWalletSuccess] = useState("");
  const [pricingSummary, setPricingSummary] = useState<PricingSummaryResponse | null>(null);
  const [walletLedger, setWalletLedger] = useState<WalletLedgerResponse | null>(null);

  const initials = useMemo(() => {
    const parts = partnerName.trim().split(" ").filter(Boolean);
    if (parts.length === 0) {
      return "RK";
    }
    return parts.slice(0, 2).map((namePart) => namePart[0]?.toUpperCase() || "").join("") || "RK";
  }, [partnerName]);

  const weeklyPremium = pricingSummary?.current_week?.premium_amount || 0;
  const pricingTiers = pricingSummary?.pricing_tiers?.length ? pricingSummary.pricing_tiers : FALLBACK_TIERS;

  const currentTierAmount = pricingSummary?.current_week ? Math.round(pricingSummary.current_week.premium_amount) : null;
  const nextTierAmount = pricingSummary?.next_week ? Math.round(pricingSummary.next_week.premium_amount) : null;

  const refreshWalletLedger = async (token: string) => {
    const ledger = await apiGet<WalletLedgerResponse>("/wallet/ledger?limit=8", token);
    setWalletLedger(ledger);
    setWalletBalance(ledger.balance);
  };

  useEffect(() => {
    const run = async () => {
      const token = getAccessToken();
      if (!token) {
        router.replace("/login");
        return;
      }

      try {
        setLoading(true);
        setErrorMessage("");

        const me = await apiGet<AuthMeResponse>("/auth/me", token);
        const currentZone = zoneFromH3(me.partner.primary_zone_h3);
        const partnerCity = `${me.partner.city.charAt(0).toUpperCase()}${me.partner.city.slice(1)}`;

        setPartnerName(me.partner.full_name);
        setCity(partnerCity);
        setZone(currentZone);
        setAreaName(`${partnerCity} - Zone ${currentZone}`);
        setWalletBalance(me.partner.mock_wallet_balance);
        setUpiHandle(me.partner.upi_handle || null);

        if (me.partner.primary_zone_h3) {
          const workability = await apiGet<WorkabilityResponse>(`/grid/workability/${me.partner.primary_zone_h3}`, token);
          setWorkabilityScore(workability.workability_score);
          setWorkabilityStatus(workability.status);
          setAreaName(workability.area_name || `${partnerCity} - Zone ${currentZone}`);
          setRiskCode(workability.risk_code || fallbackRiskCode(workability.workability_score));
          setActiveSignalCount(workability.active_events.length);
          setLivePayoutRate(workability.payout_rate_hr || 0);
          setLastUpdated(formatIsoToUi(workability.timestamp));
        } else {
          setRiskCode("R1");
          setActiveSignalCount(0);
          setLivePayoutRate(0);
        }

        const [payoutHistory, summary, pricing] = await Promise.all([
          apiGet<PayoutHistoryResponse>("/payouts/my-history?limit=6", token),
          apiGet<NotificationSummaryResponse>("/auth/notifications/summary", token).catch(() => null),
          apiGet<PricingSummaryResponse>("/policies/pricing-summary", token).catch(() => null),
        ]);

        const uiPayouts = toUiPayouts(
          payoutHistory.payouts,
          currentZone,
          partnerCity,
          me.partner.id,
          me.partner.full_name,
        );
        setRecentPayouts(uiPayouts.slice(0, 3));

        if (summary) {
          setNotificationCount(summary.total);
        }
        if (pricing) {
          setPricingSummary(pricing);
        }
        await refreshWalletLedger(token);
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          router.replace("/login");
          return;
        }
        setErrorMessage(error instanceof ApiError ? error.message : "Unable to load dashboard right now.");
      } finally {
        setLoading(false);
      }
    };

    run();
  }, [router]);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      return;
    }

    const refreshSummary = async () => {
      try {
        const summary = await apiGet<NotificationSummaryResponse>("/auth/notifications/summary", token);
        setNotificationCount(summary.total);
      } catch {
        // Keep existing badge count on transient network errors.
      }
    };

    const timer = window.setInterval(refreshSummary, 30000);
    return () => window.clearInterval(timer);
  }, []);

  const handleWithdraw = async () => {
    const token = getAccessToken();
    if (!token) {
      router.replace("/login");
      return;
    }

    const amount = Number(walletAmount);
    if (!Number.isFinite(amount) || amount <= 0) {
      setWalletError("Enter a valid amount greater than zero.");
      setWalletSuccess("");
      return;
    }

    setWalletPending(true);
    setWalletError("");
    setWalletSuccess("");

    try {
      const response = await apiPost<WalletActionResponse>("/wallet/withdraw", {
        amount,
      }, token);

      await refreshWalletLedger(token);
      setWalletSuccess(`Withdraw request submitted${response.destination ? ` to ${response.destination}` : ""}.`);
    } catch (error) {
      setWalletError(error instanceof ApiError ? error.message : "Unable to process wallet action.");
    } finally {
      setWalletPending(false);
    }
  };

  const statusPillClass =
    workabilityStatus === "safe"
      ? "bg-green-500/20 text-green-300"
      : workabilityStatus === "caution"
        ? "bg-amber-500/20 text-amber-200"
        : "bg-red-500/20 text-red-200";

  const statusPillLabel =
    workabilityStatus === "safe"
      ? "SAFE TO RIDE"
      : workabilityStatus === "caution"
        ? "RISKY CONDITIONS"
        : "DISRUPTED";

  const currentPlanLabel = useMemo(() => {
    if (!pricingSummary?.current_week) {
      return "Not assigned";
    }
    const premium = Math.round(pricingSummary.current_week.premium_amount);
    const tier = pricingTiers.find((item) => Math.round(item.premium_amount) === premium);
    return tier ? `${tier.tier} · ₹${premium}/week` : `₹${premium}/week`;
  }, [pricingSummary, pricingTiers]);

  const nextPlanLabel = useMemo(() => {
    if (!pricingSummary?.next_week) {
      return "Pending recalculation";
    }
    const premium = Math.round(pricingSummary.next_week.premium_amount);
    const tier = pricingTiers.find((item) => Math.round(item.premium_amount) === premium);
    return tier ? `${tier.tier} · ₹${premium}/week` : `₹${premium}/week`;
  }, [pricingSummary, pricingTiers]);

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
      {errorMessage && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {errorMessage}
        </div>
      )}

      {/* Desktop Top Bar */}
      <div className="hidden md:flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-navy flex items-center justify-center text-sm font-bold text-white">
            {initials}
          </div>
          <span className="font-semibold text-ink-primary">{partnerName}</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="px-3 py-1.5 rounded-full bg-amber/10 text-amber text-sm font-semibold">
            Zone {zone} · {city}
          </span>
          <button onClick={() => router.push("/history")} className="relative p-2 hover:bg-gray-100 rounded-xl transition">
            <Bell className="w-5 h-5 text-ink-muted" />
            {notificationCount > 0 && (
              <span className="absolute top-1.5 right-1.5 min-w-4 h-4 px-1 bg-red-500 rounded-full text-[10px] text-white font-bold flex items-center justify-center">
                {notificationCount > 99 ? "99+" : notificationCount}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Hero Workability Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-2xl p-6 text-center"
        style={{ background: "linear-gradient(135deg, #1A3C5E, #2A5A8E)" }}
      >
        <div className="flex justify-center">
          <WorkabilityGauge score={workabilityScore} />
        </div>
        <div className="flex items-center justify-center gap-2 mt-2">
          <span className={`px-3 py-1 rounded-full text-sm font-semibold ${statusPillClass}`}>
            {statusPillLabel}
          </span>
        </div>
        <div className="flex items-center justify-center gap-3 mt-3">
          <ConnectionStatus isLive={!loading} />
          <span className="text-white/40 text-xs">·</span>
          <span className="text-white/60 text-xs">Hex Zone {zone} · Last updated {lastUpdated}</span>
        </div>
      </motion.div>

      {/* Live Zone Insight */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.08 }}
        className="bg-white rounded-2xl shadow-card p-5"
      >
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-sm font-semibold text-ink-primary">Live Zone Insight</h3>
          <button
            onClick={() => router.push("/map")}
            className="h-8 px-3 rounded-lg border border-gray-200 text-xs font-semibold text-navy hover:bg-slate-50"
          >
            Open Map
          </button>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
            <p className="text-[11px] uppercase tracking-wide text-ink-muted">Area</p>
            <p className="text-sm font-semibold text-ink-primary mt-1 inline-flex items-center gap-1.5">
              <MapPin className="w-3.5 h-3.5 text-navy" /> {areaName}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
            <p className="text-[11px] uppercase tracking-wide text-ink-muted">Risk Code</p>
            <p className="text-sm font-semibold text-ink-primary mt-1 inline-flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5 text-amber" /> {riskCode}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
            <p className="text-[11px] uppercase tracking-wide text-ink-muted">Active Signals</p>
            <p className="text-sm font-semibold text-ink-primary mt-1 inline-flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-red-500" /> {activeSignalCount}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
            <p className="text-[11px] uppercase tracking-wide text-ink-muted">Payout Rate</p>
            <p className="text-sm font-semibold text-ink-primary mt-1">₹{Math.round(livePayoutRate)}/hour</p>
          </div>
        </div>

        <p className="text-xs text-ink-muted mt-3">
          Last sync {lastUpdated}. Risk and payout values update automatically as city events change.
        </p>
      </motion.div>

      {/* Wallet Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="relative bg-white rounded-2xl shadow-card p-6 border-l-4 border-l-amber"
      >
        <MockWalletBadge />
        <p className="text-3xl font-bold text-navy">₹{Math.round(walletBalance)}</p>
        {weeklyPremium > 0 ? (
          <p className="text-sm text-ink-muted mt-1">
            This week&apos;s premium: ₹{Math.round(weeklyPremium)} · deducted Monday
          </p>
        ) : (
          <p className="text-sm text-amber-700 mt-1">
            No active weekly policy yet. Pick a plan below to activate coverage.
          </p>
        )}
        {upiHandle ? (
          <p className="text-xs text-ink-muted mt-1">Withdrawals route to {upiHandle}</p>
        ) : (
          <p className="text-xs text-amber-700 mt-1">Add UPI in profile before withdrawing.</p>
        )}

        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-4">
          <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
            <p className="text-[11px] uppercase tracking-wide text-ink-muted">Payouts</p>
            <p className="text-sm font-semibold text-ink-primary mt-1">₹{Math.round(walletLedger?.summary.payout_credits || 0)}</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
            <p className="text-[11px] uppercase tracking-wide text-ink-muted">Added</p>
            <p className="text-sm font-semibold text-ink-primary mt-1">₹{Math.round(walletLedger?.summary.manual_additions || 0)}</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
            <p className="text-[11px] uppercase tracking-wide text-ink-muted">Premium</p>
            <p className="text-sm font-semibold text-ink-primary mt-1">₹{Math.round(walletLedger?.summary.premium_deductions || 0)}</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
            <p className="text-[11px] uppercase tracking-wide text-ink-muted">Withdrawn</p>
            <p className="text-sm font-semibold text-ink-primary mt-1">₹{Math.round(walletLedger?.summary.withdrawals || 0)}</p>
          </div>
        </div>

        <div className="mt-4 rounded-xl border border-slate-200 overflow-hidden">
          <div className="px-3 py-2 bg-slate-50 text-[11px] uppercase tracking-wide text-ink-muted font-semibold">
            Recent wallet activity
          </div>
          <div className="divide-y divide-slate-100">
            {(walletLedger?.transactions || []).slice(0, 4).map((tx) => (
              <div key={tx.id} className="px-3 py-2.5 flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-ink-primary">{walletCategoryLabel(tx.category)}</p>
                  <p className="text-[11px] text-ink-muted">{formatIsoToUi(tx.created_at)} · {tx.reference}</p>
                </div>
                <p className={`text-sm font-semibold ${tx.type === "credit" ? "text-green-700" : "text-rose-700"}`}>
                  {tx.type === "credit" ? "+" : "-"}₹{Math.round(tx.amount)}
                </p>
              </div>
            ))}
            {!loading && (!walletLedger || walletLedger.transactions.length === 0) && (
              <div className="px-3 py-3 text-xs text-ink-muted">No wallet transactions yet.</div>
            )}
          </div>
        </div>

        <p className="text-xs text-ink-muted mt-4">
          Add-money is disabled for riders. Balance updates from payouts, premium deductions, and withdrawals.
        </p>

        <div className="flex gap-3 mt-3">
          <input
            type="number"
            min="1"
            step="1"
            value={walletAmount}
            onChange={(event) => setWalletAmount(event.target.value)}
            className="w-28 h-10 rounded-lg border border-gray-200 px-3 text-sm outline-none focus:ring-2 focus:ring-navy/20"
            aria-label="Wallet amount"
          />
          <button
            disabled={walletPending}
            onClick={handleWithdraw}
            className="flex-1 h-10 rounded-lg border-2 border-navy text-navy text-sm font-semibold hover:bg-navy/5 transition disabled:opacity-60"
          >
            Withdraw
          </button>
        </div>
        {walletError && <p className="mt-3 text-xs text-red-600">{walletError}</p>}
        {walletSuccess && <p className="mt-3 text-xs text-green-700">{walletSuccess}</p>}
      </motion.div>

      {/* Pricing Plans */}
      <motion.div
        id="pricing-plans"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="bg-white rounded-2xl shadow-card p-6"
      >
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <h3 className="text-sm font-semibold text-ink-primary">Risk-Linked Weekly Pricing</h3>
            <p className="text-xs text-ink-muted mt-1">
              {pricingSummary?.message || "Pricing is calculated automatically from risk levels and updates each week."}
            </p>
          </div>
          <button
            onClick={() => router.push("/profile")}
            className="h-9 px-3 rounded-lg border border-gray-200 text-xs font-semibold text-navy hover:bg-slate-50"
          >
            Open Profile
          </button>
        </div>

        <div className="grid md:grid-cols-2 gap-3 mb-4">
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
            <p className="text-[11px] uppercase tracking-wide text-ink-muted">Current Week</p>
            <p className="text-sm font-semibold text-ink-primary mt-1">{currentPlanLabel}</p>
            <p className="text-xs text-ink-muted mt-1">
              {pricingSummary?.current_week
                ? `${formatWeekRange(pricingSummary.current_week.week_start, pricingSummary.current_week.week_end)} · ${pricingSummary.current_week.risk_tier} risk`
                : "No active policy found for this week."}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
            <p className="text-[11px] uppercase tracking-wide text-ink-muted">Next Week (Projected)</p>
            <p className="text-sm font-semibold text-ink-primary mt-1">{nextPlanLabel}</p>
            <p className="text-xs text-ink-muted mt-1">
              {pricingSummary?.next_week
                ? `${formatWeekRange(pricingSummary.next_week.week_start, pricingSummary.next_week.week_end)} · ${pricingSummary.next_week.risk_tier} risk`
                : "Projection will appear after first risk evaluation."}
            </p>
          </div>
        </div>

        <div className="space-y-2">
          {pricingTiers.map((plan) => {
            const premiumAmount = Math.round(plan.premium_amount);
            const isCurrentPlan = currentTierAmount !== null && premiumAmount === currentTierAmount;
            const isProjectedPlan = nextTierAmount !== null && premiumAmount === nextTierAmount;
            const selected = isCurrentPlan || isProjectedPlan;
            return (
              <div
                key={plan.tier}
                className={`rounded-xl border px-4 py-3 flex items-center justify-between ${
                  selected ? "border-amber-300 bg-amber-50" : "border-slate-200 bg-white"
                }`}
              >
                <div>
                  <p className="text-sm font-semibold text-ink-primary">{plan.tier} · ₹{premiumAmount}/week</p>
                  <p className="text-xs text-ink-muted">Risk score band {plan.risk_band} · {plan.note}</p>
                </div>
                <div className="flex items-center gap-2">
                  {isCurrentPlan && (
                    <span className="text-[10px] font-bold uppercase tracking-wider text-green-700">Current</span>
                  )}
                  {isProjectedPlan && !isCurrentPlan && (
                    <span className="text-[10px] font-bold uppercase tracking-wider text-amber-700">Next Week</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        <p className="mt-3 text-xs text-ink-muted">
          Riders cannot manually activate plans. Pricing is auto-assigned from live risk and activity history.
        </p>
      </motion.div>

      {/* Weekly Forecast Strip */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        <h3 className="text-sm font-semibold text-ink-primary mb-3">Weekly Forecast</h3>
        <div className="flex gap-3 overflow-x-auto hide-scrollbar snap-x snap-mandatory pb-2">
          {weeklyForecast.map((day, idx) => {
            const isToday = idx === 0;
            const riskColor =
              day.risk === "high" ? "bg-red-500" :
              day.risk === "medium" ? "bg-amber" : "bg-green-500";
            return (
              <div
                key={day.day}
                className={`flex-shrink-0 w-20 rounded-xl p-3 text-center snap-start transition-all
                  ${isToday
                    ? "border-2 border-amber bg-amber-50 shadow-sm"
                    : "bg-white border border-gray-100"
                  }`}
              >
                {isToday && (
                  <span className="text-[10px] font-semibold text-amber block -mt-1 mb-1">Today</span>
                )}
                <span className="text-xs font-semibold text-ink-primary">{day.day}</span>
                <span className="text-xl block my-1">{day.weather}</span>
                <span className={`inline-block w-2 h-2 rounded-full ${riskColor} mb-1`} />
                <span className="text-xs text-ink-muted block">₹{day.amount}</span>
              </div>
            );
          })}
        </div>
      </motion.div>

      {/* Recent Payouts */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
      >
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-ink-primary">Recent Payouts</h3>
          <button onClick={() => router.push("/history")} className="text-xs font-semibold text-amber hover:text-amber-dark transition">
            View All →
          </button>
        </div>
        <div className="bg-white rounded-2xl shadow-card divide-y divide-gray-50">
          {recentPayouts.map((payout) => (
            <PayoutCard key={payout.id} payout={payout} />
          ))}
          {!loading && recentPayouts.length === 0 && (
            <div className="px-4 py-6 text-sm text-ink-muted">No payouts yet. Your protected rides will appear here.</div>
          )}
        </div>
      </motion.div>
    </div>
  );
}
