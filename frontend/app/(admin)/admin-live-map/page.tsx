"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, CloudRain, Map as MapIcon, MapPin, Smartphone, Sun, Table2, TrafficCone, Wind } from "lucide-react";
import { cellToBoundary } from "h3-js";
import { CITIES } from "@/lib/mock-data";
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

type CityWorkabilityResponse = {
  city: string;
  cells: Array<{
    h3_cell: string;
    workability_score: number;
    status: "safe" | "caution" | "disrupted";
    payout_rate_hr?: number;
    area_name?: string;
    risk_code?: string;
    active_events: Array<{
      event_type: string;
    }>;
  }>;
};

type AdminZone = {
  h3Index: string;
  score: number;
  zone: string;
  areaName: string;
  riskCode: string;
  status: "safe" | "caution" | "disrupted";
  event: string;
  rate: number;
  boundary: [number, number][];
  centroid: [number, number];
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

type ViewMode = "map" | "table";

function fallbackRiskCode(score: number): string {
  if (score >= 0.7) return "R1";
  if (score >= 0.4) return "R2";
  if (score >= 0.2) return "R3";
  return "R4";
}

function scoreLabel(status: AdminZone["status"], score: number): string {
  if (status === "safe") return "Safe";
  if (status === "caution") return "Caution";
  if (status === "disrupted") return "Disrupted";
  if (score >= 0.95) return "Safe";
  if (score >= 0.85) return "Caution";
  return "Disrupted";
}

function scoreColor(status: AdminZone["status"], score: number): string {
  if (status === "safe") return "bg-green-100 text-green-700";
  if (status === "caution") return "bg-amber-100 text-amber-700";
  if (status === "disrupted") return "bg-red-100 text-red-700";
  if (score >= 0.95) return "bg-green-100 text-green-700";
  if (score >= 0.85) return "bg-amber-100 text-amber-700";
  return "bg-red-100 text-red-700";
}

function statusTone(status: AdminZone["status"]): string {
  if (status === "safe") return "bg-green-100 text-green-700";
  if (status === "caution") return "bg-amber-100 text-amber-700";
  return "bg-red-100 text-red-700";
}

function eventIcon(eventLabel: string) {
  const normalized = eventLabel.toLowerCase();

  if (normalized.includes("traffic") || normalized.includes("road")) {
    return <TrafficCone className="w-3.5 h-3.5 text-amber-600" />;
  }

  if (normalized.includes("rain") || normalized.includes("storm") || normalized.includes("cloud")) {
    return <CloudRain className="w-3.5 h-3.5 text-sky-600" />;
  }

  if (normalized.includes("heat")) {
    return <Sun className="w-3.5 h-3.5 text-orange-600" />;
  }

  if (normalized.includes("aqi") || normalized.includes("air")) {
    return <Wind className="w-3.5 h-3.5 text-violet-600" />;
  }

  if (normalized.includes("outage") || normalized.includes("app")) {
    return <Smartphone className="w-3.5 h-3.5 text-rose-600" />;
  }

  return <AlertTriangle className="w-3.5 h-3.5 text-slate-500" />;
}

export default function AdminLiveMapPage() {
  const [city, setCity] = useState("Bengaluru");
  const [zones, setZones] = useState<AdminZone[]>([]);
  const [selectedZone, setSelectedZone] = useState<AdminZone | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("map");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const mapCenter = CITY_CENTROIDS[city] || CITY_CENTROIDS.Bengaluru;

  useEffect(() => {
    const run = async () => {
      try {
        setLoading(true);
        setError("");

        const response = await apiGet<CityWorkabilityResponse>(`/grid/workability/city/${city.toLowerCase()}`);
        const mapped = response.cells.map((cell) => {
          const firstEvent = cell.active_events[0];
          const rawBoundary = cellToBoundary(cell.h3_cell);
          const boundary = rawBoundary.map((point) => [point[0], point[1]] as [number, number]);
          const centroid: [number, number] = boundary.reduce(
            (acc, point) => [acc[0] + point[0] / boundary.length, acc[1] + point[1] / boundary.length],
            [0, 0],
          );
          const zone = zoneFromH3(cell.h3_cell);

          return {
            h3Index: cell.h3_cell,
            score: cell.workability_score,
            zone,
            areaName: cell.area_name?.trim() || `${city} - Zone ${zone}`,
            riskCode: cell.risk_code || fallbackRiskCode(cell.workability_score),
            status: cell.status,
            event: firstEvent ? toEventLabel(firstEvent.event_type) : "Clear",
            rate: Number(cell.payout_rate_hr ?? 0),
            boundary,
            centroid,
          };
        });

        setZones(mapped);
        setSelectedZone(mapped[0] || null);
      } catch (err) {
        setZones([]);
        setSelectedZone(null);
        setError(err instanceof ApiError ? err.message : "Unable to load live map zones.");
      } finally {
        setLoading(false);
      }
    };

    run();
  }, [city]);

  const sortedCells = useMemo(() => [...zones].sort((a, b) => a.score - b.score), [zones]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-ink-primary">Live Hexagon Map</h1>
          <p className="text-sm text-ink-muted">All live hexagons in {city} with area name, status, and risk code</p>
        </div>
        <div className="flex items-center gap-3 flex-wrap justify-end">
          <div className="inline-flex rounded-lg border border-slate-200 bg-white p-1">
            <button
              onClick={() => setViewMode("map")}
              className={`h-8 px-3 rounded-md text-xs font-semibold flex items-center gap-1.5 transition-colors ${
                viewMode === "map" ? "bg-navy text-white" : "text-ink-secondary hover:bg-slate-100"
              }`}
            >
              <MapIcon className="w-3.5 h-3.5" />
              Map View
            </button>
            <button
              onClick={() => setViewMode("table")}
              className={`h-8 px-3 rounded-md text-xs font-semibold flex items-center gap-1.5 transition-colors ${
                viewMode === "table" ? "bg-navy text-white" : "text-ink-secondary hover:bg-slate-100"
              }`}
            >
              <Table2 className="w-3.5 h-3.5" />
              Tab View
            </button>
          </div>
          <select
            value={city}
            onChange={(e) => setCity(e.target.value)}
            className="h-9 px-3 rounded-lg border border-gray-200 text-sm outline-none"
          >
            {CITIES.map((cityValue) => (
              <option key={cityValue} value={cityValue}>
                {cityValue}
              </option>
            ))}
          </select>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-red-50 text-red-700 text-sm font-medium">
            <AlertTriangle className="w-4 h-4" />
            Showing all {zones.length} hexagons
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {viewMode === "map" && (
        <div className="relative h-[460px] overflow-hidden rounded-2xl border border-slate-200 bg-[#0b1320]">
          <LeafletWorkabilityMap
            center={mapCenter}
            cells={zones.map((zone) => ({
              h3Index: zone.h3Index,
              score: zone.score,
              zoneName: zone.zone,
              areaName: zone.areaName,
              riskCode: zone.riskCode,
              status: zone.status,
              event: zone.event,
              rate: zone.rate,
              boundary: zone.boundary,
              centroid: zone.centroid,
            }))}
            selectedCellId={selectedZone?.h3Index}
            userLocation={selectedZone?.centroid || mapCenter}
            onSelectCell={(cell) => {
              const nextSelected = zones.find((zone) => zone.h3Index === cell.h3Index) || null;
              setSelectedZone(nextSelected);
            }}
          />

          {!loading && zones.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center px-6 text-center pointer-events-none">
              <div className="rounded-2xl bg-black/55 border border-white/10 px-5 py-4 text-sm text-white/85">
                No zone workability data available for this city yet.
              </div>
            </div>
          )}
        </div>
      )}

      {selectedZone && (
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-sm font-semibold text-navy">{selectedZone.areaName}</span>
            <span className={`px-2 py-1 rounded-full text-xs font-semibold ${statusTone(selectedZone.status)}`}>
              {scoreLabel(selectedZone.status, selectedZone.score)}
            </span>
            <span className="px-2 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700">
              Risk Code {selectedZone.riskCode}
            </span>
            <span className="text-xs text-ink-muted">{selectedZone.h3Index}</span>
          </div>
        </div>
      )}

      {viewMode === "table" && (
        <div className="rounded-2xl border border-slate-200 bg-white overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-ink-primary">{city} Zone Table</h3>
            <p className="text-xs text-ink-muted">Click a row to focus it on map markers</p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[780px] text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-ink-secondary">
                <tr>
                  <th className="px-4 py-3 text-left">Area</th>
                  <th className="px-4 py-3 text-left">Risk</th>
                  <th className="px-4 py-3 text-left">Event</th>
                  <th className="px-4 py-3 text-left">Status</th>
                  <th className="px-4 py-3 text-left">Workability</th>
                  <th className="px-4 py-3 text-left">Payout Rate</th>
                  <th className="px-4 py-3 text-left">Hex</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {sortedCells.map((cell, index) => {
                  const selected = selectedZone?.h3Index === cell.h3Index;
                  return (
                    <motion.tr
                      key={cell.h3Index}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.02 }}
                      className={`cursor-pointer transition-colors ${selected ? "bg-slate-50" : "hover:bg-slate-50/60"}`}
                      onClick={() => {
                        setSelectedZone(cell);
                        setViewMode("map");
                      }}
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1.5">
                          <MapPin className="w-3.5 h-3.5 text-navy" />
                          <span className="font-semibold text-ink-primary">{cell.areaName}</span>
                        </div>
                        <p className="text-xs text-ink-muted mt-0.5">Zone {cell.zone}</p>
                      </td>
                      <td className="px-4 py-3 font-semibold text-ink-primary">{cell.riskCode}</td>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center gap-1.5 font-medium text-ink-primary">
                          {eventIcon(cell.event)}
                          <span>{cell.event}</span>
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded-full text-xs font-semibold ${statusTone(cell.status)}`}>
                          {cell.status.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded-full text-xs font-semibold ${scoreColor(cell.status, cell.score)}`}>
                          {cell.score.toFixed(2)}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-medium text-ink-primary">₹{cell.rate}/hour</td>
                      <td className="px-4 py-3 text-xs text-ink-muted">{cell.h3Index}</td>
                    </motion.tr>
                  );
                })}

                {!loading && sortedCells.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-sm text-ink-muted">
                      No zone workability data available for this city yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
