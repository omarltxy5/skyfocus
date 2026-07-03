import { useCallback, useEffect, useMemo, useState } from "react";
import SkyMap from "./components/SkyMap";
import Sidebar from "./components/Sidebar";
import { fetchGeoHome } from "./services/geoApi";
import { fetchAirportIntelligence } from "./services/airportsApi";
import { telemetryWs } from "./services/telemetryWs";
import type { AirportIntelligence, AirportSummary } from "./types/airport";
import type { BBox, FlightDelta } from "./types/flight";

function App() {
  const [flights, setFlights] = useState<Record<string, FlightDelta>>({});
  const [selected, setSelected] = useState<FlightDelta | null>(null);
  const [selectedAirport, setSelectedAirport] = useState<AirportSummary | null>(null);
  const [airportIntel, setAirportIntel] = useState<AirportIntelligence | null>(null);
  const [connected, setConnected] = useState(false);
  const [airportCount, setAirportCount] = useState(0);
  const [mapCenter, setMapCenter] = useState<[number, number]>([40.64, -73.78]);
  const [mapZoom, setMapZoom] = useState(10);
  const [homeLabel, setHomeLabel] = useState<string | null>(null);

  const applyFlights = useCallback((incoming: FlightDelta[]) => {
    setFlights(() => {
      const next: Record<string, FlightDelta> = {};
      for (const f of incoming) {
        next[f.icao24] = f;
      }
      return next;
    });
  }, []);

  useEffect(() => {
    fetchGeoHome()
      .then(async (geo) => {
        const ap = geo.nearest_airport;
        setMapCenter([ap.latitude, ap.longitude]);
        setMapZoom(geo.zoom);
        setHomeLabel(
          geo.location_label
            ? `${geo.location_label} → ${ap.icao} (${geo.distance_nm} NM)`
            : `Nearest: ${ap.icao} (${geo.distance_nm} NM)`,
        );
        try {
          const intel = await fetchAirportIntelligence(ap.icao);
          setSelectedAirport(ap);
          setAirportIntel(intel);
        } catch {
          setSelectedAirport(ap);
          setAirportIntel(null);
        }
      })
      .catch(() => setHomeLabel(null));
  }, []);

  useEffect(() => {
    telemetryWs.connect();
    const unsub = telemetryWs.subscribe((delta) => applyFlights(delta));
    const unsubStatus = telemetryWs.onStatus(setConnected);
    return () => {
      unsub();
      unsubStatus();
      telemetryWs.disconnect();
    };
  }, [applyFlights]);

  const flightList = useMemo(() => Object.values(flights), [flights]);

  const handleBbox = useCallback((_bbox: BBox) => {}, []);

  const handleAirportSelect = useCallback(
    (ap: AirportSummary, intel: AirportIntelligence | null) => {
      setSelected(null);
      setSelectedAirport(ap);
      setAirportIntel(intel);
    },
    [],
  );

  const handleFlightSelect = useCallback((f: FlightDelta | null) => {
    setSelected(f);
    if (f) {
      setSelectedAirport(null);
      setAirportIntel(null);
    }
  }, []);

  const clearAirport = useCallback(() => {
    setSelectedAirport(null);
    setAirportIntel(null);
  }, []);

  return (
    <div className="h-screen flex flex-col bg-sky-950 text-slate-100 overflow-hidden">
      <header className="shrink-0 border-b border-sky-800 px-6 py-3 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">SkyFocus</h1>
          <p className="text-xs text-slate-400">
            {homeLabel ?? "Resolving your nearest airport…"}
          </p>
        </div>
        <div className="flex gap-4 text-xs font-mono text-slate-500">
          <span>
            {connected ? "Live OpenSky ADS-B" : "Connecting…"}
            {airportCount > 0 ? ` · ${airportCount} airports` : ""}
          </span>
          <a
            href="http://127.0.0.1:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="text-sky-400 hover:underline"
          >
            API
          </a>
        </div>
      </header>
      <div className="flex-1 flex min-h-0">
        <Sidebar
          flights={flightList}
          selected={selected}
          onSelect={handleFlightSelect}
          selectedAirport={selectedAirport}
          airportIntel={airportIntel}
          onClearAirport={clearAirport}
          connected={connected}
          aircraftCount={flightList.length}
        />
        <main className="flex-1 min-w-0 relative">
          <SkyMap
            flights={flights}
            onBboxChange={handleBbox}
            onSelect={handleFlightSelect}
            onAirportCountChange={setAirportCount}
            onAirportSelect={handleAirportSelect}
            mapCenter={mapCenter}
            mapZoom={mapZoom}
          />
        </main>
      </div>
    </div>
  );
}

export default App;
