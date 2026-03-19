"use client";

import { motion } from "framer-motion";
import { Users, CreditCard, TrendingDown, AlertTriangle } from "lucide-react";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Area, AreaChart, Legend,
} from "recharts";
import KPICard from "@/components/gridguard/KPICard";
import ZoneHexBadge from "@/components/gridguard/ZoneHexBadge";
import { generateLossRatioData, generatePremiumPayoutData, mockPayouts, formatINR } from "@/lib/mock-data";

const lossRatioData = generateLossRatioData(30);
const premiumPayoutData = generatePremiumPayoutData(8);

const ACTIVE_EVENTS = [
  { zone: "B4F2", event: "Rainfall", partners: 234, time: "12 min ago", color: "🔴" },
  { zone: "A2C1", event: "Heat Alert", partners: 89, time: "28 min ago", color: "🟠" },
  { zone: "D7E9", event: "App Outage", partners: 45, time: "1 hr ago", color: "🟡" },
  { zone: "C3F1", event: "AQI Warning", partners: 67, time: "2 hr ago", color: "🟢" },
  { zone: "E5A2", event: "Storm Watch", partners: 112, time: "3 hr ago", color: "🔵" },
];

const RECENT_PAYOUTS = [
  { name: "Rajesh K.", amount: "₹50", zone: "B4F2", time: "2 min ago" },
  { name: "Priya M.", amount: "₹35", zone: "A2C1", time: "5 min ago" },
  { name: "Arjun S.", amount: "₹45", zone: "D7E9", time: "8 min ago" },
  { name: "Divya R.", amount: "₹40", zone: "C3F1", time: "12 min ago" },
  { name: "Karan P.", amount: "₹55", zone: "E5A2", time: "15 min ago" },
];

const sparkline1 = [12, 14, 13, 15, 14, 16, 15, 17, 16, 18];
const sparkline2 = [5, 6, 7, 6, 8, 7, 9, 8, 9, 10];
const sparkline3 = [60, 58, 56, 57, 55, 54, 55, 53, 54, 54];
const sparkline4 = [1, 1, 2, 1, 2, 2, 3, 2, 3, 3];

export default function OverviewPage() {
  return (
    <div className="flex gap-6">
      {/* Main Content */}
      <div className="flex-1 min-w-0">
        {/* KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
          <KPICard
            title="Active Partners"
            value="42,800"
            change="+3.2% ↑"
            changeType="positive"
            icon={Users}
            iconColor="bg-blue-100 text-blue-600"
            sparklineData={sparkline1}
          />
          <KPICard
            title="Payouts Today"
            value="₹8.4L"
            change="+12% ↑"
            changeType="positive"
            icon={CreditCard}
            iconColor="bg-green-100 text-green-600"
            sparklineData={sparkline2}
          />
          <KPICard
            title="Loss Ratio"
            value="54%"
            change="-2% ↓"
            changeType="positive"
            icon={TrendingDown}
            iconColor="bg-amber-100 text-amber-600"
            sparklineData={sparkline3}
          />
          <KPICard
            title="Fraud Flags"
            value="3"
            change="+1 ↑"
            changeType="negative"
            icon={AlertTriangle}
            iconColor="bg-red-100 text-red-600"
            sparklineData={sparkline4}
          />
        </div>

        {/* Live Heatmap */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-gray-900 rounded-2xl overflow-hidden mb-6 relative"
          style={{ height: 320 }}
        >
          <div className="absolute inset-0" style={{
            backgroundImage: `
              linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
              linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)
            `,
            backgroundSize: "30px 30px",
          }} />
          {/* Simulated heatmap blobs */}
          {[
            { x: 30, y: 40, r: 80, color: "rgba(231,76,60,0.3)" },
            { x: 60, y: 50, r: 60, color: "rgba(245,166,35,0.3)" },
            { x: 45, y: 65, r: 90, color: "rgba(39,174,96,0.25)" },
            { x: 70, y: 30, r: 50, color: "rgba(245,166,35,0.2)" },
            { x: 25, y: 70, r: 40, color: "rgba(231,76,60,0.2)" },
          ].map((blob, i) => (
            <div
              key={i}
              className="absolute rounded-full"
              style={{
                left: `${blob.x}%`,
                top: `${blob.y}%`,
                width: blob.r,
                height: blob.r,
                background: `radial-gradient(circle, ${blob.color}, transparent)`,
                transform: "translate(-50%, -50%)",
              }}
            />
          ))}
          {/* Pulsing active event dots */}
          {ACTIVE_EVENTS.slice(0, 3).map((evt, i) => (
            <div
              key={i}
              className="absolute"
              style={{ left: `${25 + i * 20}%`, top: `${35 + i * 12}%` }}
            >
              <span className="absolute -inset-1 rounded-full bg-amber/40 animate-ping" />
              <span className="relative block w-3 h-3 rounded-full bg-amber" />
            </div>
          ))}
          <div className="absolute top-4 right-4">
            <select className="bg-white/10 backdrop-blur text-white text-xs rounded-lg px-3 py-1.5 border-0 outline-none">
              <option>Bengaluru</option>
              <option>Mumbai</option>
              <option>Chennai</option>
              <option>Delhi</option>
            </select>
          </div>
          <div className="absolute bottom-4 left-4 text-white/60 text-xs">
            Real-time claims density heatmap
          </div>
        </motion.div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Loss Ratio */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-white rounded-2xl shadow-card p-6"
          >
            <h3 className="text-sm font-semibold text-ink-primary mb-4">Loss Ratio (30 Days)</h3>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={lossRatioData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} interval={4} />
                <YAxis tick={{ fontSize: 10 }} domain={[40, 70]} unit="%" />
                <Tooltip
                  contentStyle={{ borderRadius: 12, border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }}
                />
                <Area
                  type="monotone"
                  dataKey="ratio"
                  stroke="#1A3C5E"
                  strokeWidth={2}
                  fill="url(#navyGradient)"
                />
                <defs>
                  <linearGradient id="navyGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#F5A623" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#F5A623" stopOpacity={0} />
                  </linearGradient>
                </defs>
              </AreaChart>
            </ResponsiveContainer>
          </motion.div>

          {/* Premium vs Payouts */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="bg-white rounded-2xl shadow-card p-6"
          >
            <h3 className="text-sm font-semibold text-ink-primary mb-4">Premium vs Payouts (8 Weeks)</h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={premiumPayoutData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="week" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => `₹${(v/1000).toFixed(0)}K`} />
                <Tooltip
                  contentStyle={{ borderRadius: 12, border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }}
                  formatter={(value: number) => formatINR(value)}
                />
                <Legend />
                <Bar dataKey="premium" fill="#1A3C5E" radius={[4, 4, 0, 0]} name="Premium" />
                <Bar dataKey="payouts" fill="#F5A623" radius={[4, 4, 0, 0]} name="Payouts" />
              </BarChart>
            </ResponsiveContainer>
          </motion.div>
        </div>
      </div>

      {/* Right Panel — hidden on mobile */}
      <div className="hidden xl:block w-80 space-y-6 flex-shrink-0">
        {/* Active Events */}
        <div className="bg-white rounded-2xl shadow-card p-5">
          <h3 className="text-sm font-semibold text-ink-primary mb-3">Active Events</h3>
          <div className="space-y-3">
            {ACTIVE_EVENTS.map((evt, i) => (
              <div key={i} className="flex items-center gap-3 text-sm">
                <span>{evt.color}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <ZoneHexBadge zone={evt.zone} className="text-[10px]" />
                    <span className="text-ink-primary font-medium truncate">{evt.event}</span>
                  </div>
                  <p className="text-xs text-ink-muted">{evt.partners} partners · {evt.time}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Payouts */}
        <div className="bg-white rounded-2xl shadow-card p-5">
          <h3 className="text-sm font-semibold text-ink-primary mb-3">Recent Payouts</h3>
          <div className="space-y-3">
            {RECENT_PAYOUTS.map((p, i) => (
              <div key={i} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-full bg-navy/10 flex items-center justify-center text-[10px] font-bold text-navy">
                    {p.name.split(" ").map(n => n[0]).join("")}
                  </div>
                  <div>
                    <p className="font-medium text-ink-primary">{p.name}</p>
                    <p className="text-xs text-ink-muted">{p.zone} · {p.time}</p>
                  </div>
                </div>
                <span className="font-bold text-navy">{p.amount}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
