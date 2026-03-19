"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import FraudAlertRow from "@/components/gridguard/FraudAlertRow";
import ZoneHexBadge from "@/components/gridguard/ZoneHexBadge";
import { mockFraudAlerts, mockAccelerometerData, type FraudAlert } from "@/lib/mock-data";

const STATS = [
  { label: "Total", value: 12, color: "bg-gray-100 text-gray-700" },
  { label: "Auto-Dismissed", value: 5, color: "bg-green-100 text-green-700" },
  { label: "Pending", value: 4, color: "bg-amber-100 text-amber-700" },
  { label: "Confirmed", value: 3, color: "bg-red-100 text-red-700" },
];

const ACTIVITY_LOG = [
  { time: "3:15 PM", event: "Claim submitted", status: "info" },
  { time: "3:14 PM", event: "GPS check: FAILED — 2.3km from zone", status: "error" },
  { time: "3:10 PM", event: "Device stationary for 42 min", status: "warning" },
  { time: "2:30 PM", event: "Last delivery completed", status: "success" },
  { time: "1:00 PM", event: "Logged into partner app", status: "info" },
];

export default function FraudPage() {
  const [selectedAlert, setSelectedAlert] = useState<FraudAlert | null>(null);
  const [reviewNote, setReviewNote] = useState("");

  return (
    <div>
      <h1 className="text-xl font-bold text-ink-primary mb-4">Fraud Detection</h1>

      {/* Stats bar */}
      <div className="flex gap-3 mb-6 flex-wrap">
        {STATS.map((s) => (
          <div key={s.label} className={`px-4 py-2 rounded-xl text-sm font-semibold ${s.color}`}>
            {s.label}: {s.value}
          </div>
        ))}
      </div>

      {/* Split layout */}
      <div className="flex gap-6">
        {/* Left — Alert list (60%) */}
        <div className="flex-[3] min-w-0 space-y-3">
          {mockFraudAlerts.map((alert) => (
            <motion.div
              key={alert.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
            >
              <FraudAlertRow
                alert={alert}
                isSelected={selectedAlert?.id === alert.id}
                onClick={() => setSelectedAlert(alert)}
              />
            </motion.div>
          ))}
        </div>

        {/* Right — Detail panel (40%) */}
        <AnimatePresence mode="wait">
          {selectedAlert && (
            <motion.div
              key={selectedAlert.id}
              initial={{ opacity: 0, x: 40 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 40 }}
              className="flex-[2] bg-white rounded-2xl shadow-card p-6 sticky top-20 h-fit"
            >
              {/* Partner mini card */}
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-full bg-navy/10 flex items-center justify-center text-sm font-bold text-navy">
                  {selectedAlert.partnerName.split(" ").map(n => n[0]).join("")}
                </div>
                <div>
                  <p className="font-semibold text-ink-primary">{selectedAlert.partnerName}</p>
                  <p className="text-xs text-ink-muted">{selectedAlert.partnerId}</p>
                </div>
                <ZoneHexBadge zone="B4F2" className="ml-auto" />
              </div>

              {/* GPS Map */}
              <div className="bg-gray-900 rounded-xl overflow-hidden mb-4 relative" style={{ height: 160 }}>
                <div className="absolute inset-0" style={{
                  backgroundImage: `
                    linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)
                  `,
                  backgroundSize: "20px 20px",
                }} />
                {/* GPS marker */}
                <div className="absolute" style={{ left: "50%", top: "45%", transform: "translate(-50%, -50%)" }}>
                  <div className="relative">
                    <span className="absolute -inset-3 rounded-full bg-red-500/20 animate-ping" />
                    <span className="absolute -inset-2 rounded-full bg-red-500/10" />
                    <span className="relative block w-4 h-4 rounded-full bg-red-500 border-2 border-white" />
                  </div>
                </div>
                <div className="absolute bottom-2 left-2 text-white/40 text-[10px] font-mono">
                  {selectedAlert.lat.toFixed(4)}, {selectedAlert.lng.toFixed(4)}
                </div>
              </div>

              {/* Accelerometer chart */}
              <div className="mb-4">
                <h4 className="text-xs font-semibold text-ink-muted mb-2 uppercase">Accelerometer Data</h4>
                <ResponsiveContainer width="100%" height={120}>
                  <LineChart data={mockAccelerometerData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="time" tick={{ fontSize: 9 }} interval={4} />
                    <YAxis tick={{ fontSize: 9 }} domain={[0, 0.8]} />
                    <ReferenceLine y={0.15} stroke="#E74C3C" strokeDasharray="5 5" label={{ value: "Threshold", fontSize: 9, fill: "#E74C3C" }} />
                    <Line type="monotone" dataKey="value" stroke="#1A3C5E" strokeWidth={1.5} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* Activity timeline */}
              <div className="mb-4">
                <h4 className="text-xs font-semibold text-ink-muted mb-2 uppercase">Activity Log</h4>
                <div className="space-y-2">
                  {ACTIVITY_LOG.map((log, i) => (
                    <div key={i} className="flex items-start gap-3 text-xs">
                      <span className="text-ink-muted w-14 flex-shrink-0">{log.time}</span>
                      <span className={`w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0 ${
                        log.status === "error" ? "bg-red-500" :
                        log.status === "warning" ? "bg-amber-500" :
                        log.status === "success" ? "bg-green-500" : "bg-gray-400"
                      }`} />
                      <span className="text-ink-primary">{log.event}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Review note */}
              <textarea
                value={reviewNote}
                onChange={(e) => setReviewNote(e.target.value)}
                placeholder="Add reviewer note..."
                className="w-full h-20 px-3 py-2 rounded-xl border border-gray-200 text-sm resize-none focus:ring-2 focus:ring-navy/20 focus:border-navy outline-none mb-4"
              />

              {/* Actions */}
              <div className="flex gap-3">
                <button className="flex-1 h-10 rounded-xl bg-red-500 text-white text-sm font-semibold hover:bg-red-600 transition">
                  Confirm Fraud
                </button>
                <button className="flex-1 h-10 rounded-xl border-2 border-gray-200 text-ink-muted text-sm font-semibold hover:border-gray-300 transition">
                  Dismiss
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Empty state */}
        {!selectedAlert && (
          <div className="flex-[2] flex items-center justify-center text-ink-muted text-sm">
            Select an alert to view details
          </div>
        )}
      </div>
    </div>
  );
}
