export interface MetarDecoded {
  station: string;
  observation_time?: string | null;
  wind?: {
    direction_deg?: number | null;
    speed_kt: number;
    gust_kt?: number | null;
    variable?: boolean;
  } | null;
  visibility?: string | null;
  weather: string[];
  clouds: string[];
  temperature_c?: number | null;
  dewpoint_c?: number | null;
  altimeter_inhg?: number | null;
  flight_category?: string | null;
  explanations: string[];
}

export interface AirportSummary {
  icao: string;
  name: string;
  latitude: number;
  longitude: number;
  elevation_ft?: number | null;
  type: string;
  iso_country?: string;
  municipality?: string | null;
  iata_code?: string | null;
}

export interface AirportListResponse {
  count: number;
  airports: AirportSummary[];
  mode: "bbox" | "hubs";
}

export interface AirportIntelligence {
  icao: string;
  metar_raw?: string | null;
  metar_decoded?: MetarDecoded | null;
  wind?: {
    direction_deg: number;
    speed_kt: number;
    gust_kt?: number | null;
  } | null;
  active_runway?: string | null;
  headwind_kt?: number | null;
  crosswind_kt?: number | null;
  runways: Array<{
    designator: string;
    heading_deg: number;
    headwind_kt: number;
    crosswind_kt: number;
  }>;
  updated_at?: number | null;
}
