#!/usr/bin/env python3
"""
Lee y escribe PROOF.md, el cuaderno de obra del proyecto.

Por que existe: es la unica pieza que conoce el formato del archivo. Si el
formato cambia, cambia aca y en ningun otro lado. Los hooks nunca parsean
markdown a mano.

El archivo tiene que ser legible por una persona (lo abre Tincho, lo ve un
cliente en un diff de git) y parseable por una maquina. Por eso markdown con
secciones fijas y no JSON.
"""

import os
import re

SECCIONES = [
    ("bloqueante", "## 🔴 BLOQUEANTE"),
    ("abierto", "## ⬜ ABIERTO"),
    ("sin_probar", "## ⚠️ HECHO SIN PROBAR"),
    ("postergado", "## ⏸️ POSTERGADO"),
]

PLANTILLA = """# PROOF

Cuaderno de obra. Lo vivo arriba, lo probado plegado abajo.
Generado y mantenido por proof-first.

## 🔴 BLOQUEANTE

## ⬜ ABIERTO

## ⚠️ HECHO SIN PROBAR

## ⏸️ POSTERGADO

<details>
<summary>▸ PROBADO (0)</summary>

</details>
"""

# Un acta ocupa tres lineas. Se parsea con estas dos expresiones.
_RE_ACTA = re.compile(r"^✅ (?P<fecha>[^ ]+) · (?P<que>.+?) · nivel (?P<nivel>\d+)$")
_RE_CUBRE = re.compile(r"^\s+cubre: (?P<cubre>.*?) · huella: (?P<huella>\S*)$")


def _vacio():
    return {"bloqueante": [], "abierto": [], "sin_probar": [], "postergado": [], "actas": []}


def leer(ruta):
    """Devuelve el estado del cuaderno. Si no existe, la estructura vacia."""
    if not os.path.exists(ruta):
        return _vacio()

    datos = _vacio()
    seccion = None
    acta_parcial = None

    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            linea = linea.rstrip("\n")

            titulo = next((k for k, t in SECCIONES if linea.strip() == t), None)
            if titulo:
                seccion = titulo
                continue
            if linea.startswith("<summary>") or linea.startswith("## "):
                seccion = None

            if seccion and linea.startswith("- "):
                datos[seccion].append(linea[2:].strip())
                continue

            m = _RE_ACTA.match(linea)
            if m:
                acta_parcial = {
                    "fecha": m.group("fecha"),
                    "que": m.group("que"),
                    "nivel": int(m.group("nivel")),
                    "prueba": "",
                    "cubre": [],
                    "huella": "",
                }
                continue

            if acta_parcial is not None:
                if linea.strip().startswith("prueba:"):
                    acta_parcial["prueba"] = linea.split("prueba:", 1)[1].strip()
                    continue
                mc = _RE_CUBRE.match(linea)
                if mc:
                    cubre_str = mc.group("cubre").strip()
                    acta_parcial["cubre"] = [c.strip() for c in cubre_str.split(",")] if cubre_str else []
                    acta_parcial["huella"] = mc.group("huella").strip()
                    datos["actas"].append(acta_parcial)
                    acta_parcial = None

    return datos


def escribir(ruta, datos):
    """Reescribe PROOF.md entero desde la estructura. Unica salida a disco."""
    partes = ["# PROOF", "",
              "Cuaderno de obra. Lo vivo arriba, lo probado plegado abajo.",
              "Generado y mantenido por proof-first.", ""]

    for clave, titulo in SECCIONES:
        partes.append(titulo)
        for item in datos[clave]:
            partes.append(f"- {item}")
        partes.append("")

    partes.append(f"<details>")
    partes.append(f"<summary>▸ PROBADO ({len(datos['actas'])})</summary>")
    partes.append("")
    for a in datos["actas"]:
        partes.append(f"✅ {a['fecha']} · {a['que']} · nivel {a['nivel']}")
        partes.append(f"   prueba: {a['prueba']}")
        partes.append(f"   cubre: {', '.join(a['cubre'])} · huella: {a['huella']}")
        partes.append("")
    partes.append("</details>")

    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(partes) + "\n")


def agregar_acta(ruta, que, nivel, prueba, cubre, huella, fecha):
    datos = leer(ruta)
    # Un acta nueva sobre lo mismo reemplaza a la anterior: el cuaderno no acumula.
    datos["actas"] = [a for a in datos["actas"] if a["que"] != que]
    datos["actas"].append({"fecha": fecha, "que": que, "nivel": nivel,
                           "prueba": prueba, "cubre": cubre, "huella": huella})
    # Si estaba como deuda, deja de estarlo.
    datos["sin_probar"] = [d for d in datos["sin_probar"] if not d.startswith(f"{que} — ")]
    escribir(ruta, datos)


def agregar_deuda(ruta, que, motivo, quien, fecha):
    datos = leer(ruta)
    entrada = f"{que} — {motivo} — deuda asumida por {quien} {fecha}"
    datos["sin_probar"] = [d for d in datos["sin_probar"] if not d.startswith(f"{que} — ")]
    datos["sin_probar"].append(entrada)
    escribir(ruta, datos)


def _autotest():
    import tempfile, os
    d = tempfile.mkdtemp()
    ruta = os.path.join(d, "PROOF.md")

    # archivo inexistente devuelve estructura vacia
    vacio = leer(ruta)
    assert vacio["actas"] == [], vacio
    assert vacio["bloqueante"] == [], vacio

    # un acta ida y vuelta conserva todos sus campos
    agregar_acta(ruta, que="Login con Google", nivel=5,
                 prueba="user_id 8814 en Auth0 · anonimo rechazado 401",
                 cubre=["src/auth/sesion.ts"], huella="a3f9c1", fecha="27/08")
    d1 = leer(ruta)
    assert len(d1["actas"]) == 1, d1["actas"]
    a = d1["actas"][0]
    assert a["que"] == "Login con Google", a
    assert a["nivel"] == 5, a
    assert a["cubre"] == ["src/auth/sesion.ts"], a
    assert a["huella"] == "a3f9c1", a

    # una deuda queda registrada con quien la asumio
    agregar_deuda(ruta, que="Checkout Stripe", motivo="necesita nivel 5, tiene nivel 2",
                  quien="Tincho", fecha="27/08")
    d2 = leer(ruta)
    assert len(d2["sin_probar"]) == 1, d2["sin_probar"]
    assert "Tincho" in d2["sin_probar"][0], d2["sin_probar"]
    # agregar una deuda no pisa el acta anterior
    assert len(d2["actas"]) == 1, d2["actas"]

    # una acta con cubre vacio (ej: verificar DNS) ida y vuelta se preserva
    agregar_acta(ruta, que="El DNS resuelve", nivel=5,
                 prueba="dig +short da 76.76.21.21", cubre=[], huella="000000", fecha="27/08")
    d3 = leer(ruta)
    assert len(d3["actas"]) == 2, d3["actas"]
    a_dns = [a for a in d3["actas"] if a["que"] == "El DNS resuelve"][0]
    assert a_dns["cubre"] == [], a_dns

    # deuda con prefijo comun: "Pago" y "Pago Stripe" son casos distintos
    d = tempfile.mkdtemp()
    ruta2 = os.path.join(d, "PROOF.md")
    agregar_deuda(ruta2, que="Pago", motivo="sin probar", quien="A", fecha="27/08")
    agregar_deuda(ruta2, que="Pago Stripe", motivo="sin probar", quien="B", fecha="27/08")
    d4 = leer(ruta2)
    assert len(d4["sin_probar"]) == 2, d4["sin_probar"]
    # marcar "Pago" como acta no borra "Pago Stripe"
    agregar_acta(ruta2, que="Pago", nivel=5, prueba="test", cubre=[], huella="aaa", fecha="27/08")
    d5 = leer(ruta2)
    assert len(d5["sin_probar"]) == 1, d5["sin_probar"]
    assert "Pago Stripe" in d5["sin_probar"][0], d5["sin_probar"]

    print("cuaderno.py OK")


if __name__ == "__main__":
    _autotest()
