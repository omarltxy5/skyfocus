import type { AirportIntelligence, AirportSummary } from "../types/airport";
import type { FlightDelta, FlightDetails } from "../types/flight";
import { phaseLabel } from "../utils/phaseStyle";

function categoryClass(cat: string | null | undefined): string {
  switch (cat) {
    case "VFR":
      return "cat-vfr";
    case "MVFR":
      return "cat-mvfr";
    case "IFR":
      return "cat-ifr";
    case "LIFR":
      return "cat-lifr";
    default:
      return "";
  }
}

export function metarExplainHtml(intel: AirportIntelligence | null): string {
  if (!intel?.metar_decoded) return "";
  const d = intel.metar_decoded;
  const cat = d.flight_category
    ? `<span class="metar-cat ${categoryClass(d.flight_category)}">${d.flight_category}</span>`
    : "";
  const bullets = d.explanations.map((e) => `<li>${e}</li>`).join("");
  return `<div class="metar-explainer">
    <p class="explainer-title">METAR explained ${cat}</p>
    <ul class="explainer-list">${bullets}</ul>
  </div>`;
}

export function flightPopupLoading(f: FlightDelta): string {
  return `<div class="sky-popup"><strong>${f.callsign.trim()}</strong><br/><em>Loading aircraft details…</em></div>`;
}

export function flightPopupHtml(f: FlightDelta, d: FlightDetails | null, err: string | null): string {
  const photo = d?.photo_url
    ? `<img src="${d.photo_url}" alt="Aircraft" class="popup-photo" referrerpolicy="no-referrer"/>`
    : "";
  let route = "";
  if (d?.origin_name || d?.destination_name) {
    route = `<p class="popup-route">${d.origin_name ?? "—"} → ${d.destination_name ?? "—"}</p>`;
  }
  const meta = d
    ? `<p><b>${d.airline ?? "Unknown airline"}</b></p>
       <p class="popup-muted">${d.aircraft_type ?? "Type unknown"}${d.registration ? ` · ${d.registration}` : ""}</p>
       ${route}`
    : "";
  const telem = `<p class="popup-muted">${phaseLabel(f.phase, f.go_around)} · ${Math.round(f.altitude_ft)} ft · ${Math.round(f.vertical_speed_fpm)} fpm</p>`;
  const errBlock = err ? `<p class="popup-error">${err}</p>` : "";
  return `<div class="sky-popup">${photo}<strong>${f.callsign.trim()}</strong>${meta}${telem}${errBlock}</div>`;
}

export function airportPopupHtml(
  ap: AirportSummary,
  intel: AirportIntelligence | null,
  err: string | null,
): string {
  if (err) {
    return `<div class="sky-popup"><strong>${ap.icao}</strong><br/><span>${ap.name}</span><p class="popup-error">${err}</p></div>`;
  }
  const rwy = intel?.active_runway
    ? `<p><b>Active RWY</b> ${intel.active_runway}${intel.headwind_kt != null ? ` · ${intel.headwind_kt} kt HW` : ""}</p>`
    : "";
  const metar = intel?.metar_raw ? `<p class="popup-metar-raw">${intel.metar_raw}</p>` : "";
  const explain = metarExplainHtml(intel);
  return `<div class="sky-popup airport-popup">
    <strong>${ap.icao}</strong> ${ap.iata_code ? `(${ap.iata_code})` : ""}
    <br/><span>${ap.name}</span>
    ${rwy}${metar}${explain}
  </div>`;
}
