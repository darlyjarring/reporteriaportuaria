
#!/usr/bin/env python3
"""
Obtiene los itinerarios directamente del servicio de DP World Posorja.
Convierte la respuesta XML en datos.json para el tablero de tráfico de naves.
"""

import json
import re
import requests
import xml.etree.ElementTree as ET

from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

URL = "https://dponline.dpworldposorja.ec/ItinerarioNaves/data"
OUT = Path("datos.json")
ECUADOR = ZoneInfo("America/Guayaquil")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
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
        # Permite trabajar incluso si el XML contiene namespaces.
        tag = child.tag.split("}")[-1]
        if tag == field:
            return clean(child.text)
    return ""

def obtener_naves():
    response = requests.get(
        URL,
        headers=HEADERS,
        timeout=60
    )
    response.raise_for_status()

    # Verificar que la respuesta sea XML válido.
    try:
        root = ET.fromstring(response.content)
    except ET.ParseError as error:
        raise RuntimeError(
            f"DP World no devolvió un XML válido: {error}"
        )

    elementos = [
        elemento for elemento in root.iter()
        if elemento.tag.split("}")[-1] == "vessel"
    ]

    if not elementos:
        raise RuntimeError(
            "La respuesta XML no contiene registros vessel. "
            "No se actualizará datos.json."
        )

    naves = []

    for vessel in elementos:

        status = get_value(vessel, "status")

        # Se conserva la estructura de datos que utiliza el tablero.
        nave = {
            "gkey": get_value(vessel, "gkey"),
            "referencia": get_value(vessel, "referencia"),
            "nave": get_value(vessel, "vesselName"),
            "viaje": get_value(vessel, "nroViaje"),
            "viaje_salida": get_value(vessel, "nroViajeSalida"),
            "reefer": clean_date(
                get_value(vessel, "reeferCutOff")
            ),
            "dry": clean_date(
                get_value(vessel, "dryCutOff")
            ),
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

    now_utc = datetime.now(timezone.utc)
    now_ec = now_utc.astimezone(ECUADOR)

    print("Consultando itinerarios de DP World Posorja...")

    naves = obtener_naves()

    # Validación para evitar sobrescribir datos válidos
    # con una respuesta inesperada.
    if not naves:
        raise RuntimeError("No existen naves para guardar.")

    data = {
        "fuente": URL,
        "actualizado_utc": now_utc.isoformat(),
        "actualizado_ec": now_ec.strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(naves),
        "naves": naves
    }

    # Escritura temporal para proteger el archivo anterior.
    temporal = OUT.with_suffix(".tmp")

    temporal.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    temporal.replace(OUT)

    print("--------------------------------------")
    print("ACTUALIZACION EXITOSA")
    print(f"Total de naves: {len(naves)}")
    print(f"Por arribar: {sum(1 for n in naves if n['status'].upper() == 'TO ARRIVE')}")
    print(f"Trabajando: {sum(1 for n in naves if n['status'].upper() == 'IN OPERATION')}")
    print(f"Zarpadas: {sum(1 for n in naves if n['status'].upper() == 'DEPARTED')}")
    print(f"Actualización Ecuador: {data['actualizado_ec']}")
    print(f"Archivo generado: {OUT}")
    print("--------------------------------------")

if __name__ == "__main__":
    main()
