import L from "leaflet";

/** Top-down aircraft icon; rotated by heading (0° = north). */
export function createPlaneIcon(
  headingDeg: number,
  color: string,
  goAround: boolean,
): L.DivIcon {
  const h = Number.isFinite(headingDeg) ? headingDeg : 0;
  const size = goAround ? 28 : 24;
  const html = `<div class="plane-marker" style="width:${size}px;height:${size}px;color:${color};transform:rotate(${h}deg)">
    <svg viewBox="0 0 24 24" width="${size}" height="${size}" aria-hidden="true">
      <path fill="currentColor" stroke="#0f172a" stroke-width="1.2" d="M12 2.5 L13.8 9.2 L21 10.2 L14.5 11.8 L12 21 L9.5 11.8 L3 10.2 L10.2 9.2 Z"/>
    </svg>
  </div>`;
  return L.divIcon({
    className: goAround ? "plane-icon-wrap go-around-plane" : "plane-icon-wrap",
    html,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

const PIN_SVG = encodeURIComponent(`
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 36" width="24" height="36">
  <path fill="#38bdf8" stroke="#0f172a" stroke-width="1.2" d="M12 0C7.03 0 3 4.03 3 9c0 6.75 9 15 9 15s9-8.25 9-15c0-4.97-4.03-9-9-9z"/>
  <circle cx="12" cy="9" r="3.5" fill="#e0f2fe"/>
</svg>`);

const PIN_LARGE_SVG = encodeURIComponent(`
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 36" width="28" height="42">
  <path fill="#0ea5e9" stroke="#0f172a" stroke-width="1.2" d="M12 0C7.03 0 3 4.03 3 9c0 6.75 9 15 9 15s9-8.25 9-15c0-4.97-4.03-9-9-9z"/>
  <circle cx="12" cy="9" r="3.5" fill="#e0f2fe"/>
</svg>`);

export function createAirportPinIcon(large = false): L.Icon {
  const w = large ? 28 : 24;
  const h = large ? 42 : 36;
  const svg = large ? PIN_LARGE_SVG : PIN_SVG;
  return L.icon({
    iconUrl: `data:image/svg+xml,${svg}`,
    iconSize: [w, h],
    iconAnchor: [w / 2, h],
    popupAnchor: [0, -h],
  });
}
