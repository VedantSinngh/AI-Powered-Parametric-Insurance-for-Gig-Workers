"use client";

import { motion } from "framer-motion";
import { Bell } from "lucide-react";
import WorkabilityGauge from "@/components/gridguard/WorkabilityGauge";
import ConnectionStatus from "@/components/gridguard/ConnectionStatus";
import MockWalletBadge from "@/components/gridguard/MockWalletBadge";
import PayoutCard from "@/components/gridguard/PayoutCard";
import ZoneHexBadge from "@/components/gridguard/ZoneHexBadge";
import { mockPayouts, weeklyForecast } from "@/lib/mock-data";

export default function DashboardPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
      {/* Desktop Top Bar */}
      <div className="hidden md:flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-navy flex items-center justify-center text-sm font-bold text-white">
            RK
          </div>
          <span className="font-semibold text-ink-primary">Rajesh K.</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="px-3 py-1.5 rounded-full bg-amber/10 text-amber text-sm font-semibold">
            Zone B4F2 · Koramangala
          </span>
          <button className="relative p-2 hover:bg-gray-100 rounded-xl transition">
            <Bell className="w-5 h-5 text-ink-muted" />
            <span className="absolute top-1.5 right-1.5 w-4 h-4 bg-red-500 rounded-full text-[10px] text-white font-bold flex items-center justify-center">
              3
            </span>
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
          <WorkabilityGauge score={0.72} />
        </div>
        <div className="flex items-center justify-center gap-2 mt-2">
          <span className="px-3 py-1 rounded-full bg-green-500/20 text-green-300 text-sm font-semibold">
            SAFE TO RIDE
          </span>
        </div>
        <div className="flex items-center justify-center gap-3 mt-3">
          <ConnectionStatus isLive={true} />
          <span className="text-white/40 text-xs">·</span>
          <span className="text-white/60 text-xs">Hex Zone B4F2 · Last updated 2 min ago</span>
        </div>
      </motion.div>

      {/* Wallet Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="relative bg-white rounded-2xl shadow-card p-6 border-l-4 border-l-amber"
      >
        <MockWalletBadge />
        <p className="text-3xl font-bold text-navy">₹340</p>
        <p className="text-sm text-ink-muted mt-1">
          This week&apos;s premium: ₹18 · deducted Monday
        </p>
        <div className="flex gap-3 mt-4">
          <button className="flex-1 h-10 rounded-lg border-2 border-navy text-navy text-sm font-semibold hover:bg-navy/5 transition">
            Add Money
          </button>
          <button className="flex-1 h-10 rounded-lg border-2 border-navy text-navy text-sm font-semibold hover:bg-navy/5 transition">
            Withdraw
          </button>
        </div>
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
          <button className="text-xs font-semibold text-amber hover:text-amber-dark transition">
            View All →
          </button>
        </div>
        <div className="bg-white rounded-2xl shadow-card divide-y divide-gray-50">
          {mockPayouts.slice(0, 3).map((payout) => (
            <PayoutCard key={payout.id} payout={payout} />
          ))}
        </div>
      </motion.div>
    </div>
  );
}
