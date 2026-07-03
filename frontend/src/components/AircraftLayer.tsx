import L from "leaflet";
import { useEffect, useRef } from "react";
import { useMap } from "react-leaflet";
import { fetchFlightDetails } from "../services/flightsApi";
import type { FlightDelta } from "../types/flight";
import { createPlaneIcon } from "../utils/mapIcons";
import { phaseColor } from "../utils/phaseStyle";
import { flightPopupHtml, flightPopupLoading } from "./popups";

interface Props {
  flights: Record<string, FlightDelta>;
  onSelect?: (flight: FlightDelta) => void;
}

export default function AircraftLayer({ flights, onSelect }: Props) {
  const map = useMap();
  const markersRef = useRef<Map<string, L.Marker>>(new Map());
  const pulseRef = useRef(0);

  useEffect(() => {
    const markers = markersRef.current;
    const seen = new Set<string>();

    for (const f of Object.values(flights)) {
      seen.add(f.icao24);
      const color = phaseColor(f.phase, f.go_around);
      const heading = f.heading_deg ?? 0;
      const icon = createPlaneIcon(heading, color, f.go_around);
      let marker = markers.get(f.icao24);

      if (!marker) {
        marker = L.marker([f.latitude, f.longitude], { icon, zIndexOffset: 800 });
        marker.bindTooltip(f.callsign.trim(), {
          direction: "top",
          className: "skyfocus-tooltip",
          offset: [0, -12],
        });
        marker.on("click", async (e) => {
          L.DomEvent.stopPropagation(e);
          onSelect?.(f);
          marker!.bindPopup(flightPopupLoading(f), {
            className: "sky-popup-wrap",
            maxWidth: 340,
          });
          marker!.openPopup();
          try {
            const details = await fetchFlightDetails(f.icao24);
            marker!.setPopupContent(flightPopupHtml(f, details, null));
          } catch (err) {
            marker!.setPopupContent(
              flightPopupHtml(
                f,
                null,
                err instanceof Error ? err.message : "Failed to load",
              ),
            );
          }
        });
        marker.addTo(map);
        markers.set(f.icao24, marker);
      } else {
        marker.setLatLng([f.latitude, f.longitude]);
        marker.setIcon(icon);
        marker.setTooltipContent(f.callsign.trim());
      }
    }

    for (const [id, marker] of markers) {
      if (!seen.has(id)) {
        map.removeLayer(marker);
        markers.delete(id);
      }
    }
  }, [flights, map, onSelect]);

  useEffect(() => {
    const id = window.setInterval(() => {
      pulseRef.current = pulseRef.current === 0 ? 1 : 0;
      for (const f of Object.values(flights)) {
        if (!f.go_around) continue;
        const el = markersRef.current.get(f.icao24)?.getElement();
        if (el) el.style.opacity = pulseRef.current ? "1" : "0.5";
      }
    }, 500);
    return () => clearInterval(id);
  }, [flights]);

  return null;
}
