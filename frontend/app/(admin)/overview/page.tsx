"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Users, CreditCard, TrendingUp, AlertTriangle } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Area, AreaChart, Legend, Line, ReferenceLine,
} from "recharts";
import KPICard from "@/components/gridguard/KPICard";
import ZoneHexBadge from "@/components/gridguard/ZoneHexBadge";
import Link from "next/link";
import { ApiError, apiGet } from "@/lib/api";
import { formatIsoToUi, getAccessToken, zoneFromH3 } from "@/lib/gridguard";

type SummaryResponse = {
  active_partners: number;
  payouts_today_amount: number;
  payouts_today_count: number;
  loss_ratio_30d: number;
  net_profit_30d: number;
  profit_margin_30d: number;
  fraud_flags_pending: number;
  premium_collected_this_week: number;
  top_disrupted_zones: Array<{
    _id: string;
    event_count: number;
    avg_severity: number;
    city?: string;
  }>;
  system_health: {
    ws_connections: number;
    redis_ping_ms: number;
    db_ping_ms: number;
  };
};

type LossRatioResponse = {
  data: Array<{
    period: string;
    total_payouts: number;
    total_premiums: number;
    net_profit: number;
    profit_margin: number | null;
    payout_count: number;
    policy_count: number;
    loss_ratio: number | null;
  }>;
};

type RecentPayoutsResponse = {
  payouts: Array<{
    id: string;
    partner_name: string;
    amount: number;
    h3_cell: string;
    status: string;
    created_at: string;
  }>;
};

function formatINR(amount: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

export default function OverviewPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [dailyLoss, setDailyLoss] = useState<LossRatioResponse["data"]>([]);
  const [weeklyLoss, setWeeklyLoss] = useState<LossRatioResponse["data"]>([]);
  const [recentPayouts, setRecentPayouts] = useState<RecentPayoutsResponse["payouts"]>([]);

  useEffect(() => {
    const run = async () => {
      const token = getAccessToken();
      if (!token) {
        setError("Login required to view admin analytics.");
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError("");

        const [summaryRes, dailyRes, weeklyRes, payoutsRes] = await Promise.all([
          apiGet<SummaryResponse>("/admin/analytics/summary", token),
          apiGet<LossRatioResponse>("/admin/analytics/loss-ratio?granularity=day", token),
          apiGet<LossRatioResponse>("/admin/analytics/loss-ratio?granularity=week", token),
          apiGet<RecentPayoutsResponse>("/admin/payouts/recent?limit=8", token),
        ]);

        setSummary(summaryRes);
        setDailyLoss(dailyRes.data);
        setWeeklyLoss(weeklyRes.data);
        setRecentPayouts(payoutsRes.payouts);
      } catch (err) {
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          setError("Admin access required. Use an approved admin account to continue.");
        } else {
          setError(err instanceof ApiError ? err.message : "Unable to load overview analytics.");
        }
      } finally {
        setLoading(false);
      }
    };

    run();
  }, []);

  const profitTrendData = useMemo(
    () => dailyLoss.slice(-30).map((row) => ({
      date: row.period,
      net_profit: Number((row.net_profit || 0).toFixed(2)),
    })),
    [dailyLoss],
  );

  const premiumPayoutData = useMemo(
    () => weeklyLoss.slice(-8).map((row) => ({
      week: row.period,
      premium: row.total_premiums,
      payouts: row.total_payouts,
      profit: row.total_premiums - row.total_payouts,
    })),
    [weeklyLoss],
  );

  const profitability = useMemo(() => {
    const totalWeeks = premiumPayoutData.length;
    const profitableWeeks = premiumPayoutData.filter((row) => row.profit >= 0).length;
    return {
      profitableWeeks,
      totalWeeks,
    };
  }, [premiumPayoutData]);

  const sparklinePayouts = premiumPayoutData.slice(-10).map((row) => Math.round(row.payouts));
  const sparklinePremiums = premiumPayoutData.slice(-10).map((row) => Math.round(row.premium));
  const sparklineProfit = dailyLoss.slice(-10).map((row) => Math.round(row.net_profit || 0));
  const sparklineFlags = summary
    ? [
      Math.max(summary.fraud_flags_pending - 3, 0),
      Math.max(summary.fraud_flags_pending - 2, 0),
      Math.max(summary.fraud_flags_pending - 1, 0),
      summary.fraud_flags_pending,
    ]
    : [];

  return (
    <div className="flex gap-6">
      {/* Main Content */}
      <div className="flex-1 min-w-0">
        {error && (
          <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
          <KPICard
            title="Active Partners"
            value={summary ? summary.active_partners.toLocaleString("en-IN") : "-"}
            change={loading ? "Loading" : "Live"}
            changeType="positive"
            icon={Users}
            iconColor="bg-blue-100 text-blue-600"
            sparklineData={sparklinePremiums}
          />
          <KPICard
            title="Payouts Today"
            value={summary ? formatINR(summary.payouts_today_amount) : "-"}
            change={summary ? `${summary.payouts_today_count} paid` : "Loading"}
            changeType="positive"
            icon={CreditCard}
            iconColor="bg-green-100 text-green-600"
            sparklineData={sparklinePayouts}
          />
          <KPICard
            title="Net Profit (30d)"
            value={summary ? formatINR(summary.net_profit_30d) : "-"}
            change={summary ? `${(summary.profit_margin_30d * 100).toFixed(1)}% margin` : "Loading"}
            changeType={summary && summary.net_profit_30d < 0 ? "negative" : "positive"}
            icon={TrendingUp}
            iconColor="bg-emerald-100 text-emerald-700"
            sparklineData={sparklineProfit}
          />
          <KPICard
            title="Fraud Flags Pending"
            value={summary ? String(summary.fraud_flags_pending) : "-"}
            change={loading ? "Loading" : "Needs review"}
            changeType="positive"
            icon={AlertTriangle}
            iconColor="bg-red-100 text-red-600"
            sparklineData={sparklineFlags}
          />
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-white rounded-2xl shadow-card p-6"
          >
            <h3 className="text-sm font-semibold text-ink-primary mb-4">Net Profit Trend (30 Days)</h3>
            <ResponsiveContainer width="100%" height={220} minWidth={0} minHeight={1}>
              <AreaChart data={profitTrendData}>
                <defs>
                  <linearGradient id="colorProfit" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#16a34a" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#16a34a" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="date" hide />
                <YAxis tick={{ fontSize: 10 }} tickFormatter={(value) => `₹${Math.round(Number(value) / 1000)}K`} />
                <Tooltip
                  contentStyle={{ borderRadius: 12, border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }}
                  formatter={(value) => formatINR(Number(value || 0))}
                />
                <Area type="monotone" dataKey="net_profit" stroke="#16a34a" fillOpacity={1} fill="url(#colorProfit)" />
              </AreaChart>
            </ResponsiveContainer>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="bg-white rounded-2xl shadow-card p-6"
          >
            <h3 className="text-sm font-semibold text-ink-primary mb-4">Premium vs Payouts (8 Weeks)</h3>
            <ResponsiveContainer width="100%" height={220} minWidth={0} minHeight={1}>
              <BarChart data={premiumPayoutData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="week" tick={{ fontSize: 10 }} />
                <YAxis yAxisId="amount" tick={{ fontSize: 10 }} tickFormatter={(v) => `₹${(v/1000).toFixed(0)}K`} />
                <YAxis
                  yAxisId="profit"
                  orientation="right"
                  tick={{ fontSize: 10 }}
                  tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}K`}
                />
                <Tooltip
                  contentStyle={{ borderRadius: 12, border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }}
                  formatter={(value, name) => {
                    const amount = Number(value || 0);
                    if (name === "Net Profit") {
                      return [
                        `${formatINR(Math.abs(amount))} ${amount >= 0 ? "profit" : "loss"}`,
                        name,
                      ];
                    }
                    return [formatINR(amount), name];
                  }}
                />
                <Legend />
                <ReferenceLine yAxisId="profit" y={0} stroke="#94a3b8" strokeDasharray="4 4" />
                <Bar yAxisId="amount" dataKey="premium" fill="#1A3C5E" radius={[4, 4, 0, 0]} name="Premium" />
                <Bar yAxisId="amount" dataKey="payouts" fill="#F5A623" radius={[4, 4, 0, 0]} name="Payouts" />
                <Line
                  yAxisId="profit"
                  type="monotone"
                  dataKey="profit"
                  stroke="#16a34a"
                  strokeWidth={2}
                  dot={{ r: 2 }}
                  name="Net Profit"
                />
              </BarChart>
            </ResponsiveContainer>
            <div className="mt-3 flex items-center justify-between text-xs text-ink-muted">
              <p>
                Profitable weeks: {profitability.profitableWeeks}/{profitability.totalWeeks || "-"}
              </p>
              <p>
                Rolling margin: {summary ? `${(summary.profit_margin_30d * 100).toFixed(1)}%` : "-"}
              </p>
            </div>
          </motion.div>
        </div>

        {/* Recent Payouts Table */}
        <div className="bg-white rounded-2xl shadow-card overflow-hidden">
          <div className="p-6 border-b border-slate-100 flex items-center justify-between">
            <h3 className="font-semibold text-ink-primary">Recent Automated Payouts</h3>
            <Link href="/payouts" className="text-sm text-navy font-semibold">View All</Link>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-slate-50 text-xs font-bold text-ink-secondary uppercase tracking-wider">
                  <th className="px-6 py-3">Partner</th>
                  <th className="px-6 py-3">Amount</th>
                  <th className="px-6 py-3">Zone</th>
                  <th className="px-6 py-3">Time</th>
                  <th className="px-6 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {recentPayouts.map((payout) => (
                  <tr key={payout.id} className="text-sm">
                    <td className="px-6 py-4 font-medium text-ink-primary">{payout.partner_name || "Unknown"}</td>
                    <td className="px-6 py-4 font-bold text-green-600">{formatINR(payout.amount)}</td>
                    <td className="px-6 py-4">
                      <ZoneHexBadge zone={zoneFromH3(payout.h3_cell)} />
                    </td>
                    <td className="px-6 py-4 text-ink-secondary">{formatIsoToUi(payout.created_at)}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-bold ${
                        payout.status === "paid"
                          ? "bg-green-100 text-green-700"
                          : payout.status === "failed"
                            ? "bg-red-100 text-red-700"
                            : "bg-amber-100 text-amber-700"
                      }`}>{payout.status}</span>
                    </td>
                  </tr>
                ))}
                {!loading && recentPayouts.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-sm text-ink-muted text-center">
                      No recent payouts available.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Sidebar - Active Events */}
      <div className="hidden lg:block w-80 space-y-6">
        <div className="bg-white rounded-2xl shadow-card p-6">
          <h3 className="font-semibold text-ink-primary mb-4 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-500" />
            Active Climate Events
          </h3>
          <div className="space-y-4">
            {(summary?.top_disrupted_zones || []).slice(0, 5).map((event) => (
              <div key={event._id} className="flex flex-col gap-2 p-3 bg-slate-50 rounded-xl border border-slate-100">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-navy bg-white px-2 py-1 rounded-lg border border-slate-200">
                    Zone {zoneFromH3(event._id)}
                  </span>
                  <span className="text-[10px] text-ink-secondary">avg sev {event.avg_severity.toFixed(2)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium flex items-center gap-1 text-ink-primary">
                    {event.city || "unknown city"}
                  </span>
                  <span className="text-xs font-bold text-navy">{event.event_count} active events</span>
                </div>
              </div>
            ))}
            {!loading && (summary?.top_disrupted_zones || []).length === 0 && (
              <p className="text-sm text-ink-muted">No active disruption zones right now.</p>
            )}
          </div>
          <Link href="/admin-live-map" className="w-full mt-4 py-3 text-sm font-bold text-navy border border-navy/10 rounded-xl hover:bg-slate-50 transition-colors block text-center">
            Open Event Map
          </Link>
        </div>

        <div className="bg-navy rounded-2xl p-6 text-white relative overflow-hidden">
          <div className="absolute -right-4 -bottom-4 w-24 h-24 bg-white/10 rounded-full blur-xl" />
          <h3 className="font-bold relative z-10">Smart Audits</h3>
          <p className="text-xs opacity-70 mt-1 mb-4 relative z-10">We&apos;ve flagged 12 anomalies requiring manual review today.</p>
          <Link href="/fraud" className="inline-block px-4 py-2 bg-white text-navy text-xs font-bold rounded-lg relative z-10">
            Start Review
          </Link>
        </div>
      </div>
    </div>
  );
}
