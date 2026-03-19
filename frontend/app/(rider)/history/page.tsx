"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import confetti from "canvas-confetti";
import { Check, ArrowRight } from "lucide-react";
import PayoutCard from "@/components/gridguard/PayoutCard";
import { mockPayouts, EVENT_ICONS } from "@/lib/mock-data";
import Link from "next/link";

const FILTERS = ["All", "Rain", "Heat", "AQI", "Outage"] as const;

function HistoryContent() {
  const searchParams = useSearchParams();
  const payoutId = searchParams.get("payout");
  const [showSuccess, setShowSuccess] = useState(false);
  const [activeFilter, setActiveFilter] = useState<string>("All");
  const [countUp, setCountUp] = useState(0);

  useEffect(() => {
    if (payoutId) {
      setShowSuccess(true);
      // Count-up animation
      const target = 50;
      let current = 0;
      const timer = setInterval(() => {
        current += 2;
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
  }, [payoutId]);

  const filteredPayouts = activeFilter === "All"
    ? mockPayouts
    : mockPayouts.filter(p => p.eventType === activeFilter.toLowerCase());

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
                Zone B4F2 rain disruption — 1 hr covered
              </motion.p>

              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.9 }}
                className="text-white/40 text-xs font-mono mb-6"
              >
                MOCK-RAIN-a3f2b1c9
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
                    ["Event", "Zone B4F2 Rainfall"],
                    ["Duration", "1 hour"],
                    ["Rate", "₹50/hr"],
                    ["Total", "₹50"],
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
        {["Today", "Yesterday", "This Week"].map((group) => {
          const groupPayouts = filteredPayouts.filter(p => {
            if (group === "Today") return p.timestamp.includes("Today");
            if (group === "Yesterday") return p.timestamp.includes("Yesterday");
            return !p.timestamp.includes("Today") && !p.timestamp.includes("Yesterday");
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
