import type { AirportSummary } from "../types/airport";

export interface GeoHome {
  latitude: number;
  longitude: number;
  location_label?: string | null;
  nearest_airport: AirportSummary;
  distance_nm: number;
  zoom: number;
}

export async function fetchGeoHome(): Promise<GeoHome> {
  const res = await fetch("/api/v1/geo/home");
  if (!res.ok) throw new Error(`Geo home failed: ${res.status}`);
  return res.json() as Promise<GeoHome>;
}
