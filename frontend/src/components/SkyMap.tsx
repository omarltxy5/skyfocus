import { useCallback, useEffect } from "react";
import { MapContainer, TileLayer, useMap, useMapEvents } from "react-leaflet";
import type { AirportIntelligence, AirportSummary } from "../types/airport";
import type { BBox, FlightDelta } from "../types/flight";
import { telemetryWs } from "../services/telemetryWs";
import AircraftLayer from "./AircraftLayer";
import AirportLayer from "./AirportLayer";
import MapViewController from "./MapViewController";

interface Props {
  flights: Record<string, FlightDelta>;
  onBboxChange: (bbox: BBox) => void;
  onSelect?: (flight: FlightDelta) => void;
  onAirportCountChange?: (count: number) => void;
  onAirportSelect?: (ap: AirportSummary, intel: AirportIntelligence | null) => void;
  mapCenter: [number, number];
  mapZoom: number;
}

function BboxSync({ onBboxChange }: { onBboxChange: (b: BBox) => void }) {
  const map = useMap();

  const emit = useCallback(() => {
    const b = map.getBounds();
    const bbox: BBox = [b.getSouth(), b.getWest(), b.getNorth(), b.getEast()];
    onBboxChange(bbox);
    telemetryWs.setBbox(bbox);
  }, [map, onBboxChange]);

  useEffect(() => {
    emit();
  }, [emit]);

  useMapEvents({
    moveend: emit,
    zoomend: emit,
  });

  return null;
}

export default function SkyMap({
  flights,
  onBboxChange,
  onSelect,
  onAirportCountChange,
  onAirportSelect,
  mapCenter,
  mapZoom,
}: Props) {
  const flyTarget: [number, number] | null = mapCenter;

  return (
    <MapContainer
      center={mapCenter}
      zoom={mapZoom}
      className="h-full w-full z-0"
      preferCanvas
      scrollWheelZoom
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <MapViewController center={flyTarget} zoom={mapZoom} />
      <BboxSync onBboxChange={onBboxChange} />
      <AirportLayer
        onCountChange={onAirportCountChange}
        onAirportSelect={onAirportSelect}
      />
      <AircraftLayer flights={flights} onSelect={onSelect} />
    </MapContainer>
  );
}
