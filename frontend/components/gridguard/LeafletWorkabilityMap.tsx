"use client";

import { useEffect } from "react";
import { divIcon } from "leaflet";
import { CircleMarker, MapContainer, Marker, Polygon, TileLayer, Tooltip, useMap, ZoomControl } from "react-leaflet";

type MapHexCell = {
  h3Index: string;
  score: number;
  zoneName: string;
  event: string;
  rate: number;
  areaName?: string;
  riskCode?: string;
  status?: string;
  boundary: [number, number][];
  centroid: [number, number];
};

interface LeafletWorkabilityMapProps {
  center: [number, number];
  cells: MapHexCell[];
  selectedCellId?: string;
  userLocation: [number, number];
  onSelectCell: (cell: MapHexCell) => void;
}

function FlyToSelection({ center }: { center: [number, number] }) {
  const map = useMap();

  useEffect(() => {
    map.flyTo(center, Math.max(map.getZoom(), 12), {
      duration: 0.7,
    });
  }, [center, map]);

  return null;
}

function colorForCell(cell: MapHexCell): string {
  if (cell.status === "safe") return "#16a34a";
  if (cell.status === "caution") return "#f59e0b";
  if (cell.status === "disrupted") return "#ef4444";

  if (cell.score >= 0.95) return "#16a34a";
  if (cell.score >= 0.85) return "#f59e0b";
  return "#ef4444";
}

type EventMarkerVisual = {
  symbolHtml: string;
  bgColor: string;
  borderColor: string;
  glowColor: string;
  label: string;
};

function markerVisualForEvent(eventName: string): EventMarkerVisual {
  const normalized = eventName.toLowerCase();

  if (normalized.includes("traffic") || normalized.includes("road")) {
    return {
      symbolHtml: "&#128678;",
      bgColor: "#f59e0b",
      borderColor: "#fbbf24",
      glowColor: "rgba(245, 158, 11, 0.45)",
      label: "Traffic",
    };
  }

  if (normalized.includes("rain") || normalized.includes("storm") || normalized.includes("cloud")) {
    return {
      symbolHtml: "&#9729;",
      bgColor: "#0ea5e9",
      borderColor: "#38bdf8",
      glowColor: "rgba(14, 165, 233, 0.45)",
      label: "Rain",
    };
  }

  if (normalized.includes("heat")) {
    return {
      symbolHtml: "&#9728;",
      bgColor: "#f97316",
      borderColor: "#fb923c",
      glowColor: "rgba(249, 115, 22, 0.45)",
      label: "Heat",
    };
  }

  if (normalized.includes("aqi") || normalized.includes("air")) {
    return {
      symbolHtml: "&#127787;",
      bgColor: "#8b5cf6",
      borderColor: "#a78bfa",
      glowColor: "rgba(139, 92, 246, 0.45)",
      label: "AQI",
    };
  }

  if (normalized.includes("outage") || normalized.includes("app")) {
    return {
      symbolHtml: "&#128241;",
      bgColor: "#ef4444",
      borderColor: "#f87171",
      glowColor: "rgba(239, 68, 68, 0.45)",
      label: "Outage",
    };
  }

  return {
    symbolHtml: "&#9679;",
    bgColor: "#64748b",
    borderColor: "#94a3b8",
    glowColor: "rgba(100, 116, 139, 0.4)",
    label: "Clear",
  };
}

function markerIconForCell(eventName: string, selected: boolean) {
  const visual = markerVisualForEvent(eventName);
  const size = selected ? 30 : 26;

  return divIcon({
    className: "gridguard-event-marker",
    html: `<div style="
      width:${size}px;
      height:${size}px;
      display:flex;
      align-items:center;
      justify-content:center;
      clip-path:polygon(25% 6%,75% 6%,100% 50%,75% 94%,25% 94%,0 50%);
      background:${visual.bgColor};
      border:${selected ? 2 : 1.5}px solid ${selected ? "#ffffff" : visual.borderColor};
      box-shadow:0 0 0 1px rgba(0,0,0,0.24), 0 0 18px ${visual.glowColor};
      color:#ffffff;
      font-size:${selected ? 14 : 12}px;
      line-height:1;
      text-shadow:0 1px 2px rgba(0,0,0,0.45);
    ">${visual.symbolHtml}</div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

export default function LeafletWorkabilityMap({
  center,
  cells,
  selectedCellId,
  userLocation,
  onSelectCell,
}: LeafletWorkabilityMapProps) {
  return (
    <MapContainer
      center={center}
      zoom={12}
      zoomControl={false}
      className="h-full w-full"
      scrollWheelZoom={true}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
      />
      <ZoomControl position="bottomright" />
      <FlyToSelection center={selectedCellId ? (cells.find((cell) => cell.h3Index === selectedCellId)?.centroid || center) : center} />

      {cells.map((cell) => {
        const selected = selectedCellId === cell.h3Index;
        const fillColor = colorForCell(cell);
        const eventVisual = markerVisualForEvent(cell.event);
        const hasDisruptionEvent = cell.event.toLowerCase() !== "clear";

        const layers = [
          <Polygon
            key={`${cell.h3Index}-poly`}
              positions={cell.boundary}
              pathOptions={{
                color: selected ? "#ffffff" : "rgba(255,255,255,0.35)",
                weight: selected ? 2 : 1,
                fillColor,
                fillOpacity: selected ? 0.65 : 0.45,
              }}
              eventHandlers={{
                click: () => onSelectCell(cell),
              }}
            >
              <Tooltip sticky>
                <div className="text-xs">
                  <p className="font-semibold">{cell.areaName || `Zone ${cell.zoneName}`}</p>
                  <p>{cell.event}</p>
                  {cell.riskCode && <p>Risk Code {cell.riskCode}</p>}
                  {cell.status && <p className="capitalize">Status {cell.status}</p>}
                  <p>Score {cell.score.toFixed(2)}</p>
                </div>
              </Tooltip>
          </Polygon>,
        ];

        if (hasDisruptionEvent) {
          layers.push(
            <Marker
              key={`${cell.h3Index}-marker`}
                position={cell.centroid}
                icon={markerIconForCell(cell.event, selected)}
                zIndexOffset={selected ? 900 : 500}
                eventHandlers={{
                  click: () => onSelectCell(cell),
                }}
              >
                <Tooltip direction="top" offset={[0, -12]}>
                  <div className="text-xs">
                    <p className="font-semibold">{eventVisual.label} Signal</p>
                    <p>{cell.areaName || `Zone ${cell.zoneName}`}</p>
                  </div>
                </Tooltip>
            </Marker>,
          );
        }

        return layers;
      })}

      <CircleMarker
        center={userLocation}
        radius={7}
        pathOptions={{
          color: "#7dd3fc",
          weight: 2,
          fillColor: "#ffffff",
          fillOpacity: 1,
        }}
      >
        <Tooltip>Your location</Tooltip>
      </CircleMarker>
    </MapContainer>
  );
}
