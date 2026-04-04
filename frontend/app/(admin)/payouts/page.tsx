"use client";

import { useMemo, useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { Download } from "lucide-react";
import ZoneHexBadge from "@/components/gridguard/ZoneHexBadge";
import { EVENT_ICONS } from "@/lib/mock-data";
import { ApiError, apiGet } from "@/lib/api";
import {
  formatDurationHours,
  formatIsoToUi,
  getAccessToken,
  toUiEventType,
  zoneFromH3,
} from "@/lib/gridguard";

type RecentPayoutsResponse = {
  payouts: Array<{
    id: string;
    partner_name: string;
    city: string;
    event_type: string;
    h3_cell: string;
    amount: number;
    duration_hours: number;
    status: string;
    provider?: string;
    provider_status?: string;
    failure_reason?: string;
    reference: string;
    created_at: string;
  }>;
};

type TimelinePayout = {
  id: string;
  zone: string;
  eventType: "rain" | "heat" | "aqi" | "outage" | "traffic";
  eventName: string;
  amount: number;
  city: string;
  status: string;
  txHash: string;
  timestamp: string;
  duration: string;
  provider: string;
  providerStatus: string;
  failureReason?: string;
};

function formatINR(amount: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

export default function PayoutsPage() {
  const searchParams = useSearchParams();
  const [eventFilter, setEventFilter] = useState("All");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [items, setItems] = useState<TimelinePayout[]>([]);

  useEffect(() => {
    const run = async () => {
      const token = getAccessToken();
      if (!token) {
        setError("Login required to view payouts.");
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError("");

        const params = new URLSearchParams({ limit: "200" });
        const search = searchParams.get("search");
        if (search) {
          params.set("search", search);
        }

        const response = await apiGet<RecentPayoutsResponse>(`/admin/payouts/recent?${params.toString()}`, token);
        const mapped: TimelinePayout[] = response.payouts.map((payout) => {
          const eventType = toUiEventType(payout.event_type);

          return {
            id: payout.id,
            zone: zoneFromH3(payout.h3_cell),
            eventType,
            eventName: payout.event_type ? payout.event_type.replaceAll("_", " ") : "Unknown Event",
            amount: payout.amount,
            city: payout.city || "Unknown",
            status: payout.status,
            txHash: payout.reference || payout.id,
            timestamp: formatIsoToUi(payout.created_at),
            duration: formatDurationHours(payout.duration_hours),
            provider: payout.provider || "mock",
            providerStatus: payout.provider_status || payout.status,
            failureReason: payout.failure_reason,
          };
        });

        setItems(mapped);
      } catch (err) {
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          setError("Admin access required. Use an approved admin account to continue.");
        } else {
          setError(err instanceof ApiError ? err.message : "Unable to load payout timeline.");
        }
      } finally {
        setLoading(false);
      }
    };

    run();
  }, [searchParams]);

  const filtered = useMemo(
    () =>
      eventFilter === "All"
        ? items
        : items.filter((item) => item.eventType === eventFilter.toLowerCase()),
    [eventFilter, items],
  );

  const summary = useMemo(() => {
    if (filtered.length === 0) {
      return {
        totalPaid: 0,
        avgPayout: 0,
        largest: 0,
        paidToday: 0,
      };
    }

    const totalPaid = filtered.reduce((sum, item) => sum + item.amount, 0);
    const largest = filtered.reduce((max, item) => Math.max(max, item.amount), 0);
    const paidToday = filtered.filter((item) => item.timestamp.startsWith("Today")).length;

    return {
      totalPaid,
      avgPayout: totalPaid / filtered.length,
      largest,
      paidToday,
    };
  }, [filtered]);

  const exportCSV = () => {
    const header = "Zone,Event,City,Amount,Timestamp,TxHash,Duration,Status,Provider,ProviderStatus\n";
    const rows = filtered
      .map(
        (item) =>
          `${item.zone},${item.eventName},${item.city},${item.amount},${item.timestamp},${item.txHash},${item.duration},${item.status},${item.provider},${item.providerStatus}`,
      )
      .join("\n");

    const blob = new Blob([header + rows], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "gridguard-payouts.csv";
    a.click();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-ink-primary">Payouts</h1>
        <button
          onClick={exportCSV}
          className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-navy text-white text-sm font-medium hover:bg-navy-dark transition"
        >
          <Download className="w-4 h-4" /> Export CSV
        </button>
      </div>

      {error && (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Summary */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[
          { label: "Total Paid", value: formatINR(summary.totalPaid), color: "text-navy" },
          { label: "Avg Payout", value: formatINR(summary.avgPayout), color: "text-ink-primary" },
          { label: "Largest", value: formatINR(summary.largest), color: "text-amber" },
          { label: "Today", value: String(summary.paidToday), color: "text-success" },
        ].map((card) => (
          <motion.div
            key={card.label}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white rounded-2xl shadow-card p-5"
          >
            <p className={`text-2xl font-bold ${card.color}`}>{loading ? "..." : card.value}</p>
            <p className="text-xs text-ink-muted mt-1">{card.label}</p>
          </motion.div>
        ))}
      </div>

      {/* Filter chips */}
      <div className="flex gap-2 mb-6">
        {["All", "Rain", "Heat", "AQI", "Traffic", "Outage"].map((type) => (
          <button
            key={type}
            onClick={() => setEventFilter(type)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              eventFilter === type
                ? "bg-navy text-white"
                : "bg-white text-ink-muted border border-gray-200"
            }`}
          >
            {type}
          </button>
        ))}
      </div>

      {/* Timeline */}
      <div className="relative">
        <motion.div
          initial={{ height: 0 }}
          animate={{ height: "100%" }}
          transition={{ duration: 0.8 }}
          className="absolute left-6 top-2 w-0.5 bg-gray-200"
        />
        <div className="space-y-6">
          {filtered.map((item, index) => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.04 }}
              className="relative pl-14"
            >
              <div className="absolute left-4 top-4 w-5 h-5 rounded-full bg-white border-2 border-amber flex items-center justify-center z-10">
                <span className="text-xs">{EVENT_ICONS[item.eventType]}</span>
              </div>
              <div className="bg-white rounded-2xl shadow-card p-5 hover:shadow-card-hover transition-shadow">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <ZoneHexBadge zone={item.zone} />
                      <span className="text-ink-primary font-semibold">{item.eventName}</span>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase bg-slate-100 text-slate-700">{item.provider}</span>
                    </div>
                    <p className="text-xs text-ink-muted">
                      {item.city} · {item.timestamp}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-navy">{formatINR(item.amount)}</p>
                    <p className="text-xs text-ink-muted capitalize">{item.status} · {item.providerStatus}</p>
                  </div>
                </div>
                <div className="flex items-center justify-between pt-3 border-t border-gray-50">
                  <span className="text-xs font-mono text-ink-muted">{item.txHash}</span>
                  <span className="text-xs text-ink-muted">{item.duration}</span>
                </div>
                {item.failureReason && (
                  <p className="mt-2 text-xs text-red-600">Failure: {item.failureReason}</p>
                )}
              </div>
            </motion.div>
          ))}

          {!loading && filtered.length === 0 && (
            <div className="rounded-2xl border border-dashed border-gray-300 bg-white p-6 text-sm text-ink-muted text-center">
              No payouts found for this filter.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
