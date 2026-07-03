import type { FlightDetails } from "../types/flight";

export async function fetchFlightDetails(icao24: string): Promise<FlightDetails> {
  const res = await fetch(`/api/v1/flights/icao/${icao24}/details`);
  if (!res.ok) {
    const err = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(err.detail ?? `Flight details failed: ${res.status}`);
  }
  return res.json() as Promise<FlightDetails>;
}
