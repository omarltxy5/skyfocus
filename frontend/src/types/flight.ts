export type FlightPhase =
  | "climb"
  | "cruise"
  | "descent"
  | "approach"
  | "go_around";

export interface FlightDelta {
  icao24: string;
  callsign: string;
  phase: FlightPhase;
  go_around: boolean;
  latitude: number;
  longitude: number;
  altitude_ft: number;
  vertical_speed_fpm: number;
  heading_deg?: number | null;
  ground_speed_kt?: number | null;
  inferred_runway?: string | null;
  nearest_airport?: string | null;
}

export interface WsUpdateMessage {
  type: "update";
  flights: FlightDelta[];
  ts: number;
}

export type BBox = [number, number, number, number]; // south, west, north, east

export interface FlightDetails {
  icao24: string;
  callsign: string;
  airline?: string | null;
  aircraft_type?: string | null;
  registration?: string | null;
  data_sources?: string[];
  origin_icao?: string | null;
  destination_icao?: string | null;
  origin_name?: string | null;
  destination_name?: string | null;
  photo_url?: string | null;
  phase?: string | null;
  go_around?: boolean;
  altitude_ft?: number | null;
  vertical_speed_fpm?: number | null;
  ground_speed_kt?: number | null;
  heading_deg?: number | null;
}
