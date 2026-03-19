"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { MapPin, ChevronDown, Shield, AlertTriangle } from "lucide-react";
import { mockHexCells, CITIES } from "@/lib/mock-data";
import ZoneHexBadge from "@/components/gridguard/ZoneHexBadge";

interface HexCell {
  h3Index: string;
  lat: number;
  lng: number;
  score: number;
  zoneName: string;
  event: string;
  rate: number;
}

function getScoreColor(score: number): string {
  if (score > 0.7) return "bg-green-500";
  if (score > 0.4) return "bg-amber";
  return "bg-red-500";
}

function getScoreLabel(score: number): string {
  if (score > 0.7) return "Safe";
  if (score > 0.4) return "Caution";
  return "Disrupted";
}

export default function MapPage() {
  const [selectedCell, setSelectedCell] = useState<HexCell | null>(null);
  const [selectedCity, setSelectedCity] = useState("Bengaluru");
  const [showCityDropdown, setShowCityDropdown] = useState(false);

  return (
    <div className="relative h-[calc(100dvh-3.5rem)] md:h-screen overflow-hidden bg-gray-900">
      {/* Map placeholder with styled hex grid */}
      <div className="absolute inset-0 bg-[#1a1a2e]">
        {/* Simulated map grid */}
        <div className="absolute inset-0" style={{
          backgroundImage: `
            linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)
          `,
          backgroundSize: "40px 40px",
        }} />

        {/* Hex cells rendered as dots on map */}
        {mockHexCells.map((cell, idx) => {
          const x = 10 + ((cell.lng - 77.5) * 600);
          const y = 10 + ((13.1 - cell.lat) * 600);
          const color =
            cell.score > 0.7 ? "rgba(39,174,96,0.6)" :
            cell.score > 0.4 ? "rgba(245,166,35,0.6)" :
            "rgba(231,76,60,0.8)";
          return (
            <motion.div
              key={cell.h3Index}
              initial={{ opacity: 0, scale: 0 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: idx * 0.05 }}
              onClick={() => setSelectedCell(cell)}
              className="absolute cursor-pointer hover:scale-110 transition-transform"
              style={{
                left: `${Math.min(Math.max(x, 5), 85)}%`,
                top: `${Math.min(Math.max(y, 5), 80)}%`,
                width: 60,
                height: 52,
              }}
            >
              <svg viewBox="0 0 60 52" className="w-full h-full">
                <polygon
                  points="30,0 58,13 58,39 30,52 2,39 2,13"
                  fill={color}
                  stroke={selectedCell?.h3Index === cell.h3Index ? "white" : "rgba(255,255,255,0.2)"}
                  strokeWidth={selectedCell?.h3Index === cell.h3Index ? 2 : 0.5}
                />
                <text x="30" y="30" textAnchor="middle" fill="white" fontSize="8" fontWeight="bold">
                  {cell.zoneName}
                </text>
              </svg>
            </motion.div>
          );
        })}

        {/* User location dot */}
        <div className="absolute" style={{ left: "45%", top: "40%" }}>
          <div className="relative">
            <span className="absolute -inset-2 rounded-full bg-white/30 animate-ping" />
            <span className="relative block w-4 h-4 rounded-full bg-white shadow-lg border-2 border-blue-400" />
          </div>
        </div>
      </div>

      {/* City selector */}
      <div className="absolute top-4 right-4 z-20">
        <div className="relative">
          <button
            onClick={() => setShowCityDropdown(!showCityDropdown)}
            className="flex items-center gap-2 px-4 py-2 bg-white/10 backdrop-blur-md rounded-xl text-white text-sm font-medium hover:bg-white/20 transition"
          >
            <MapPin className="w-4 h-4" />
            {selectedCity}
            <ChevronDown className="w-4 h-4" />
          </button>
          {showCityDropdown && (
            <motion.div
              initial={{ opacity: 0, y: -5 }}
              animate={{ opacity: 1, y: 0 }}
              className="absolute right-0 mt-2 w-44 bg-white rounded-xl shadow-lg py-2 z-30"
            >
              {CITIES.map((city) => (
                <button
                  key={city}
                  onClick={() => { setSelectedCity(city); setShowCityDropdown(false); }}
                  className={`w-full text-left px-4 py-2 text-sm hover:bg-surface transition ${
                    city === selectedCity ? "text-amber font-semibold" : "text-ink-primary"
                  }`}
                >
                  {city}
                </button>
              ))}
            </motion.div>
          )}
        </div>
      </div>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 md:bottom-auto md:top-4 md:left-4 z-20">
        <div className="flex gap-3 px-4 py-2 bg-white/10 backdrop-blur-md rounded-xl">
          {[
            { label: "Safe", color: "bg-green-500" },
            { label: "Caution", color: "bg-amber" },
            { label: "Disrupted", color: "bg-red-500" },
          ].map((item) => (
            <div key={item.label} className="flex items-center gap-1.5">
              <span className={`w-2.5 h-2.5 rounded-full ${item.color}`} />
              <span className="text-xs text-white/80">{item.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Bottom Sheet (mobile) / Right Panel (desktop) */}
      {selectedCell && (
        <motion.div
          initial={{ y: "100%", opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: "100%", opacity: 0 }}
          className="absolute bottom-0 left-0 right-0 md:bottom-auto md:top-0 md:left-auto md:right-0 md:w-80 md:h-full
            bg-white rounded-t-3xl md:rounded-none shadow-2xl z-30"
        >
          {/* Drag handle mobile */}
          <div className="flex justify-center pt-3 md:hidden">
            <div className="w-10 h-1 bg-gray-300 rounded-full" />
          </div>

          <div className="p-6">
            <div className="flex items-center justify-between mb-4">
              <ZoneHexBadge zone={selectedCell.zoneName} />
              <button
                onClick={() => setSelectedCell(null)}
                className="text-ink-muted hover:text-ink-primary text-sm"
              >
                ✕
              </button>
            </div>

            <div className="flex items-center gap-3 mb-4">
              <div className={`w-3 h-3 rounded-full ${getScoreColor(selectedCell.score)}`} />
              <span className="text-lg font-bold text-ink-primary">
                {selectedCell.score.toFixed(2)}
              </span>
              <span className="text-sm text-ink-muted">{getScoreLabel(selectedCell.score)}</span>
            </div>

            <div className="space-y-3 mb-6">
              <div className="flex justify-between text-sm">
                <span className="text-ink-muted">Event</span>
                <span className="text-ink-primary font-medium">{selectedCell.event}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-ink-muted">Rate</span>
                <span className="text-ink-primary font-medium">₹{selectedCell.rate}/hr</span>
              </div>
            </div>

            {/* Coverage status */}
            <div className={`p-4 rounded-xl ${
              selectedCell.score > 0.7
                ? "bg-green-50 border border-green-200"
                : "bg-amber-50 border border-amber-200"
            }`}>
              <div className="flex items-center gap-2">
                {selectedCell.score > 0.7 ? (
                  <>
                    <Shield className="w-5 h-5 text-green-600" />
                    <span className="text-sm font-semibold text-green-700">You are covered ✓</span>
                  </>
                ) : (
                  <>
                    <AlertTriangle className="w-5 h-5 text-amber-600" />
                    <button className="text-sm font-semibold text-amber-700 hover:underline">
                      Get covered →
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
}
