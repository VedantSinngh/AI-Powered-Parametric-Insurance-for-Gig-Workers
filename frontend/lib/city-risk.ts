import { apiGet } from "@/lib/api";

export type RiskTier = "low" | "medium" | "high" | "critical";
export type WorkabilityStatus = "safe" | "caution" | "disrupted";

export type CityWorkabilityCell = {
  h3_cell: string;
  workability_score: number;
  status?: string;
  active_events?: Array<{
    event_type?: string;
    severity?: number;
    raw_value?: number;
  }>;
};

export type CityRiskSummary = {
  avg_workability_score: number;
  risk_score: number;
  risk_tier: RiskTier;
  status: WorkabilityStatus;
  safe_cells: number;
  caution_cells: number;
  disrupted_cells: number;
  active_events: number;
};

type CityWorkabilityResponse = {
  city: string;
  total: number;
  cells: CityWorkabilityCell[];
  summary?: CityRiskSummary & {
    timestamp?: string;
  };
};

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

export function scoreToRiskTier(riskScore: number): RiskTier {
  if (riskScore < 0.3) {
    return "low";
  }
  if (riskScore < 0.6) {
    return "medium";
  }
  if (riskScore < 0.8) {
    return "high";
  }
  return "critical";
}

export function summarizeCityWorkability(cells: CityWorkabilityCell[]): CityRiskSummary {
  if (cells.length === 0) {
    return {
      avg_workability_score: 1,
      risk_score: 0,
      risk_tier: "low",
      status: "safe",
      safe_cells: 0,
      caution_cells: 0,
      disrupted_cells: 0,
      active_events: 0,
    };
  }

  let safeCells = 0;
  let cautionCells = 0;
  let disruptedCells = 0;
  let totalScore = 0;
  let minScore = 1;
  let activeEvents = 0;
  const severityValues: number[] = [];

  for (const cell of cells) {
    const score = clamp(Number(cell.workability_score || 0), 0, 1);
    totalScore += score;
    minScore = Math.min(minScore, score);

    if (score >= 0.7) {
      safeCells += 1;
    } else if (score >= 0.4) {
      cautionCells += 1;
    } else {
      disruptedCells += 1;
    }

    const events = cell.active_events || [];
    activeEvents += events.length;

    for (const event of events) {
      if (typeof event.severity === "number") {
        severityValues.push(clamp(event.severity, 0, 1));
      }
    }
  }

  const avgWorkability = totalScore / cells.length;
  const disruptedRatio = disruptedCells / cells.length;
  const cautionRatio = cautionCells / cells.length;
  const avgSeverity = severityValues.length > 0
    ? severityValues.reduce((sum, value) => sum + value, 0) / severityValues.length
    : 0;

  const riskScore = clamp(
    (1 - avgWorkability) * 0.4
      + disruptedRatio * 0.2
      + cautionRatio * 0.05
      + avgSeverity * 0.1
      + (1 - minScore) * 0.25,
    0,
    1,
  );

  return {
    avg_workability_score: Number(avgWorkability.toFixed(4)),
    risk_score: Number(riskScore.toFixed(4)),
    risk_tier: scoreToRiskTier(riskScore),
    status: avgWorkability >= 0.7 ? "safe" : avgWorkability >= 0.4 ? "caution" : "disrupted",
    safe_cells: safeCells,
    caution_cells: cautionCells,
    disrupted_cells: disruptedCells,
    active_events: activeEvents,
  };
}

export async function fetchCityRiskSummary(city: string): Promise<CityRiskSummary | null> {
  const cityKey = city.trim().toLowerCase();
  if (!cityKey) {
    return null;
  }

  const response = await apiGet<CityWorkabilityResponse>(`/grid/workability/city/${encodeURIComponent(cityKey)}`);
  if (response.summary) {
    return {
      ...response.summary,
      risk_tier: scoreToRiskTier(response.summary.risk_score),
    };
  }
  return summarizeCityWorkability(response.cells || []);
}
