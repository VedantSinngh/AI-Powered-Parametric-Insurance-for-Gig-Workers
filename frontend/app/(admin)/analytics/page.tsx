"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  Line,
  ReferenceLine,
  LineChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { CITIES } from "@/lib/mock-data";
import { ApiError, apiGet } from "@/lib/api";
import { getAccessToken, zoneFromH3 } from "@/lib/gridguard";

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

type SummaryResponse = {
  active_partners: number;
  top_disrupted_zones: Array<{
    _id: string;
    event_count: number;
    city?: string;
  }>;
};

function formatINR(amount: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

export default function AnalyticsPage() {
  const [city, setCity] = useState("All");
  const [dateFrom, setDateFrom] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 29);
    return d.toISOString().slice(0, 10);
  });
  const [dateTo, setDateTo] = useState(() => new Date().toISOString().slice(0, 10));

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [series, setSeries] = useState<LossRatioResponse["data"]>([]);
  const [summary, setSummary] = useState<SummaryResponse | null>(null);

  useEffect(() => {
    const run = async () => {
      const token = getAccessToken();
      if (!token) {
        setError("Login required to view analytics.");
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError("");

        const params = new URLSearchParams({ granularity: "day" });
        if (city !== "All") {
          params.set("city", city.toLowerCase());
        }
        if (dateFrom) {
          params.set("date_from", `${dateFrom}T00:00:00`);
        }
        if (dateTo) {
          params.set("date_to", `${dateTo}T23:59:59`);
        }

        const [lossRes, summaryRes] = await Promise.all([
          apiGet<LossRatioResponse>(`/admin/analytics/loss-ratio?${params.toString()}`, token),
          apiGet<SummaryResponse>("/admin/analytics/summary", token),
        ]);

        setSeries(lossRes.data);
        setSummary(summaryRes);
      } catch (err) {
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          setError("Admin access required. Use an approved admin account to continue.");
        } else {
          setError(err instanceof ApiError ? err.message : "Unable to load analytics right now.");
        }
      } finally {
        setLoading(false);
      }
    };

    run();
  }, [city, dateFrom, dateTo]);

  const marginData = useMemo(
    () =>
      series.map((row) => ({
        date: row.period,
        margin: Number(((row.profit_margin || 0) * 100).toFixed(1)),
      })),
    [series],
  );

  const premiumPayoutData = useMemo(
    () =>
      series.map((row) => ({
        period: row.period,
        premium: row.total_premiums,
        payouts: row.total_payouts,
        profit: row.total_premiums - row.total_payouts,
      })),
    [series],
  );

  const profitablePeriods = useMemo(
    () => premiumPayoutData.filter((row) => row.profit >= 0).length,
    [premiumPayoutData],
  );

  const activityData = useMemo(
    () =>
      series.map((row) => ({
        date: row.period,
        payouts: row.payout_count,
        policies: row.policy_count,
      })),
    [series],
  );

  const topZonesData = useMemo(
    () =>
      (summary?.top_disrupted_zones || []).slice(0, 10).map((zone) => ({
        zone: zoneFromH3(zone._id),
        events: zone.event_count,
      })),
    [summary],
  );

  const metrics = useMemo(() => {
    const totalPremium = series.reduce((sum, row) => sum + row.total_premiums, 0);
    const totalPayouts = series.reduce((sum, row) => sum + row.total_payouts, 0);
    const marginValues = series
      .map((row) => row.profit_margin)
      .filter((value): value is number => value !== null);
    const avgProfitMargin =
      marginValues.length > 0
        ? marginValues.reduce((sum, value) => sum + value, 0) / marginValues.length
        : 0;
    const netProfit = totalPremium - totalPayouts;

    return {
      avgProfitMargin,
      totalPremium,
      totalPayouts,
      netProfit,
    };
  }, [series]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-ink-primary">Profitability Analytics</h1>
        <div className="flex gap-3">
          <input
            type="date"
            className="h-9 px-3 rounded-lg border border-gray-200 text-sm outline-none"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
          />
          <input
            type="date"
            className="h-9 px-3 rounded-lg border border-gray-200 text-sm outline-none"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
          />
          <select
            value={city}
            onChange={(e) => setCity(e.target.value)}
            className="h-9 px-3 rounded-lg border border-gray-200 text-sm outline-none"
          >
            <option value="All">All Cities</option>
            {CITIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* 2x2 Chart Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Profit Margin */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-2xl shadow-card p-6"
        >
          <h3 className="text-sm font-semibold text-ink-primary mb-4">Profit Margin</h3>
          <ResponsiveContainer width="100%" height={240} minWidth={0} minHeight={1}>
            <AreaChart data={marginData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} interval={4} />
              <YAxis tick={{ fontSize: 10 }} domain={["auto", "auto"]} unit="%" />
              <Tooltip
                contentStyle={{ borderRadius: 12, border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }}
                formatter={(value) => `${Number(value || 0)}%`}
              />
              <Area type="monotone" dataKey="margin" stroke="#16a34a" strokeWidth={2} fill="url(#greenFill)" />
              <defs>
                <linearGradient id="greenFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#16a34a" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#16a34a" stopOpacity={0} />
                </linearGradient>
              </defs>
            </AreaChart>
          </ResponsiveContainer>
        </motion.div>

        {/* Premium vs Payouts */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white rounded-2xl shadow-card p-6"
        >
          <h3 className="text-sm font-semibold text-ink-primary mb-4">Premium vs Payouts</h3>
          <ResponsiveContainer width="100%" height={240} minWidth={0} minHeight={1}>
            <BarChart data={premiumPayoutData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="period" tick={{ fontSize: 10 }} interval={4} />
              <YAxis yAxisId="amount" tick={{ fontSize: 10 }} tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}K`} />
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
          <p className="mt-3 text-xs text-ink-muted">
            Profitable periods: {profitablePeriods}/{premiumPayoutData.length || "-"}
          </p>
        </motion.div>

        {/* Activity Volume */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-white rounded-2xl shadow-card p-6"
        >
          <h3 className="text-sm font-semibold text-ink-primary mb-4">Policy vs Payout Activity</h3>
          <ResponsiveContainer width="100%" height={240} minWidth={0} minHeight={1}>
            <LineChart data={activityData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} interval={4} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip
                contentStyle={{ borderRadius: 12, border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }}
              />
              <Legend />
              <Line type="monotone" dataKey="policies" stroke="#1A3C5E" strokeWidth={2} dot={false} name="Policies" />
              <Line type="monotone" dataKey="payouts" stroke="#F5A623" strokeWidth={2} dot={false} name="Payouts" />
            </LineChart>
          </ResponsiveContainer>
        </motion.div>

        {/* Top Zones */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-white rounded-2xl shadow-card p-6"
        >
          <h3 className="text-sm font-semibold text-ink-primary mb-4">Top Disrupted Zones</h3>
          <ResponsiveContainer width="100%" height={240} minWidth={0} minHeight={1}>
            <BarChart data={topZonesData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis type="number" tick={{ fontSize: 10 }} />
              <YAxis type="category" dataKey="zone" tick={{ fontSize: 10 }} width={50} />
              <Tooltip
                contentStyle={{ borderRadius: 12, border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }}
              />
              <Bar dataKey="events" fill="#F5A623" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </motion.div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            label: "Avg Profit Margin",
            value: `${(metrics.avgProfitMargin * 100).toFixed(1)}%`,
            sub: "Filtered range",
          },
          {
            label: "Total Premium",
            value: formatINR(metrics.totalPremium),
            sub: "Filtered range",
          },
          {
            label: "Total Payouts",
            value: formatINR(metrics.totalPayouts),
            sub: "Filtered range",
          },
          {
            label: "Net Profit",
            value: formatINR(metrics.netProfit),
            sub: summary ? `${summary.active_partners.toLocaleString("en-IN")} active partners` : "Live",
          },
        ].map((metric, index) => (
          <motion.div
            key={metric.label}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 + index * 0.05 }}
            className="bg-white rounded-2xl shadow-card p-5"
          >
            <p className="text-2xl font-bold text-navy">{loading ? "..." : metric.value}</p>
            <p className="text-sm font-medium text-ink-primary mt-1">{metric.label}</p>
            <p className="text-xs text-ink-muted">{metric.sub}</p>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
