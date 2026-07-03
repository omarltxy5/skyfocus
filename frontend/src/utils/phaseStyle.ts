import type { FlightPhase } from "../types/flight";

export const PHASE_COLORS: Record<FlightPhase, string> = {
  climb: "#3b82f6",
  cruise: "#94a3b8",
  descent: "#f59e0b",
  approach: "#22c55e",
  go_around: "#ef4444",
};

export function phaseColor(phase: FlightPhase, goAround: boolean): string {
  if (goAround || phase === "go_around") return PHASE_COLORS.go_around;
  return PHASE_COLORS[phase] ?? PHASE_COLORS.cruise;
}

export function phaseLabel(phase: FlightPhase, goAround: boolean): string {
  if (goAround || phase === "go_around") return "GO-AROUND";
  return phase.toUpperCase();
}
