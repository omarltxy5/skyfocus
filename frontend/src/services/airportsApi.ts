import type { AirportIntelligence, AirportListResponse } from "../types/airport";

export async function fetchAirportsInBbox(
  minLat: number,
  minLon: number,
  maxLat: number,
  maxLon: number,
): Promise<AirportListResponse> {
  const q = new URLSearchParams({
    min_lat: String(minLat),
    min_lon: String(minLon),
    max_lat: String(maxLat),
    max_lon: String(maxLon),
  });
  const res = await fetch(`/api/v1/airports?${q}`);
  if (!res.ok) throw new Error(`Airports fetch failed: ${res.status}`);
  return res.json() as Promise<AirportListResponse>;
}

export async function fetchAirportHubs(): Promise<AirportListResponse> {
  const res = await fetch("/api/v1/airports");
  if (!res.ok) throw new Error(`Airport hubs fetch failed: ${res.status}`);
  return res.json() as Promise<AirportListResponse>;
}

export async function fetchAirportIntelligence(
  icao: string,
): Promise<AirportIntelligence> {
  const res = await fetch(`/api/v1/airports/${icao}/intelligence`);
  if (!res.ok) {
    const err = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(err.detail ?? `Intelligence fetch failed: ${res.status}`);
  }
  return res.json() as Promise<AirportIntelligence>;
}
