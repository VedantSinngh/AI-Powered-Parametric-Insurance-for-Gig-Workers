"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Download, Filter } from "lucide-react";
import ZoneHexBadge from "@/components/gridguard/ZoneHexBadge";
import { mockTimelinePayouts, EVENT_ICONS, formatINR } from "@/lib/mock-data";

const SUMMARY = [
  { label: "Total Paid", value: "₹42.8L", color: "text-navy" },
  { label: "Avg Payout", value: "₹38", color: "text-ink-primary" },
  { label: "Largest", value: "₹200", color: "text-amber" },
  { label: "Today", value: "7", color: "text-success" },
];

export default function PayoutsPage() {
  const [eventFilter, setEventFilter] = useState("All");

  const filtered = eventFilter === "All"
    ? mockTimelinePayouts
    : mockTimelinePayouts.filter(p => p.eventType === eventFilter.toLowerCase());

  const exportCSV = () => {
    const h = "Zone,Event,City,Amount,Partners,Timestamp,TxHash\n";
    const r = filtered.map(p =>
      `${p.zone},${p.eventName},${p.city},${p.amount},${p.partnerCount},${p.timestamp},${p.txHash}`
    ).join("\n");
    const blob = new Blob([h + r], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "payouts.csv";
    a.click();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-ink-primary">Payouts</h1>
        <button onClick={exportCSV} className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-navy text-white text-sm font-medium hover:bg-navy-dark transition">
          <Download className="w-4 h-4" /> Export CSV
        </button>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {SUMMARY.map((c) => (
          <motion.div key={c.label} initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} className="bg-white rounded-2xl shadow-card p-5">
            <p className={`text-2xl font-bold ${c.color}`}>{c.value}</p>
            <p className="text-xs text-ink-muted mt-1">{c.label}</p>
          </motion.div>
        ))}
      </div>

      {/* Filter chips */}
      <div className="flex gap-2 mb-6">
        {["All", "Rain", "Heat", "AQI", "Outage"].map((t) => (
          <button key={t} onClick={() => setEventFilter(t)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${eventFilter === t ? "bg-navy text-white" : "bg-white text-ink-muted border border-gray-200"}`}>{t}</button>
        ))}
      </div>

      {/* Timeline */}
      <div className="relative">
        <motion.div initial={{ height: 0 }} animate={{ height: "100%" }} transition={{ duration: 0.8 }} className="absolute left-6 top-2 w-0.5 bg-gray-200" />
        <div className="space-y-6">
          {filtered.map((p, i) => (
            <motion.div key={p.id} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.08 }} className="relative pl-14">
              <div className="absolute left-4 top-4 w-5 h-5 rounded-full bg-white border-2 border-amber flex items-center justify-center z-10">
                <span className="text-xs">{EVENT_ICONS[p.eventType]}</span>
              </div>
              <div className="bg-white rounded-2xl shadow-card p-5 hover:shadow-card-hover transition-shadow">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <ZoneHexBadge zone={p.zone} />
                      <span className="text-ink-primary font-semibold">{p.eventName}</span>
                    </div>
                    <p className="text-xs text-ink-muted">{p.city} · {p.timestamp}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-navy">{formatINR(p.amount)}</p>
                    <p className="text-xs text-ink-muted">{p.partnerCount} partners</p>
                  </div>
                </div>
                <div className="flex items-center justify-between pt-3 border-t border-gray-50">
                  <span className="text-xs font-mono text-ink-muted">{p.txHash}</span>
                  <span className="text-xs text-ink-muted">{p.duration}</span>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
