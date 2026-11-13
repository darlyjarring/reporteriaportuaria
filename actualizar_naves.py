
#!/usr/bin/env python3

import json
import re
import requests
import xml.etree.ElementTree as ET

from datetime import datetime, timezone, timedelta
from pathlib import Path

URL = "https://dponline.dpworldposorja.ec/ItinerarioNaves/data"
OUT = Path("datos.json")

ECUADOR = timezone(timedelta(hours=-5))

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/xml, text/xml, */*",
    "Accept-Language": "es-EC,es;q=0.9,en;q=0.8",
    "Referer": "https://dponline.dpworldposorja.ec/ItinerarioNaves"
}

def clean(value):
    if value is None:
        return ""
    value = str(value).replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value).strip()
    if value.lower() in {"null", "none", "-"}:
        return ""
    return value

def clean_date(value):
    value = clean(value)
    return re.sub(r"\.0+$", "", value)

def get_value(element, field):
    for child in element:
        tag = child.tag.split("}")[-1]
        if tag == field:
            return clean(child.text)
    return ""

def obtener_naves():

    print("Conectando con DP World Posorja...")

    response = requests.get(
        URL,
        headers=HEADERS,
        timeout=60
    )

    response.raise_for_status()

    print("Respuesta recibida:", response.status_code)

    try:
        root = ET.fromstring(response.content)
    except ET.ParseError as error:
        raise RuntimeError(f"Error interpretando XML: {error}")

    elementos = [
        elemento for elemento in root.iter()
        if elemento.tag.split("}")[-1] == "vessel"
    ]

    if not elementos:
        raise RuntimeError("El XML no contiene registros de naves.")

    naves = []

    for vessel in elementos:

        status = get_value(vessel, "status")

        nave = {
            "gkey": get_value(vessel, "gkey"),
            "referencia": get_value(vessel, "referencia"),
            "nave": get_value(vessel, "vesselName"),
            "viaje": get_value(vessel, "nroViaje"),
            "viaje_salida": get_value(vessel, "nroViajeSalida"),
            "reefer": clean_date(get_value(vessel, "reeferCutOff")),
            "dry": clean_date(get_value(vessel, "dryCutOff")),
            "linea": get_value(vessel, "lineId"),
            "etb": clean_date(get_value(vessel, "etb")),
            "etd": clean_date(get_value(vessel, "etd")),
            "ata": clean_date(get_value(vessel, "ata")),
            "atd": clean_date(get_value(vessel, "atd")),
            "status": status,
            "origen": get_value(vessel, "puertoOrigenId"),
            "destino": get_value(vessel, "puertoDestinoId"),
            "servicio": get_value(vessel, "servicioId")
        }

        naves.append(nave)

    return naves

def main():

    print("Iniciando actualización...")

    naves = obtener_naves()

    now_utc = datetime.now(timezone.utc)
    now_ec = now_utc.astimezone(ECUADOR)

    data = {
        "fuente": URL,
        "actualizado_utc": now_utc.isoformat(),
        "actualizado_ec": now_ec.strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(naves),
        "naves": naves
    }

    temporal = OUT.with_suffix(".tmp")

    temporal.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    temporal.replace(OUT)

    print("--------------------------------")
    print("ACTUALIZACION EXITOSA")
    print("Total naves:", len(naves))
    print("Por arribar:", sum(n["status"].upper() == "TO ARRIVE" for n in naves))
    print("Trabajando:", sum(n["status"].upper() == "IN OPERATION" for n in naves))
    print("Zarpadas:", sum(n["status"].upper() == "DEPARTED" for n in naves))
    print("Hora Ecuador:", data["actualizado_ec"])
    print("Archivo:", OUT)
    print("--------------------------------")

if __name__ == "__main__":
    main()
