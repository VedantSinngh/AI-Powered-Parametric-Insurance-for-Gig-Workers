"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ShieldCheck, AlertCircle, TrendingUp, Search, Info } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Cell, Legend } from "recharts";
import { ApiError, apiGet, apiPatch } from "@/lib/api";
import { formatIsoToUi, getAccessToken, zoneFromH3 } from "@/lib/gridguard";

type FraudFlag = {
  id: string;
  partner_id: string;
  partner_name?: string;
  partner_email?: string;
  city?: string;
  primary_zone_h3?: string | null;
  flag_type: string;
  severity: "info" | "warning" | "critical";
  rule_triggered: string;
  fraud_score: number;
  checks_failed: string[];
  status: "pending" | "dismissed" | "escalated" | "confirmed";
  flagged_at: string;
  payout_amount?: number;
};

type FraudFlagsResponse = {
  flags: FraudFlag[];
  total: number;
};

const STATUS_FILTERS = ["all", "pending", "escalated", "confirmed", "dismissed"] as const;
const SEVERITY_FILTERS = ["all", "critical", "warning", "info"] as const;

function normalizeFraudScore(score: number): number {
  const normalized = score <= 1 ? score * 100 : score;
  return Math.max(0, Math.min(100, normalized));
}

function prettifyToken(rawValue: string): string {
  return rawValue
    .split("_")
    .map((token) => token.charAt(0).toUpperCase() + token.slice(1))
    .join(" ");
}

function severityPill(severity: FraudFlag["severity"]): string {
  if (severity === "critical") {
    return "bg-red-100 text-red-700";
  }
  if (severity === "warning") {
    return "bg-amber-100 text-amber-700";
  }
  return "bg-slate-100 text-slate-600";
}

export default function FraudPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<(typeof STATUS_FILTERS)[number]>("all");
  const [severityFilter, setSeverityFilter] = useState<(typeof SEVERITY_FILTERS)[number]>("all");
  const [flags, setFlags] = useState<FraudFlag[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [updatingFlagId, setUpdatingFlagId] = useState<string | null>(null);
  const riskChartHostRef = useRef<HTMLDivElement | null>(null);
  const [riskChartWidth, setRiskChartWidth] = useState(0);

  const loadFlags = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      setError("Login required to view fraud analytics.");
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError("");

      const params = new URLSearchParams({
        limit: "100",
        offset: "0",
      });
      if (statusFilter !== "all") {
        params.set("status", statusFilter);
      }
      if (severityFilter !== "all") {
        params.set("severity", severityFilter);
      }
      if (search.trim()) {
        params.set("search", search.trim());
      }

      const response = await apiGet<FraudFlagsResponse>(`/fraud/flags?${params.toString()}`, token);
      setFlags(response.flags);
      setTotal(response.total);
    } catch (err) {
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        setError("Admin access required. Use an approved admin account to continue.");
      } else {
        setError(err instanceof ApiError ? err.message : "Unable to load fraud flags.");
      }
    } finally {
      setLoading(false);
    }
  }, [search, severityFilter, statusFilter]);

  useEffect(() => {
    loadFlags();
  }, [loadFlags]);

  useEffect(() => {
    const host = riskChartHostRef.current;
    if (!host) {
      return;
    }

    const updateWidth = () => {
      setRiskChartWidth(Math.max(0, Math.floor(host.clientWidth)));
    };

    updateWidth();
    const observer = new ResizeObserver(updateWidth);
    observer.observe(host);

    return () => observer.disconnect();
  }, []);

  const riskBuckets = useMemo(() => {
    const ranges = [
      { range: "0-20", min: 0, max: 20, count: 0 },
      { range: "21-40", min: 21, max: 40, count: 0 },
      { range: "41-60", min: 41, max: 60, count: 0 },
      { range: "61-80", min: 61, max: 80, count: 0 },
      { range: "81-100", min: 81, max: 100, count: 0 },
    ];

    for (const flag of flags) {
      const score = normalizeFraudScore(flag.fraud_score);
      const bucket = ranges.find((candidate) => score >= candidate.min && score <= candidate.max);
      if (bucket) {
        bucket.count += 1;
      }
    }

    return ranges.map(({ range, count }) => ({ range, count }));
  }, [flags]);

  const stats = useMemo(() => {
    const highRiskClaims = flags.filter((flag) => normalizeFraudScore(flag.fraud_score) >= 80).length;
    const pendingReview = flags.filter((flag) => flag.status === "pending" || flag.status === "escalated").length;
    const fraudSavings = flags
      .filter((flag) => flag.status === "confirmed")
      .reduce((sum, flag) => sum + Number(flag.payout_amount || 0), 0);

    return {
      highRiskClaims,
      pendingReview,
      fraudSavings,
      savingsProgress: Math.min(100, (fraudSavings / 1250000) * 100),
    };
  }, [flags]);

  const handleStatusUpdate = async (
    flagId: string,
    nextStatus: FraudFlag["status"],
  ) => {
    const token = getAccessToken();
    if (!token) {
      setError("Login required to update fraud flags.");
      return;
    }

    try {
      setUpdatingFlagId(flagId);
      await apiPatch(
        `/fraud/flags/${flagId}`,
        {
          status: nextStatus,
          reviewer_note: `Status updated to ${nextStatus} from dashboard`,
        },
        token,
      );

      setFlags((currentFlags) =>
        currentFlags.map((flag) =>
          flag.id === flagId
            ? { ...flag, status: nextStatus }
            : flag,
        ),
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to update fraud flag.");
    } finally {
      setUpdatingFlagId(null);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-navy flex items-center gap-2">
            <ShieldCheck className="w-6 h-6 text-green-600" />
            Fraud Detection Center
          </h1>
          <p className="text-sm text-ink-secondary">Real-time analysis of claim patterns and anomaly detection</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-secondary" />
            <input
              type="text"
              placeholder="Search Partner ID..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              className="pl-10 pr-4 py-2 bg-white border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-navy/10"
            />
          </div>
          <select
            value={severityFilter}
            onChange={(event) => setSeverityFilter(event.target.value as (typeof SEVERITY_FILTERS)[number])}
            className="px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm"
          >
            {SEVERITY_FILTERS.map((severity) => (
              <option key={severity} value={severity}>
                {severity === "all" ? "All Severities" : prettifyToken(severity)}
              </option>
            ))}
          </select>
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value as (typeof STATUS_FILTERS)[number])}
            className="px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm"
          >
            {STATUS_FILTERS.map((status) => (
              <option key={status} value={status}>
                {status === "all" ? "All Statuses" : prettifyToken(status)}
              </option>
            ))}
          </select>
          <button
            onClick={loadFlags}
            className="px-4 py-2 bg-navy text-white rounded-lg text-sm font-medium hover:bg-navy/90 transition-colors"
          >
            Run Manual Audit
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Risk Distribution Chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="lg:col-span-2 bg-white rounded-2xl shadow-card p-6 border border-slate-100"
        >
          <div className="flex items-center justify-between mb-8">
            <h2 className="font-semibold text-navy">Claim Anomaly Detection</h2>
            <div className="flex items-center gap-2 text-xs font-medium text-ink-secondary bg-slate-100 px-2 py-1 rounded">
              <TrendingUp className="w-3 h-3" />
              +4% vs Last Month
            </div>
          </div>
          <div ref={riskChartHostRef} className="h-[300px]">
            {riskChartWidth > 0 && (
              <BarChart width={riskChartWidth} height={300} data={riskBuckets}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="range" tick={{ fontSize: 12, fill: "#64748b" }} axisLine={false} tickLine={false} />
                <YAxis hide />
                <Bar dataKey="count" radius={[6, 6, 0, 0]} barSize={40}>
                  {riskBuckets.map((entry, index) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={index > 3 ? "#ef4444" : index > 2 ? "#f59e0b" : "#1A3C5E"}
                      fillOpacity={0.8 + (index * 0.05)}
                    />
                  ))}
                </Bar>
                <Legend />
              </BarChart>
            )}
          </div>
        </motion.div>

        {/* Flagged Claims Stats */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="space-y-6"
        >
          <div className="bg-white rounded-2xl shadow-card p-6 border border-slate-100 flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-red-100 flex items-center justify-center">
              <AlertCircle className="w-6 h-6 text-red-600" />
            </div>
            <div>
              <p className="text-xs font-medium text-ink-secondary uppercase tracking-wider">High Risk Claims</p>
              <p className="text-2xl font-bold text-navy">{loading ? "..." : stats.highRiskClaims}</p>
              <p className="text-xs text-red-600 font-medium mt-1">Score 80+ anomalies</p>
            </div>
          </div>

          <div className="bg-white rounded-2xl shadow-card p-6 border border-slate-100 flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-amber-100 flex items-center justify-center">
              <Info className="w-6 h-6 text-amber-600" />
            </div>
            <div>
              <p className="text-xs font-medium text-ink-secondary uppercase tracking-wider">Pending Review</p>
              <p className="text-2xl font-bold text-navy">{loading ? "..." : stats.pendingReview}</p>
              <p className="text-xs text-ink-secondary mt-1">SLA queue currently open</p>
            </div>
          </div>

          <div className="bg-navy rounded-2xl p-6 text-white overflow-hidden relative">
            <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -mr-16 -mt-16 blur-2xl" />
            <p className="text-sm font-medium opacity-80 mb-1">Fraud Savings (MTD)</p>
            <p className="text-3xl font-bold">₹{Math.round(stats.fraudSavings).toLocaleString("en-IN")}</p>
            <div className="mt-4 flex items-center gap-2">
              <div className="flex-1 h-1 bg-white/20 rounded-full overflow-hidden">
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: `${stats.savingsProgress}%` }}
                  className="h-full bg-green-400" 
                />
              </div>
              <span className="text-xs font-bold">{Math.round(stats.savingsProgress)}% of Target</span>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Flagged Partners Table */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="bg-white rounded-2xl shadow-card border border-slate-100 overflow-hidden"
      >
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h2 className="font-semibold text-navy">Claims Under Investigation</h2>
          <span className="text-sm text-ink-secondary">{total.toLocaleString("en-IN")} total flags</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50">
                <th className="px-6 py-3 text-xs font-bold text-ink-secondary uppercase tracking-wider">Partner</th>
                <th className="px-6 py-3 text-xs font-bold text-ink-secondary uppercase tracking-wider">Zone</th>
                <th className="px-6 py-3 text-xs font-bold text-ink-secondary uppercase tracking-wider">Rule Trigger</th>
                <th className="px-6 py-3 text-xs font-bold text-ink-secondary uppercase tracking-wider">Risk Score</th>
                <th className="px-6 py-3 text-xs font-bold text-ink-secondary uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-xs font-bold text-ink-secondary uppercase tracking-wider">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              <AnimatePresence>
                {flags.map((flag, idx) => {
                  const score = normalizeFraudScore(flag.fraud_score);
                  return (
                  <motion.tr 
                    key={flag.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.1 * idx }}
                    className="hover:bg-slate-50 transition-colors"
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-xs font-bold text-navy">
                          {(flag.partner_name || flag.partner_id)
                            .split(" ")
                            .map((part) => part[0])
                            .join("")
                            .slice(0, 2)
                            .toUpperCase()}
                        </div>
                        <div>
                          <p className="text-sm font-bold text-navy">{flag.partner_name || "Unknown Partner"}</p>
                          <p className="text-xs text-ink-secondary">ID: {flag.partner_id}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-1 bg-slate-100 rounded text-xs font-mono font-medium">
                        {zoneFromH3(flag.primary_zone_h3)}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div>
                        <p className="text-sm font-medium text-navy">{prettifyToken(flag.flag_type)}</p>
                        <p className="text-xs text-ink-secondary">{flag.rule_triggered || `${flag.checks_failed.length} checks failed`}</p>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div className="flex-1 w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                          <div 
                            className={`h-full rounded-full ${score >= 80 ? "bg-red-500" : "bg-amber-500"}`}
                            style={{ width: `${score}%` }}
                          />
                        </div>
                        <span className="text-xs font-bold text-navy">{Math.round(score)}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-col gap-1">
                        <span className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase w-fit ${severityPill(flag.severity)}`}>
                          {flag.severity}
                        </span>
                        <span className="text-xs text-ink-secondary">{formatIsoToUi(flag.flagged_at)}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <select
                        value={flag.status}
                        disabled={updatingFlagId === flag.id}
                        onChange={(event) =>
                          handleStatusUpdate(flag.id, event.target.value as FraudFlag["status"])
                        }
                        className="text-xs font-bold text-navy px-2 py-1.5 border border-navy/20 rounded-lg bg-white"
                      >
                        <option value="pending">Pending</option>
                        <option value="escalated">Escalated</option>
                        <option value="confirmed">Confirmed</option>
                        <option value="dismissed">Dismissed</option>
                      </select>
                    </td>
                  </motion.tr>
                );
                })}
              </AnimatePresence>

              {!loading && flags.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-sm text-ink-muted text-center">
                    No fraud flags found for this filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </motion.div>
    </div>
  );
}
