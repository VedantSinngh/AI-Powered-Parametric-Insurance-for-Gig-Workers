"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Camera, Mail } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import ZoneHexBadge from "@/components/gridguard/ZoneHexBadge";
import RiskTierPill from "@/components/gridguard/RiskTierPill";

const LANGUAGES = [
  { code: "en", label: "English", flag: "🇬🇧" },
  { code: "hi", label: "हिंदी", flag: "🇮🇳" },
  { code: "ta", label: "தமிழ்", flag: "🇮🇳" },
  { code: "te", label: "తెలుగు", flag: "🇮🇳" },
];

const COVERAGE_HISTORY = [
  {
    week: "Mar 18 – Mar 24",
    events: [
      { type: "Rain", zone: "B4F2", amount: 50, date: "Mar 19" },
      { type: "Heat", zone: "A2C1", amount: 35, date: "Mar 20" },
    ],
  },
  {
    week: "Mar 11 – Mar 17",
    events: [
      { type: "AQI", zone: "D7E9", amount: 45, date: "Mar 12" },
      { type: "Outage", zone: "C3F1", amount: 40, date: "Mar 14" },
    ],
  },
  {
    week: "Mar 4 – Mar 10",
    events: [
      { type: "Rain", zone: "E5A2", amount: 55, date: "Mar 5" },
    ],
  },
];

export default function ProfilePage() {
  const [autoDeduct, setAutoDeduct] = useState(true);
  const [selectedLang, setSelectedLang] = useState("en");
  const [expandedWeek, setExpandedWeek] = useState<string | null>(null);

  return (
    <div className="max-w-2xl mx-auto px-4 py-6 space-y-6">
      {/* Avatar + Info */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center"
      >
        <div className="relative inline-block">
          <div className="w-20 h-20 rounded-full bg-navy flex items-center justify-center text-2xl font-bold text-white">
            RK
          </div>
          <button className="absolute bottom-0 right-0 w-7 h-7 rounded-full bg-amber flex items-center justify-center shadow-md">
            <Camera className="w-3.5 h-3.5 text-white" />
          </button>
        </div>
        <h2 className="text-xl font-bold text-ink-primary mt-3">Rajesh K.</h2>
        <div className="flex items-center justify-center gap-3 mt-2">
          <span className="px-3 py-1 rounded-lg bg-gray-100 text-xs font-mono text-ink-muted">
            DEV-A1B2C3D4
          </span>
          <ZoneHexBadge zone="B4F2" />
        </div>
      </motion.div>

      {/* Policy Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="relative bg-white rounded-2xl shadow-card p-6"
      >
        <span className="absolute top-4 right-4 px-2.5 py-0.5 rounded-full bg-green-100 text-green-700 text-xs font-semibold">
          Active Coverage
        </span>
        <h3 className="text-lg font-bold text-ink-primary mb-4">Your Policy</h3>
        <div className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-ink-muted">Week</span>
            <span className="text-ink-primary font-medium">Mar 18 – Mar 24, 2026</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-ink-muted">Risk Tier</span>
            <RiskTierPill tier="medium" />
          </div>
          <div className="flex justify-between">
            <span className="text-ink-muted">Premium</span>
            <span className="text-ink-primary font-medium">₹18/week</span>
          </div>
        </div>
      </motion.div>

      {/* Auto-Deduction Toggle */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="bg-white rounded-2xl shadow-card p-6"
      >
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-ink-primary">Auto-premium deduction</p>
            <p className="text-xs text-ink-muted mt-0.5">Deducted every Monday 6:00 AM</p>
          </div>
          <Switch
            checked={autoDeduct}
            onCheckedChange={setAutoDeduct}
            className="data-[state=checked]:bg-amber"
          />
        </div>
      </motion.div>

      {/* Coverage History */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="bg-white rounded-2xl shadow-card p-6"
      >
        <h3 className="text-lg font-bold text-ink-primary mb-4">Coverage History</h3>
        <div className="space-y-2">
          {COVERAGE_HISTORY.map((week) => (
            <div key={week.week} className="border border-gray-100 rounded-xl overflow-hidden">
              <button
                onClick={() => setExpandedWeek(expandedWeek === week.week ? null : week.week)}
                className="w-full flex items-center justify-between px-4 py-3 hover:bg-surface transition text-left"
              >
                <span className="text-sm font-medium text-ink-primary">{week.week}</span>
                <span className="text-xs text-ink-muted">
                  {week.events.length} event{week.events.length > 1 ? "s" : ""}
                </span>
              </button>
              {expandedWeek === week.week && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  className="border-t border-gray-100"
                >
                  {week.events.map((event, idx) => (
                    <div key={idx} className="flex items-center justify-between px-4 py-2 text-sm">
                      <div className="flex items-center gap-2">
                        <span className="text-ink-muted">{event.date}</span>
                        <span className="text-ink-primary">{event.type}</span>
                        <ZoneHexBadge zone={event.zone} className="text-[10px]" />
                      </div>
                      <span className="font-semibold text-navy">₹{event.amount}</span>
                    </div>
                  ))}
                </motion.div>
              )}
            </div>
          ))}
        </div>
      </motion.div>

      {/* Language Selector */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="bg-white rounded-2xl shadow-card p-6"
      >
        <h3 className="text-sm font-semibold text-ink-primary mb-3">Language</h3>
        <div className="grid grid-cols-2 gap-2">
          {LANGUAGES.map((lang) => (
            <button
              key={lang.code}
              onClick={() => setSelectedLang(lang.code)}
              className={`flex items-center gap-2 px-4 py-3 rounded-xl text-sm font-medium transition-all
                ${selectedLang === lang.code
                  ? "bg-navy text-white"
                  : "bg-surface text-ink-primary hover:bg-gray-100"
                }`}
            >
              <span>{lang.flag}</span>
              {lang.label}
            </button>
          ))}
        </div>
      </motion.div>

      {/* Contact Support */}
      <a
        href="mailto:support@gridguard.ai"
        className="flex items-center justify-center gap-2 w-full h-12 rounded-xl border-2 border-gray-200 text-sm font-semibold text-ink-muted hover:border-navy hover:text-navy transition-all"
      >
        <Mail className="w-4 h-4" />
        Contact Support
      </a>
    </div>
  );
}
