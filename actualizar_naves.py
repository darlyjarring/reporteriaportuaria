#!/usr/bin/env python3
"""
Obtiene la tabla pública de itinerarios de DP World Posorja y genera datos.json.

Fuente:
https://www.dpworldposorja.com.ec/itinerarios.php

No se guarda HTML de la página: solamente los campos necesarios para el tablero.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

URL = "https://www.dpworldposorja.com.ec/itinerarios.php"
OUT = Path("datos.json")
ECUADOR = ZoneInfo("America/Guayaquil")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; DPWorldNavesBot/1.0; +https://github.com/)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-EC,es;q=0.9,en;q=0.8",
}

def clean(value):
    value = "" if value is None else str(value)
    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value).strip()
    if value.lower() in {"null", "none", "-"}:
        return ""
    return value

def clean_date(value):
    value = clean(value)
    # DP World publica "2026-09-26 23:00:00.0"
    value = re.sub(r"\.0+$", "", value)
    return value

def header_key(value):
    return clean(value).upper().replace(" ", "")

def main():
    response = requests.get(URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    target = None
    headers = None

    for table in soup.find_all("table"):
        row = table.find("tr")
        if not row:
            continue
        cells = row.find_all(["th", "td"])
        hs = [clean(c.get_text(" ", strip=True)) for c in cells]
        keys = [header_key(x) for x in hs]
        if "STATUS" in keys and "NAVE" in keys and "ETB" in keys:
            target = table
            headers = hs
            break

    if target is None:
        raise RuntimeError("No se encontró la tabla de itinerarios con las columnas esperadas.")

    index = {header_key(h): i for i, h in enumerate(headers)}

    aliases = {
        "NAVE": ["NAVE"],
        "VIAJE": ["VIAJE"],
        "REEFER CUTOFF": ["REEFERCUTOFF"],
        "DRY CUTOFF": ["DRYCUTOFF"],
        "LINEA": ["LINEA", "LÍNEA"],
        "ETB": ["ETB"],
        "ETD": ["ETD"],
        "ATA": ["ATA"],
        "ATD": ["ATD"],
        "STATUS": ["STATUS"],
        "PTO.ORIGEN": ["PTO.ORIGEN", "PTOORIGEN"],
        "PTO.DESTINO": ["PTO.DESTINO", "PTODESTINO"],
        "SERVICIO": ["SERVICIO"],
    }

    def pos(name):
        for alias in aliases[name]:
            k = header_key(alias)
            if k in index:
                return index[k]
        return None

    required = ["NAVE","VIAJE","LINEA","ETB","ETD","ATA","ATD","STATUS","PTO.ORIGEN","PTO.DESTINO","SERVICIO"]
    missing = [x for x in required if pos(x) is None]
    if missing:
        raise RuntimeError("Faltan columnas en DP World: " + ", ".join(missing))

    naves = []
    for tr in target.find_all("tr")[1:]:
        cells = tr.find_all(["td","th"])
        if len(cells) < len(headers):
            continue
        values = [clean(c.get_text(" ", strip=True)) for c in cells]
        nave = values[pos("NAVE")]
        if not nave:
            continue

        naves.append({
            "nave": nave,
            "viaje": values[pos("VIAJE")],
            "reefer": values[pos("REEFER CUTOFF")] if pos("REEFER CUTOFF") is not None else "",
            "dry": values[pos("DRY CUTOFF")] if pos("DRY CUTOFF") is not None else "",
            "linea": values[pos("LINEA")],
            "etb": clean_date(values[pos("ETB")]),
            "etd": clean_date(values[pos("ETD")]),
            "ata": clean_date(values[pos("ATA")]),
            "atd": clean_date(values[pos("ATD")]),
            "status": values[pos("STATUS")],
            "origen": values[pos("PTO.ORIGEN")],
            "destino": values[pos("PTO.DESTINO")],
            "servicio": values[pos("SERVICIO")],
        })

    now_utc = datetime.now(timezone.utc)
    now_ec = now_utc.astimezone(ECUADOR)

    data = {
        "fuente": URL,
        "actualizado_utc": now_utc.isoformat(),
        "actualizado_ec": now_ec.strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(naves),
        "naves": naves,
    }

    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: {len(naves)} naves guardadas en {OUT}")

if __name__ == "__main__":
    main()
