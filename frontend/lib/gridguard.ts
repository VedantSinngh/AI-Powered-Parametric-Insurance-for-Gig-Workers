export type UiEventType = "rain" | "heat" | "aqi" | "outage" | "traffic";

const EVENT_TYPE_MAP: Record<string, UiEventType> = {
  rainfall: "rain",
  rain: "rain",
  heat: "heat",
  aqi: "aqi",
  app_outage: "outage",
  outage: "outage",
  road_saturation: "traffic",
  traffic: "traffic",
};

const EVENT_LABEL_MAP: Record<UiEventType, string> = {
  rain: "Rainfall",
  heat: "Heat Alert",
  aqi: "AQI Spike",
  outage: "Platform Outage",
  traffic: "Road Saturation",
};

export function toUiEventType(eventType?: string | null): UiEventType {
  if (!eventType) {
    return "outage";
  }
  return EVENT_TYPE_MAP[eventType] || "outage";
}

export function toEventLabel(eventType?: string | null): string {
  const uiType = toUiEventType(eventType);
  return EVENT_LABEL_MAP[uiType];
}

export function zoneFromH3(h3Cell?: string | null): string {
  if (!h3Cell) {
    return "N/A";
  }
  const sanitized = h3Cell.replace(/[^a-zA-Z0-9]/g, "").toUpperCase();
  if (!sanitized) {
    return "N/A";
  }

  const meaningful = sanitized.replace(/F+$/, "");
  if (meaningful.length >= 4) {
    return meaningful.slice(-4);
  }
  if (sanitized.length >= 6) {
    return sanitized.slice(2, 6);
  }
  return sanitized;
}

export function formatIsoToUi(isoDate?: string | null): string {
  if (!isoDate) {
    return "Unknown";
  }

  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) {
    return "Unknown";
  }

  const now = new Date();
  const sameDay =
    now.getFullYear() === date.getFullYear() &&
    now.getMonth() === date.getMonth() &&
    now.getDate() === date.getDate();

  const yesterday = new Date();
  yesterday.setDate(now.getDate() - 1);
  const isYesterday =
    yesterday.getFullYear() === date.getFullYear() &&
    yesterday.getMonth() === date.getMonth() &&
    yesterday.getDate() === date.getDate();

  const time = date.toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });

  if (sameDay) {
    return `Today ${time}`;
  }
  if (isYesterday) {
    return `Yesterday ${time}`;
  }

  return date.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
}

export function formatDurationHours(durationHours?: number | null): string {
  if (!durationHours || durationHours <= 0) {
    return "-";
  }

  if (durationHours === 1) {
    return "1 hour";
  }

  if (durationHours < 1) {
    const mins = Math.round(durationHours * 60);
    return `${mins} min`;
  }

  return `${durationHours.toFixed(1)} hours`;
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return localStorage.getItem("gridguard_access_token");
}
