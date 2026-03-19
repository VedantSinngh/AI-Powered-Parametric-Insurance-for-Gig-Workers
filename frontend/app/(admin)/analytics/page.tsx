"use client";

import { motion } from "framer-motion";
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { generateLossRatioData, generatePremiumPayoutData, generatePartnerGrowthData, topZonesData, formatINR } from "@/lib/mock-data";
import { CITIES } from "@/lib/mock-data";
import { useState } from "react";

const lossData = generateLossRatioData(30);
const ppData = generatePremiumPayoutData(8);
const growthData = generatePartnerGrowthData(30);

const METRICS = [
  { label: "Avg Loss Ratio", value: "54%", sub: "30-day average" },
  { label: "Total Premium", value: "₹2.4L", sub: "This month" },
  { label: "Total Payouts", value: "₹1.3L", sub: "This month" },
  { label: "Break-even", value: "0.89x", sub: "Premium / Payouts" },
];

export default function AnalyticsPage() {
  const [city, setCity] = useState("All");

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-ink-primary">Analytics</h1>
        <div className="flex gap-3">
          <input type="date" className="h-9 px-3 rounded-lg border border-gray-200 text-sm outline-none" defaultValue="2026-03-01" />
          <input type="date" className="h-9 px-3 rounded-lg border border-gray-200 text-sm outline-none" defaultValue="2026-03-19" />
          <select value={city} onChange={(e) => setCity(e.target.value)} className="h-9 px-3 rounded-lg border border-gray-200 text-sm outline-none">
            <option value="All">All Cities</option>
            {CITIES.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
      </div>

      {/* 2x2 Chart Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Loss Ratio */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="bg-white rounded-2xl shadow-card p-6">
          <h3 className="text-sm font-semibold text-ink-primary mb-4">Loss Ratio</h3>
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={lossData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} interval={4} />
              <YAxis tick={{ fontSize: 10 }} domain={[40, 70]} unit="%" />
              <Tooltip contentStyle={{ borderRadius: 12, border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }} formatter={(v: number) => `${v}%`} />
              <Area type="monotone" dataKey="ratio" stroke="#F5A623" strokeWidth={2} fill="url(#amberFill)" />
              <defs>
                <linearGradient id="amberFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#F5A623" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#F5A623" stopOpacity={0} />
                </linearGradient>
              </defs>
            </AreaChart>
          </ResponsiveContainer>
        </motion.div>

        {/* Premium vs Payouts */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="bg-white rounded-2xl shadow-card p-6">
          <h3 className="text-sm font-semibold text-ink-primary mb-4">Premium vs Payouts</h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={ppData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="week" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => `₹${(v/1000).toFixed(0)}K`} />
              <Tooltip contentStyle={{ borderRadius: 12, border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }} formatter={(v: number) => formatINR(v)} />
              <Legend />
              <Bar dataKey="premium" fill="#1A3C5E" radius={[4, 4, 0, 0]} name="Premium" />
              <Bar dataKey="payouts" fill="#F5A623" radius={[4, 4, 0, 0]} name="Payouts" />
            </BarChart>
          </ResponsiveContainer>
        </motion.div>

        {/* Active Partners */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="bg-white rounded-2xl shadow-card p-6">
          <h3 className="text-sm font-semibold text-ink-primary mb-4">Active Partners</h3>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={growthData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} interval={4} />
              <YAxis tick={{ fontSize: 10 }} domain={[37000, 44000]} tickFormatter={(v) => `${(v/1000).toFixed(0)}K`} />
              <Tooltip contentStyle={{ borderRadius: 12, border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }} formatter={(v: number) => v.toLocaleString("en-IN")} />
              <Line type="monotone" dataKey="partners" stroke="#1A3C5E" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </motion.div>

        {/* Top Zones */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="bg-white rounded-2xl shadow-card p-6">
          <h3 className="text-sm font-semibold text-ink-primary mb-4">Top Zones by Payout</h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={topZonesData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={(v) => `₹${(v/1000).toFixed(0)}K`} />
              <YAxis type="category" dataKey="zone" tick={{ fontSize: 10 }} width={50} />
              <Tooltip contentStyle={{ borderRadius: 12, border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }} formatter={(v: number) => formatINR(v)} />
              <Bar dataKey="payouts" fill="#F5A623" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </motion.div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {METRICS.map((m, i) => (
          <motion.div key={m.label} initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 + i * 0.05 }} className="bg-white rounded-2xl shadow-card p-5">
            <p className="text-2xl font-bold text-navy">{m.value}</p>
            <p className="text-sm font-medium text-ink-primary mt-1">{m.label}</p>
            <p className="text-xs text-ink-muted">{m.sub}</p>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
