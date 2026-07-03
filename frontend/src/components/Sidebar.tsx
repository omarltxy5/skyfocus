import { useEffect, useState } from "react";
import { fetchFlightDetails } from "../services/flightsApi";
import type { AirportIntelligence, AirportSummary } from "../types/airport";
import type { FlightDelta, FlightDetails } from "../types/flight";
import { phaseColor, phaseLabel } from "../utils/phaseStyle";

interface Props {
  flights: FlightDelta[];
  selected: FlightDelta | null;
  onSelect: (f: FlightDelta | null) => void;
  selectedAirport: AirportSummary | null;
  airportIntel: AirportIntelligence | null;
  onClearAirport: () => void;
  connected: boolean;
  aircraftCount: number;
}

function categoryBadge(cat: string | null | undefined) {
  const colors: Record<string, string> = {
    VFR: "bg-emerald-900/70 text-emerald-200",
    MVFR: "bg-amber-900/70 text-amber-200",
    IFR: "bg-orange-900/70 text-orange-200",
    LIFR: "bg-red-900/70 text-red-200",
  };
  const cls = colors[cat ?? ""] ?? "bg-slate-800 text-slate-300";
  return (
    <span className={`text-xs font-mono px-2 py-0.5 rounded ${cls}`}>{cat ?? "—"}</span>
  );
}

export default function Sidebar({
  flights,
  selected,
  onSelect,
  selectedAirport,
  airportIntel,
  onClearAirport,
  connected,
  aircraftCount,
}: Props) {
  const [details, setDetails] = useState<FlightDetails | null>(null);
  const [detailsLoading, setDetailsLoading] = useState(false);

  useEffect(() => {
    if (!selected) {
      setDetails(null);
      return;
    }
    let cancelled = false;
    setDetailsLoading(true);
    fetchFlightDetails(selected.icao24)
      .then((d) => {
        if (!cancelled) setDetails(d);
      })
      .catch(() => {
        if (!cancelled) setDetails(null);
      })
      .finally(() => {
        if (!cancelled) setDetailsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selected?.icao24]);

  const sorted = [...flights].sort((a, b) =>
    a.callsign.localeCompare(b.callsign),
  );

  if (selected) {
    return (
      <aside className="w-96 shrink-0 border-r border-sky-800 bg-sky-900/90 flex flex-col h-full overflow-hidden">
        <FlightPanel
          flight={selected}
          details={details}
          loading={detailsLoading}
          onBack={() => onSelect(null)}
        />
      </aside>
    );
  }

  if (selectedAirport) {
    return (
      <aside className="w-96 shrink-0 border-r border-sky-800 bg-sky-900/90 flex flex-col h-full overflow-hidden">
        <AirportPanel
          airport={selectedAirport}
          intel={airportIntel}
          onBack={onClearAirport}
        />
      </aside>
    );
  }

  return (
    <aside className="w-80 shrink-0 border-r border-sky-800 bg-sky-900/80 flex flex-col overflow-hidden">
      <div className="p-4 border-b border-sky-800 space-y-2 shrink-0">
        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-400">Feed</span>
          <span
            className={`font-mono text-xs px-2 py-0.5 rounded ${
              connected
                ? "bg-emerald-900/60 text-emerald-300"
                : "bg-red-900/60 text-red-300"
            }`}
          >
            {connected ? "LIVE" : "OFFLINE"}
          </span>
        </div>
        <p className="text-2xl font-semibold tabular-nums">{aircraftCount}</p>
        <p className="text-xs text-slate-500">Click a plane or airport on the map</p>
      </div>

      <div className="flex-1 overflow-y-auto">
        <ul className="divide-y divide-sky-800/80">
          {sorted.map((f) => {
            const color = phaseColor(f.phase, f.go_around);
            return (
              <li key={f.icao24}>
                <button
                  type="button"
                  onClick={() => onSelect(f)}
                  className={`w-full text-left px-4 py-3 hover:bg-sky-800/40 transition ${
                    f.go_around ? "go-around-row" : ""
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span
                      className="w-2.5 h-2.5 rounded-full shrink-0"
                      style={{ backgroundColor: color }}
                    />
                    <span className="font-mono font-medium">{f.callsign.trim()}</span>
                    <span className="ml-auto text-xs font-mono" style={{ color }}>
                      {phaseLabel(f.phase, f.go_around)}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1 pl-4">
                    {Math.round(f.altitude_ft)} ft · {Math.round(f.vertical_speed_fpm)} fpm
                  </p>
                </button>
              </li>
            );
          })}
        </ul>
        {sorted.length === 0 && (
          <p className="p-4 text-sm text-slate-500">No aircraft in view. Pan/zoom the map.</p>
        )}
      </div>
    </aside>
  );
}

function FlightPanel({
  flight,
  details,
  loading,
  onBack,
}: {
  flight: FlightDelta;
  details: FlightDetails | null;
  loading: boolean;
  onBack: () => void;
}) {
  const color = phaseColor(flight.phase, flight.go_around);
  return (
    <>
      <div className="shrink-0 p-3 border-b border-sky-800 flex items-center gap-2">
        <button
          type="button"
          onClick={onBack}
          className="text-sky-400 hover:text-sky-300 text-sm"
        >
          ← Back
        </button>
        <span className="font-mono font-semibold text-lg truncate flex-1">
          {flight.callsign.trim()}
        </span>
        <span className="text-xs font-mono" style={{ color }}>
          {phaseLabel(flight.phase, flight.go_around)}
        </span>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {details?.photo_url && (
          <img
            src={details.photo_url}
            alt="Aircraft"
            className="w-full h-48 object-cover rounded-lg border border-sky-700 shadow-lg"
            referrerPolicy="no-referrer"
          />
        )}
        {loading && <p className="text-slate-400 text-sm">Looking up registration…</p>}
        <section className="space-y-2">
          <h3 className="text-xs uppercase tracking-wide text-slate-500">Operator</h3>
          <p className="text-lg text-slate-100">{details?.airline ?? "—"}</p>
        </section>
        <section className="space-y-2">
          <h3 className="text-xs uppercase tracking-wide text-slate-500">Aircraft</h3>
          <p className="text-slate-200">{details?.aircraft_type ?? "—"}</p>
          {details?.registration && (
            <p className="font-mono text-sky-300">{details.registration}</p>
          )}
        </section>
        {(details?.origin_name || details?.destination_name) && (
          <section className="space-y-2">
            <h3 className="text-xs uppercase tracking-wide text-slate-500">Route</h3>
            <p className="text-slate-200 text-sm leading-relaxed">
              <span className="text-emerald-300">{details.origin_name ?? "—"}</span>
              <br />↓<br />
              <span className="text-sky-300">{details.destination_name ?? "—"}</span>
            </p>
          </section>
        )}
        <section className="grid grid-cols-2 gap-3 text-sm">
          <Stat label="Altitude" value={`${Math.round(flight.altitude_ft)} ft`} />
          <Stat label="VS" value={`${Math.round(flight.vertical_speed_fpm)} fpm`} />
          {flight.ground_speed_kt != null && (
            <Stat label="Speed" value={`${Math.round(flight.ground_speed_kt)} kt`} />
          )}
          {flight.heading_deg != null && (
            <Stat label="Heading" value={`${Math.round(flight.heading_deg)}°`} />
          )}
        </section>
        {details?.data_sources && details.data_sources.length > 0 && (
          <p className="text-[10px] text-slate-600 font-mono">
            Sources: {details.data_sources.join(", ")}
          </p>
        )}
      </div>
    </>
  );
}

function AirportPanel({
  airport,
  intel,
  onBack,
}: {
  airport: AirportSummary;
  intel: AirportIntelligence | null;
  onBack: () => void;
}) {
  return (
    <>
      <div className="shrink-0 p-3 border-b border-sky-800 flex items-center gap-2">
        <button type="button" onClick={onBack} className="text-sky-400 hover:text-sky-300 text-sm">
          ← Back
        </button>
        <span className="font-mono font-semibold truncate flex-1">{airport.icao}</span>
        {intel?.metar_decoded?.flight_category &&
          categoryBadge(intel.metar_decoded.flight_category)}
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div>
          <h2 className="text-lg font-medium text-slate-100">{airport.name}</h2>
          <p className="text-sm text-slate-500 capitalize">
            {airport.type.replace("_", " ")}
            {airport.municipality ? ` · ${airport.municipality}` : ""}
          </p>
        </div>
        {intel?.active_runway && (
          <section className="p-3 rounded-lg bg-sky-950/80 border border-sky-800">
            <h3 className="text-xs uppercase text-slate-500 mb-1">Inferred active runway</h3>
            <p className="text-2xl font-mono text-sky-300">{intel.active_runway}</p>
            {intel.headwind_kt != null && (
              <p className="text-sm text-slate-400 mt-1">{intel.headwind_kt} kt headwind</p>
            )}
          </section>
        )}
        {intel?.metar_raw && (
          <section>
            <h3 className="text-xs uppercase text-slate-500 mb-2">Raw METAR</h3>
            <p className="font-mono text-xs text-slate-400 break-all leading-relaxed p-2 bg-sky-950 rounded border border-sky-800">
              {intel.metar_raw}
            </p>
          </section>
        )}
        {intel?.metar_decoded && (
          <section>
            <h3 className="text-xs uppercase text-slate-500 mb-2">Explanation</h3>
            <ul className="space-y-2 text-sm text-slate-300">
              {intel.metar_decoded.explanations.map((line, i) => (
                <li key={i} className="flex gap-2">
                  <span className="text-sky-500 shrink-0">•</span>
                  <span>{line}</span>
                </li>
              ))}
            </ul>
          </section>
        )}
        {!intel && (
          <p className="text-sm text-slate-500">No live METAR available for this station.</p>
        )}
      </div>
    </>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-2 rounded bg-sky-950/60 border border-sky-800/80">
      <p className="text-[10px] uppercase text-slate-500">{label}</p>
      <p className="font-mono text-slate-200">{value}</p>
    </div>
  );
}
