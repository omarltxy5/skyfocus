import L from "leaflet";
import { useCallback, useEffect, useRef } from "react";
import { useMap, useMapEvents } from "react-leaflet";
import {
  fetchAirportHubs,
  fetchAirportIntelligence,
  fetchAirportsInBbox,
} from "../services/airportsApi";
import type { AirportIntelligence, AirportSummary } from "../types/airport";
import { createAirportPinIcon } from "../utils/mapIcons";
import { airportPopupHtml } from "./popups";

const HUB_ZOOM_MAX = 6;
const DEBOUNCE_MS = 250;

interface Props {
  onCountChange?: (count: number) => void;
  onAirportSelect?: (ap: AirportSummary, intel: AirportIntelligence | null) => void;
}

export default function AirportLayer({ onCountChange, onAirportSelect }: Props) {
  const map = useMap();
  const markersRef = useRef<Map<string, L.Marker>>(new Map());
  const airportsRef = useRef<Map<string, AirportSummary>>(new Map());
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearMarkers = useCallback(() => {
    for (const m of markersRef.current.values()) {
      map.removeLayer(m);
    }
    markersRef.current.clear();
    airportsRef.current.clear();
    onCountChange?.(0);
  }, [map, onCountChange]);

  const renderAirports = useCallback(
    (airports: AirportSummary[]) => {
      const markers = markersRef.current;
      const store = airportsRef.current;
      const seen = new Set<string>();

      for (const ap of airports) {
        seen.add(ap.icao);
        store.set(ap.icao, ap);
        const large = ap.type === "large_airport";
        const icon = createAirportPinIcon(large);
        let marker = markers.get(ap.icao);

        if (!marker) {
          marker = L.marker([ap.latitude, ap.longitude], {
            icon,
            zIndexOffset: 400,
          });
          marker.bindTooltip(`${ap.icao} · ${ap.name}`, {
            direction: "top",
            offset: [0, -36],
            className: "skyfocus-tooltip",
          });
          marker.on("click", async (e) => {
            L.DomEvent.stopPropagation(e);
            marker!.bindPopup(
              `<div class="sky-popup"><strong>${ap.icao}</strong><br/><em>Loading intelligence…</em></div>`,
              { className: "sky-popup-wrap", maxWidth: 340 },
            );
            marker!.openPopup();
            try {
              const intel = await fetchAirportIntelligence(ap.icao);
              marker!.setPopupContent(airportPopupHtml(ap, intel, null));
              onAirportSelect?.(ap, intel);
            } catch (err) {
              marker!.setPopupContent(
                airportPopupHtml(
                  ap,
                  null,
                  err instanceof Error ? err.message : "Failed to load",
                ),
              );
              onAirportSelect?.(ap, null);
            }
          });
          marker.addTo(map);
          markers.set(ap.icao, marker);
        } else {
          marker.setLatLng([ap.latitude, ap.longitude]);
          marker.setIcon(icon);
        }
      }

      for (const [icao, marker] of markers) {
        if (!seen.has(icao)) {
          map.removeLayer(marker);
          markers.delete(icao);
          store.delete(icao);
        }
      }
      onCountChange?.(airports.length);
    },
    [map, onCountChange, onAirportSelect],
  );

  const loadForView = useCallback(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      try {
        const zoom = map.getZoom();
        if (zoom <= HUB_ZOOM_MAX) {
          renderAirports((await fetchAirportHubs()).airports);
        } else {
          const b = map.getBounds();
          renderAirports(
            (
              await fetchAirportsInBbox(
                b.getSouth(),
                b.getWest(),
                b.getNorth(),
                b.getEast(),
              )
            ).airports,
          );
        }
      } catch (err) {
        console.warn("[AirportLayer]", err);
      }
    }, DEBOUNCE_MS);
  }, [map, renderAirports]);

  useEffect(() => {
    loadForView();
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      clearMarkers();
    };
  }, [loadForView, clearMarkers]);

  useMapEvents({ moveend: loadForView, zoomend: loadForView });

  return null;
}
