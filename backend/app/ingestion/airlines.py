"""Map flight callsign prefixes to airline names."""

from __future__ import annotations

# Common ICAO airline telephony prefixes (3-letter)
_AIRLINE_PREFIXES: dict[str, str] = {
    "AAL": "American Airlines",
    "UAL": "United Airlines",
    "DAL": "Delta Air Lines",
    "SWA": "Southwest Airlines",
    "BAW": "British Airways",
    "VIR": "Virgin Atlantic",
    "AFR": "Air France",
    "DLH": "Lufthansa",
    "KLM": "KLM",
    "ITY": "ITA Airways",
    "RYR": "Ryanair",
    "EZY": "easyJet",
    "UAE": "Emirates",
    "QTR": "Qatar Airways",
    "SIA": "Singapore Airlines",
    "CPA": "Cathay Pacific",
    "ANA": "All Nippon Airways",
    "JAL": "Japan Airlines",
    "QFA": "Qantas",
    "ACA": "Air Canada",
    "WJA": "WestJet",
    "LAN": "LATAM",
    "AVA": "Avianca",
    "ETH": "Ethiopian Airlines",
    "SAA": "South African Airways",
    "ELY": "El Al",
    "THY": "Turkish Airlines",
    "SAS": "Scandinavian Airlines",
    "IBE": "Iberia",
    "TAP": "TAP Air Portugal",
    "SWR": "Swiss",
    "AUA": "Austrian Airlines",
    "CSN": "China Southern",
    "CES": "China Eastern",
    "CCA": "Air China",
    "HVN": "Vietnam Airlines",
    "KAL": "Korean Air",
    "ASA": "Alaska Airlines",
    "FFT": "Frontier Airlines",
    "NKS": "Spirit Airlines",
    "JBU": "JetBlue",
    "FDX": "FedEx",
    "UPS": "UPS Airlines",
}


def airline_from_callsign(callsign: str) -> str | None:
    cs = (callsign or "").strip().upper()
    if len(cs) < 3:
        return None
    prefix = cs[:3]
    if prefix in _AIRLINE_PREFIXES:
        return _AIRLINE_PREFIXES[prefix]
    # Numeric-heavy callsigns are often commercial flights — show prefix
    if cs.isalnum() and not cs.isdigit():
        return prefix
    return None
