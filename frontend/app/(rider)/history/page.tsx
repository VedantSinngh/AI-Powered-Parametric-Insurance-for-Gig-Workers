"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter } from "next/navigation";
import { useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import confetti from "canvas-confetti";
import { Check } from "lucide-react";
import PayoutCard from "@/components/gridguard/PayoutCard";
import type { Payout } from "@/lib/mock-data";
import { EVENT_ICONS } from "@/lib/mock-data";
import Link from "next/link";
import { ApiError, apiGet } from "@/lib/api";
import {
  formatDurationHours,
  formatIsoToUi,
  getAccessToken,
  toEventLabel,
  toUiEventType,
  zoneFromH3,
} from "@/lib/gridguard";

const FILTERS = ["All", "Rain", "Heat", "AQI", "Traffic", "Outage"] as const;

type AuthMeResponse = {
  partner: {
    id: string;
    full_name: string;
    city: string;
    primary_zone_h3: string | null;
  };
};

type HistoryResponse = {
  payouts: Array<{
    id: string;
    amount: number;
    status: string;
    mock_reference: string;
    created_at: string;
    duration_hours: number;
    rate_per_hour: number;
    event_type?: string;
    h3_cell?: string;
  }>;
};

type WalletLedgerSummaryResponse = {
  summary: {
    payout_credits: number;
    manual_additions: number;
    premium_deductions: number;
    withdrawals: number;
  };
};

type UiHistoryPayout = Payout & {
  createdAt: string;
  ratePerHour: number;
};

function bucketForDate(isoDate: string): "Today" | "Yesterday" | "This Week" {
  const date = new Date(isoDate);
  const now = new Date();

  if (
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()
  ) {
    return "Today";
  }

  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (
    date.getFullYear() === yesterday.getFullYear() &&
    date.getMonth() === yesterday.getMonth() &&
    date.getDate() === yesterday.getDate()
  ) {
    return "Yesterday";
  }

  return "This Week";
}

function HistoryContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const payoutId = searchParams.get("payout");
  const [showSuccess, setShowSuccess] = useState(false);
  const [activeFilter, setActiveFilter] = useState<string>("All");
  const [countUp, setCountUp] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [payouts, setPayouts] = useState<UiHistoryPayout[]>([]);
  const [walletSummary, setWalletSummary] = useState<WalletLedgerSummaryResponse["summary"] | null>(null);

  const highlightedPayout = payoutId ? payouts.find((payout) => payout.id === payoutId) || null : null;

  useEffect(() => {
    if (payoutId && highlightedPayout) {
      setShowSuccess(true);
      // Count-up animation
      const target = Math.round(highlightedPayout.amount);
      let current = 0;
      const timer = setInterval(() => {
        current += Math.max(1, Math.round(target / 25));
        if (current >= target) {
          setCountUp(target);
          clearInterval(timer);
        } else {
          setCountUp(current);
        }
      }, 30);
      // Confetti
      setTimeout(() => {
        confetti({
          particleCount: 100,
          spread: 70,
          origin: { y: 0.6 },
          colors: ["#F5A623", "#1A3C5E", "#FFFFFF", "#27AE60"],
        });
      }, 500);
      return () => clearInterval(timer);
    }
  }, [payoutId, highlightedPayout]);

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
        const fallbackZone = zoneFromH3(me.partner.primary_zone_h3);
        const partnerCity = `${me.partner.city.charAt(0).toUpperCase()}${me.partner.city.slice(1)}`;

        const [response, ledger] = await Promise.all([
          apiGet<HistoryResponse>("/payouts/my-history?limit=100", token),
          apiGet<WalletLedgerSummaryResponse>("/wallet/ledger?limit=1", token).catch(() => null),
        ]);
        const mapped: UiHistoryPayout[] = response.payouts.map((payout) => {
          const uiEventType = toUiEventType(payout.event_type);
          const uiStatus = payout.status === "paid" ? "paid" : payout.status === "failed" ? "flagged" : "pending";

          return {
            id: payout.id,
            partnerId: me.partner.id,
            partnerName: me.partner.full_name,
            zone: zoneFromH3(payout.h3_cell) || fallbackZone,
            eventType: uiEventType,
            eventName: toEventLabel(payout.event_type),
            amount: Math.round(payout.amount),
            timestamp: formatIsoToUi(payout.created_at),
            status: uiStatus,
            txHash: payout.mock_reference || payout.id,
            city: partnerCity,
            duration: formatDurationHours(payout.duration_hours),
            partnerCount: undefined,
            createdAt: payout.created_at,
            ratePerHour: payout.rate_per_hour,
          };
        });

        setPayouts(mapped);
        if (ledger) {
          setWalletSummary(ledger.summary);
        }
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          router.replace("/login");
          return;
        }
        setError(err instanceof ApiError ? err.message : "Unable to load payout history.");
      } finally {
        setLoading(false);
      }
    };

    run();
  }, [router]);

  const filteredPayouts = activeFilter === "All"
    ? payouts
    : payouts.filter((payout) => payout.eventType === activeFilter.toLowerCase());

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      {/* Success Overlay */}
      <AnimatePresence>
        {showSuccess && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-navy/90 z-50 flex items-center justify-center p-4"
          >
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="text-center max-w-sm"
            >
              {/* Green check circle */}
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.3, type: "spring" }}
                className="w-20 h-20 rounded-full bg-green-500 flex items-center justify-center mx-auto mb-6"
              >
                <motion.div
                  initial={{ pathLength: 0 }}
                  animate={{ pathLength: 1 }}
                  transition={{ delay: 0.5, duration: 0.4 }}
                >
                  <Check className="w-10 h-10 text-white" strokeWidth={3} />
                </motion.div>
              </motion.div>

              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.6 }}
                className="text-4xl font-bold text-white mb-2"
              >
                ₹{countUp} Credited!
              </motion.p>

              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.8 }}
                className="text-white/60 text-sm mb-2"
              >
                Zone {highlightedPayout?.zone || "N/A"} {highlightedPayout?.eventName || "disruption"} — {highlightedPayout?.duration || "covered"}
              </motion.p>

              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.9 }}
                className="text-white/40 text-xs font-mono mb-6"
              >
                {highlightedPayout?.txHash || "-"}
              </motion.p>

              {/* Breakdown card */}
              <motion.div
                initial={{ y: 30, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 1 }}
                className="bg-white/10 backdrop-blur-md rounded-2xl p-4 mb-6 text-left"
              >
                <div className="space-y-2 text-sm">
                  {[
                    ["Event", `Zone ${highlightedPayout?.zone || "N/A"} ${highlightedPayout?.eventName || "Disruption"}`],
                    ["Duration", highlightedPayout?.duration || "-"],
                    ["Rate", `₹${Math.round(highlightedPayout?.ratePerHour || 0)}/hr`],
                    ["Total", `₹${Math.round(highlightedPayout?.amount || 0)}`],
                  ].map(([label, value]) => (
                    <div key={label} className="flex justify-between">
                      <span className="text-white/60">{label}</span>
                      <span className="text-white font-medium">{value}</span>
                    </div>
                  ))}
                </div>
              </motion.div>

              {/* Buttons */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1.2 }}
                className="flex gap-3"
              >
                <button
                  onClick={() => setShowSuccess(false)}
                  className="flex-1 h-12 rounded-full font-bold text-white text-sm"
                  style={{ background: "linear-gradient(135deg, #F5A623, #D4891A)" }}
                >
                  View History
                </button>
                <Link
                  href="/dashboard"
                  className="flex-1 h-12 rounded-full border-2 border-white/30 text-white font-bold text-sm flex items-center justify-center hover:bg-white/10 transition"
                >
                  Back to Home
                </Link>
              </motion.div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Page Header */}
      <h1 className="text-xl font-bold text-ink-primary mb-4">Payout History</h1>

      {error && (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Filter Chips */}
      {walletSummary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-5">
          <div className="rounded-xl border border-slate-200 bg-white px-3 py-2">
            <p className="text-[11px] uppercase tracking-wide text-ink-muted">Payouts</p>
            <p className="text-sm font-semibold text-ink-primary mt-1">₹{Math.round(walletSummary.payout_credits)}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white px-3 py-2">
            <p className="text-[11px] uppercase tracking-wide text-ink-muted">Added</p>
            <p className="text-sm font-semibold text-ink-primary mt-1">₹{Math.round(walletSummary.manual_additions)}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white px-3 py-2">
            <p className="text-[11px] uppercase tracking-wide text-ink-muted">Premium</p>
            <p className="text-sm font-semibold text-ink-primary mt-1">₹{Math.round(walletSummary.premium_deductions)}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white px-3 py-2">
            <p className="text-[11px] uppercase tracking-wide text-ink-muted">Withdrawn</p>
            <p className="text-sm font-semibold text-ink-primary mt-1">₹{Math.round(walletSummary.withdrawals)}</p>
          </div>
        </div>
      )}

      {/* Filter Chips */}
      <div className="flex gap-2 mb-6 overflow-x-auto hide-scrollbar">
        {FILTERS.map((filter) => (
          <button
            key={filter}
            onClick={() => setActiveFilter(filter)}
            className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-all
              ${activeFilter === filter
                ? "bg-navy text-white shadow-sm"
                : "bg-white text-ink-muted border border-gray-200 hover:border-navy/30"
              }`}
          >
            {filter !== "All" && <span className="mr-1">{EVENT_ICONS[filter.toLowerCase()]}</span>}
            {filter}
          </button>
        ))}
      </div>

      {/* Payout List */}
      <div className="space-y-4">
        {loading && (
          <div className="text-sm text-ink-muted">Loading payout history...</div>
        )}

        {["Today", "Yesterday", "This Week"].map((group) => {
          const groupPayouts = filteredPayouts.filter((payout) => {
            return bucketForDate(payout.createdAt) === group;
          });
          if (groupPayouts.length === 0) return null;
          return (
            <div key={group}>
              <h3 className="text-xs font-semibold text-ink-muted uppercase tracking-wider mb-2">
                {group}
              </h3>
              <div className="bg-white rounded-2xl shadow-card divide-y divide-gray-50">
                {groupPayouts.map((payout) => (
                  <PayoutCard key={payout.id} payout={payout} />
                ))}
              </div>
            </div>
          );
        })}

        {!loading && filteredPayouts.length === 0 && (
          <div className="rounded-xl border border-dashed border-gray-300 bg-white p-6 text-sm text-ink-muted">
            No payouts found for this filter yet.
          </div>
        )}
      </div>
    </div>
  );
}

export default function HistoryPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-ink-muted">Loading...</div>}>
      <HistoryContent />
    </Suspense>
  );
}
