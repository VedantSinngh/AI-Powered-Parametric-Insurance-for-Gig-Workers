"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { cellToBoundary } from "h3-js";
import { MapPin, ChevronDown, Shield, AlertTriangle, PlayCircle, PauseCircle } from "lucide-react";
import { CITIES } from "@/lib/mock-data";
import ZoneHexBadge from "@/components/gridguard/ZoneHexBadge";
import { ApiError, apiGet } from "@/lib/api";
import { toEventLabel, zoneFromH3 } from "@/lib/gridguard";

const LeafletWorkabilityMap = dynamic(
  () => import("@/components/gridguard/LeafletWorkabilityMap"),
  {
    ssr: false,
    loading: () => (
      <div className="absolute inset-0 flex items-center justify-center text-sm text-white/70 bg-[#0b1320]">
        Loading live map...
      </div>
    ),
  },
);

interface HexCell {
  h3Index: string;
  score: number;
  zoneName: string;
  areaName: string;
  riskCode: string;
  status: "safe" | "caution" | "disrupted";
  activeEventCount: number;
  lastUpdated: string;
  event: string;
  rate: number;
  boundary: [number, number][];
  centroid: [number, number];
}

type CityWorkabilityResponse = {
  city: string;
  total: number;
  data_mode?: "real" | "demo";
  summary?: {
    avg_workability_score: number;
    risk_score: number;
    risk_tier: "low" | "medium" | "high" | "critical";
    safe_cells: number;
    caution_cells: number;
    disrupted_cells: number;
    active_events: number;
    timestamp?: string;
  };
  cells: Array<{
    h3_cell: string;
    workability_score: number;
    status: "safe" | "caution" | "disrupted";
    payout_rate_hr?: number;
    area_name?: string;
    risk_code?: string;
    active_events: Array<{
      event_type: string;
      severity: number;
      raw_value: number;
    }>;
    timestamp: string;
  }>;
};

const CITY_CENTROIDS: Record<string, [number, number]> = {
  Bengaluru: [12.9716, 77.5946],
  Mumbai: [19.076, 72.8777],
  Chennai: [13.0827, 80.2707],
  Delhi: [28.6139, 77.209],
  Hyderabad: [17.385, 78.4867],
  Pune: [18.5204, 73.8567],
  Kolkata: [22.5726, 88.3639],
};

function getScoreColor(status: "safe" | "caution" | "disrupted", score: number): string {
  if (status === "safe") return "bg-green-500";
  if (status === "caution") return "bg-amber";
  if (status === "disrupted") return "bg-red-500";

  if (score >= 0.95) return "bg-green-500";
  if (score >= 0.85) return "bg-amber";
  return "bg-red-500";
}

function getScoreLabel(status: "safe" | "caution" | "disrupted", score: number): string {
  if (status === "safe") return "Safe";
  if (status === "caution") return "Caution";
  if (status === "disrupted") return "Disrupted";

  if (score >= 0.95) return "Safe";
  if (score >= 0.85) return "Caution";
  return "Disrupted";
}

function fallbackRiskCode(score: number): string {
  if (score >= 0.7) return "R1";
  if (score >= 0.4) return "R2";
  if (score >= 0.2) return "R3";
  return "R4";
}

export default function MapPage() {
  const router = useRouter();
  const [selectedCell, setSelectedCell] = useState<HexCell | null>(null);
  const [selectedCity, setSelectedCity] = useState("Bengaluru");
  const [showCityDropdown, setShowCityDropdown] = useState(false);
  const [cells, setCells] = useState<HexCell[]>([]);
  const [replayMode, setReplayMode] = useState(false);
  const [replayIndex, setReplayIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [citySummary, setCitySummary] = useState<CityWorkabilityResponse["summary"] | null>(null);

  const hotspots = useMemo(
    () => cells
      .filter((cell) => cell.status !== "safe")
      .sort((a, b) => a.score - b.score)
      .slice(0, 12),
    [cells],
  );

  const mapCenter = CITY_CENTROIDS[selectedCity] || CITY_CENTROIDS.Bengaluru;
  const overviewRiskPercent = Math.round((citySummary?.risk_score || 0) * 100);
  const topHotspots = useMemo(() => hotspots.slice(0, 6), [hotspots]);

  useEffect(() => {
    if (!replayMode || hotspots.length === 0) {
      return;
    }

    setReplayIndex(0);
    setSelectedCell(hotspots[0]);

    const timer = window.setInterval(() => {
      setReplayIndex((prev) => (prev + 1) % hotspots.length);
    }, 1600);

    return () => window.clearInterval(timer);
  }, [replayMode, hotspots]);

  useEffect(() => {
    if (!replayMode || hotspots.length === 0) {
      return;
    }
    setSelectedCell(hotspots[replayIndex]);
  }, [replayIndex, replayMode, hotspots]);

  useEffect(() => {
    const run = async () => {
      try {
        setLoading(true);
        setError("");

        const response = await apiGet<CityWorkabilityResponse>(`/grid/workability/city/${selectedCity.toLowerCase()}`);
        const mapped = response.cells.map((cell) => {
          const firstEvent = cell.active_events[0];
          const rate = Number(cell.payout_rate_hr ?? 0);

          const rawBoundary = cellToBoundary(cell.h3_cell);
          const boundary = rawBoundary.map((point) => [point[0], point[1]] as [number, number]);
          const centroid: [number, number] = boundary.reduce(
            (acc, point) => [acc[0] + point[0] / boundary.length, acc[1] + point[1] / boundary.length],
            [0, 0],
          );

          return {
            h3Index: cell.h3_cell,
            score: cell.workability_score,
            zoneName: zoneFromH3(cell.h3_cell),
            areaName: cell.area_name?.trim() || `${selectedCity} - Zone ${zoneFromH3(cell.h3_cell)}`,
            riskCode: cell.risk_code || fallbackRiskCode(cell.workability_score),
            status: cell.status,
            activeEventCount: cell.active_events.length,
            lastUpdated: cell.timestamp,
            event: firstEvent ? toEventLabel(firstEvent.event_type) : "Clear",
            rate,
            boundary,
            centroid,
          };
        });

        setCells(mapped);
        setCitySummary(response.summary || null);
      } catch (err) {
        setCells([]);
        setCitySummary(null);
        setError(err instanceof ApiError ? err.message : "Unable to load map data.");
      } finally {
        setLoading(false);
      }
    };

    setReplayMode(false);
    setReplayIndex(0);
    setSelectedCell(null);
    run();
  }, [selectedCity]);

  return (
    <div className="relative h-[calc(100dvh-3.5rem)] md:h-screen overflow-hidden bg-gray-900">
      <div className="absolute inset-0 bg-[#0b1320]">
        <LeafletWorkabilityMap
          center={mapCenter}
          cells={cells}
          selectedCellId={selectedCell?.h3Index}
          userLocation={selectedCell?.centroid || mapCenter}
          onSelectCell={(cell) => {
            setReplayMode(false);
            const nextSelected = cells.find((item) => item.h3Index === cell.h3Index) || null;
            setSelectedCell(nextSelected);
          }}
        />

        {!loading && cells.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center px-6 text-center pointer-events-none">
            <div className="rounded-2xl bg-black/55 border border-white/10 px-5 py-4 text-sm text-white/85">
              {error || "No live zone cells available for this city yet."}
            </div>
          </div>
        )}
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

      {/* City overview panel */}
      {citySummary && (
        <div className="absolute right-4 top-20 z-20 hidden lg:block w-80">
          <div className="rounded-2xl border border-white/10 bg-black/55 backdrop-blur-md p-4 text-white">
            <h3 className="text-lg font-semibold">{selectedCity} Overview</h3>
            <p className="text-xs text-white/70 mt-1">
              {citySummary.disrupted_cells} disruption zones detected
            </p>

            <div className="mt-3">
              <div className="h-1.5 w-full rounded-full bg-white/15 overflow-hidden">
                <div
                  className="h-full rounded-full bg-red-500"
                  style={{ width: `${overviewRiskPercent}%` }}
                />
              </div>
              <p className="text-xs text-white/70 mt-2">
                Avg. Workability: {(citySummary.avg_workability_score * 100).toFixed(0)}%
              </p>
            </div>

            <div className="grid grid-cols-3 gap-2 mt-4 text-center">
              <div className="rounded-lg bg-white/5 py-2">
                <p className="text-[10px] uppercase tracking-wide text-white/60">Risk</p>
                <p className="text-xs font-semibold capitalize">{citySummary.risk_tier}</p>
              </div>
              <div className="rounded-lg bg-white/5 py-2">
                <p className="text-[10px] uppercase tracking-wide text-white/60">Events</p>
                <p className="text-xs font-semibold">{citySummary.active_events}</p>
              </div>
              <div className="rounded-lg bg-white/5 py-2">
                <p className="text-[10px] uppercase tracking-wide text-white/60">Zones</p>
                <p className="text-xs font-semibold">{cells.length}</p>
              </div>
            </div>

            <div className="mt-4 border-t border-white/10 pt-3">
              <p className="text-xs uppercase tracking-wider text-white/60 mb-2">Active zones</p>
              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {topHotspots.map((cell) => (
                  <button
                    key={cell.h3Index}
                    onClick={() => setSelectedCell(cell)}
                    className="w-full rounded-lg bg-white/5 hover:bg-white/10 px-3 py-2 text-left"
                  >
                    <p className="text-sm font-semibold">{cell.areaName}</p>
                    <p className="text-[11px] text-white/70">
                      {cell.event} · Work {Math.round(cell.score * 100)}% · ₹{cell.rate}/hr
                    </p>
                  </button>
                ))}
                {topHotspots.length === 0 && (
                  <p className="text-xs text-white/60">No active hotspots right now.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Replay controls */}
      <div className="absolute top-4 left-4 z-20">
        <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-black/45 backdrop-blur-md border border-white/10">
          <button
            onClick={() => setReplayMode((value) => !value)}
            className="flex items-center gap-1.5 text-xs font-semibold text-white hover:text-amber-200"
          >
            {replayMode ? <PauseCircle className="w-4 h-4" /> : <PlayCircle className="w-4 h-4" />}
            {replayMode ? "Pause Replay" : "Replay Hotspots"}
          </button>
          <span className="text-xs text-white/60">{hotspots.length} hotspots</span>
          <button
            onClick={() => router.push("/dashboard#pricing-plans")}
            className="text-xs font-semibold text-amber-200 hover:text-amber-100"
          >
            Pricing
          </button>
        </div>
      </div>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 md:bottom-auto md:top-4 md:left-4 z-20">
        <div className="flex gap-3 px-4 py-2 bg-black/45 border border-white/10 backdrop-blur-md rounded-xl mt-12 md:mt-0">
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

            <p className="text-sm font-semibold text-ink-primary mb-2">{selectedCell.areaName}</p>

            <div className="flex items-center gap-3 mb-4">
              <div className={`w-3 h-3 rounded-full ${getScoreColor(selectedCell.status, selectedCell.score)}`} />
              <span className="text-lg font-bold text-ink-primary">
                {selectedCell.score.toFixed(2)}
              </span>
              <span className="text-sm text-ink-muted">{getScoreLabel(selectedCell.status, selectedCell.score)}</span>
            </div>

            <div className="space-y-3 mb-6">
              <div className="flex justify-between text-sm">
                <span className="text-ink-muted">Event</span>
                <span className="text-ink-primary font-medium">{selectedCell.event}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-ink-muted">Risk Code</span>
                <span className="text-ink-primary font-medium">{selectedCell.riskCode}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-ink-muted">Payout Rate</span>
                <span className="text-ink-primary font-medium">₹{selectedCell.rate}/hour</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-ink-muted">Active Signals</span>
                <span className="text-ink-primary font-medium">{selectedCell.activeEventCount}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-ink-muted">Last Updated</span>
                <span className="text-ink-primary font-medium">{new Date(selectedCell.lastUpdated).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: true })}</span>
              </div>
            </div>

            {/* Coverage status */}
            <div className={`p-4 rounded-xl ${
              selectedCell.status === "safe"
                ? "bg-green-50 border border-green-200"
                : "bg-amber-50 border border-amber-200"
            }`}>
              <div className="flex items-center gap-2">
                {selectedCell.status === "safe" ? (
                  <>
                    <Shield className="w-5 h-5 text-green-600" />
                    <span className="text-sm font-semibold text-green-700">You are covered ✓</span>
                  </>
                ) : (
                  <>
                    <AlertTriangle className="w-5 h-5 text-amber-600" />
                    <button
                      onClick={() => router.push("/dashboard#pricing-plans")}
                      className="text-sm font-semibold text-amber-700 hover:underline"
                    >
                      View pricing plans →
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
