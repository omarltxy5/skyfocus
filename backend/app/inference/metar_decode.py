"""
METAR decoder and plain-language explainer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.inference.metar import parse_wind

# Visibility: 10SM, 1/2SM, 9999, 0800 (meters)
_VIS_SM = re.compile(r"(?:^|\s)(?P<vis>\d+|\d+/\d+)SM(?:\s|$)")
_VIS_M = re.compile(r"(?:^|\s)(?P<vis>\d{4})(?:\s|$)")
# Cloud layers
_CLOUD = re.compile(r"(?:^|\s)(SKC|CLR|NSC|NCD|FEW|SCT|BKN|OVC|VV)(\d{3})?(?:\s|$)")
# Temp / dewpoint
_TEMP = re.compile(r"(?:^|\s)(M?\d{2})/(M?\d{2})(?:\s|$)")
# Altimeter Axxxx or Qxxxx
_ALT_A = re.compile(r"(?:^|\s)A(?P<a>\d{4})(?:\s|$)")
_ALT_Q = re.compile(r"(?:^|\s)Q(?P<q>\d{4})(?:\s|$)")
# Weather phenomena tokens (simplified set)
_WX_TOKENS = re.compile(
    r"(?<![A-Z])"
    r"(-|\+|VC)?"
    r"(MI|BC|PR|DR|BL|SH|TS|FZ)?"
    r"(DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PO|SQ|FC|SS|DS)+"
    r"(?![A-Z])",
)

_WX_MEANINGS: dict[str, str] = {
    "RA": "rain",
    "SN": "snow",
    "DZ": "drizzle",
    "TS": "thunderstorm",
    "SH": "showers",
    "FG": "fog",
    "BR": "mist",
    "HZ": "haze",
    "FU": "smoke",
    "SQ": "squalls",
    "FC": "funnel cloud / tornado",
    "VA": "volcanic ash",
    "IC": "ice crystals",
    "GR": "hail",
    "GS": "small hail",
    "BL": "blowing",
    "DR": "drifting",
    "FZ": "freezing",
}


@dataclass
class DecodedMetar:
    station: str
    observation_time: str | None = None
    wind: dict | None = None
    visibility: str | None = None
    weather: list[str] = field(default_factory=list)
    clouds: list[str] = field(default_factory=list)
    temperature_c: float | None = None
    dewpoint_c: float | None = None
    altimeter_inhg: float | None = None
    flight_category: str | None = None
    explanations: list[str] = field(default_factory=list)


def _parse_temp(token: str) -> float:
    if token.startswith("M"):
        return -float(token[1:])
    return float(token)


def _explain_wx(code: str) -> str:
    intensity = ""
    if code.startswith("+"):
        intensity = "heavy "
        code = code[1:]
    elif code.startswith("-"):
        intensity = "light "
        code = code[1:]
    elif code.startswith("VC"):
        intensity = "vicinity "
        code = code[2:]

    parts: list[str] = []
    i = 0
    while i < len(code):
        matched = False
        for key in sorted(_WX_MEANINGS, key=len, reverse=True):
            if code[i : i + len(key)] == key:
                parts.append(_WX_MEANINGS[key])
                i += len(key)
                matched = True
                break
        if not matched:
            i += 1
    if not parts:
        return code
    return intensity + " and ".join(parts)


def _ceiling_ft(clouds: list[str]) -> int | None:
    """Lowest BKN/OVC/VV layer height in feet."""
    best: int | None = None
    for c in clouds:
        if any(c.startswith(x) for x in ("BKN", "OVC", "VV")) and len(c) >= 6:
            try:
                h = int(c[3:6]) * 100
                if best is None or h < best:
                    best = h
            except ValueError:
                pass
    return best


def _flight_category(visibility_sm: float | None, ceiling_ft: int | None) -> str:
    vis = visibility_sm if visibility_sm is not None else 10.0
    ceil = ceiling_ft if ceiling_ft is not None else 100_000
    if vis < 1 or ceil < 500:
        return "LIFR"
    if vis < 3 or ceil < 1000:
        return "IFR"
    if vis <= 5 or ceil < 3000:
        return "MVFR"
    return "VFR"


def decode_metar(raw: str, station: str | None = None) -> DecodedMetar:
    text = raw.strip().upper()
    tokens = text.split()
    icao = station
    obs_time: str | None = None
    if not icao and len(tokens) >= 2:
        if tokens[0] == "METAR":
            icao = tokens[1]
            if len(tokens) > 2 and tokens[2].endswith("Z") and tokens[2][:6].isdigit():
                obs_time = tokens[2]
        elif len(tokens[0]) == 4 and tokens[0].isalpha():
            icao = tokens[0]
            if len(tokens) > 1 and tokens[1].endswith("Z"):
                obs_time = tokens[1]
    icao = (icao or "????").upper()

    wind_obj = parse_wind(text)
    wind_dict: dict | None = None
    wind_expl: str | None = None
    if wind_obj:
        wind_dict = {
            "direction_deg": wind_obj.direction_deg,
            "speed_kt": wind_obj.speed_kt,
            "gust_kt": wind_obj.gust_kt,
            "variable": wind_obj.variable,
        }
        if wind_obj.variable:
            wind_expl = f"Variable wind at {wind_obj.speed_kt:.0f} knots."
        elif wind_obj.speed_kt == 0:
            wind_expl = "Winds calm."
        else:
            gust = f", gusting {wind_obj.gust_kt:.0f} kt" if wind_obj.gust_kt else ""
            wind_expl = (
                f"Wind from {wind_obj.direction_deg:03d}° at {wind_obj.speed_kt:.0f} knots{gust}."
            )

    visibility: str | None = None
    visibility_sm: float | None = None
    m = _VIS_SM.search(text)
    if m:
        vis_raw = m.group("vis")
        if "/" in vis_raw:
            num, den = vis_raw.split("/")
            visibility_sm = int(num) / int(den)
            visibility = f"{vis_raw} statute miles"
        else:
            visibility_sm = float(vis_raw)
            visibility = f"{vis_raw} statute miles"
    else:
        m2 = _VIS_M.search(text)
        if m2 and m2.group("vis") != "9999":
            meters = int(m2.group("vis"))
            visibility_sm = meters / 1609.34
            visibility = f"{meters} m (~{visibility_sm:.1f} SM)"

    weather_codes: list[str] = []
    for tok in tokens:
        if _WX_TOKENS.fullmatch(tok) and tok not in weather_codes:
            weather_codes.append(tok)
    weather_expl = [_explain_wx(w) for w in weather_codes]

    clouds: list[str] = []
    for c in _CLOUD.findall(text):
        layer, height = c[0], c[1]
        if height:
            clouds.append(f"{layer}{height}")
        else:
            clouds.append(layer)
    cloud_expl: list[str] = []
    for c in clouds:
        if c in ("SKC", "CLR", "NSC", "NCD"):
            cloud_expl.append("Sky clear / no significant clouds.")
        elif len(c) >= 6:
            kind = {"FEW": "Few", "SCT": "Scattered", "BKN": "Broken", "OVC": "Overcast", "VV": "Vertical visibility"}.get(
                c[:3], c[:3]
            )
            ft = int(c[3:6]) * 100
            cloud_expl.append(f"{kind} clouds at {ft:,} ft.")
        else:
            cloud_expl.append(c)

    temp_c = dew_c = None
    tm = _TEMP.search(text)
    if tm:
        temp_c = _parse_temp(tm.group(1))
        dew_c = _parse_temp(tm.group(2))

    alt_inhg: float | None = None
    am = _ALT_A.search(text)
    if am:
        alt_inhg = int(am.group("a")) / 100.0
    else:
        qm = _ALT_Q.search(text)
        if qm:
            alt_inhg = int(qm.group("q")) * 0.02953  # hPa to inHg approx

    ceiling = _ceiling_ft(clouds)
    category = _flight_category(visibility_sm, ceiling)

    explanations: list[str] = []
    if obs_time:
        explanations.append(f"Observation time {obs_time} UTC.")
    if wind_expl:
        explanations.append(wind_expl)
    if visibility:
        explanations.append(f"Visibility {visibility}.")
    for w in weather_expl:
        explanations.append(f"Weather: {w.capitalize()}.")
    explanations.extend(cloud_expl)
    if temp_c is not None and dew_c is not None:
        spread = temp_c - dew_c
        explanations.append(f"Temperature {temp_c:.0f}°C, dewpoint {dew_c:.0f}°C (spread {spread:.0f}°C).")
    if alt_inhg is not None:
        explanations.append(f"Altimeter {alt_inhg:.2f} inHg.")
    explanations.append(
        f"Flight category {category}: "
        + {
            "VFR": "visual flight rules — good weather for VFR.",
            "MVFR": "marginal VFR — lowered ceilings or visibility.",
            "IFR": "instrument conditions likely required.",
            "LIFR": "low IFR — very poor ceiling/visibility.",
        }[category]
    )

    return DecodedMetar(
        station=icao,
        observation_time=obs_time,
        wind=wind_dict,
        visibility=visibility,
        weather=weather_codes,
        clouds=clouds,
        temperature_c=temp_c,
        dewpoint_c=dew_c,
        altimeter_inhg=alt_inhg,
        flight_category=category,
        explanations=explanations,
    )
