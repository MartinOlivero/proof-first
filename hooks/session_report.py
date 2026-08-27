#!/usr/bin/env python3
"""
Muestra el estado del cuaderno al abrir la sesion.

Por que existe: sin esto PROOF.md existe pero nadie lo abre, y la memoria entre
sesiones no sirve de nada. Cinco lineas, no mas: si no se entiende de un
vistazo donde estas parado, fallo.

Salida: JSON con systemMessage, o nada si no hay cuaderno.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))

import cuaderno  # noqa: E402
import huella  # noqa: E402

MAX_ITEMS = 3


def resumen(raiz):
    proof = os.path.join(raiz, "PROOF.md")
    if not os.path.exists(proof):
        return None

    datos = cuaderno.leer(proof)
    fuera = huella.vencidas(datos["actas"], raiz)
    vigentes = len(datos["actas"]) - len(fuera)

    lineas = []
    cabecera = f"proof-first · {vigentes} acta{'s' if vigentes != 1 else ''} vigente{'s' if vigentes != 1 else ''}"
    if fuera:
        cabecera += f" · {len(fuera)} vencida{'s' if len(fuera) != 1 else ''}"
    lineas.append(cabecera)

    for b in datos["bloqueante"][:MAX_ITEMS]:
        lineas.append(f"🔴 {b}")
    for s in datos["sin_probar"][:MAX_ITEMS]:
        lineas.append(f"⚠️ {s}")

    if fuera:
        nombres = ", ".join(a["que"] for a in fuera[:MAX_ITEMS])
        lineas.append(f"↺ volver a probar: {nombres}")

    return "\n".join(lineas)


def main():
    # Windows usa cp1252 por defecto y no puede enviar acentos. Reconfigurar a UTF-8.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    try:
        entrada = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        entrada = {}
    raiz = entrada.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()

    try:
        texto = resumen(raiz)
    except Exception:  # noqa: BLE001
        texto = None

    if texto:
        print(json.dumps({"systemMessage": texto}, ensure_ascii=False))
    sys.exit(0)


def _autotest():
    import tempfile, os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
    import cuaderno, huella

    # sin PROOF.md no dice nada: el plugin es invisible hasta que hace falta
    d = tempfile.mkdtemp()
    assert resumen(d) is None

    # con actas vigentes, las cuenta
    proof = os.path.join(d, "PROOF.md")
    open(os.path.join(d, "a.py"), "w").write("x=1\n")
    h = huella.calcular(["a.py"], d)
    cuaderno.agregar_acta(proof, que="Login", nivel=5, prueba="401 ok",
                          cubre=["a.py"], huella=h, fecha="27/08")
    r = resumen(d)
    assert "1 acta" in r, r
    assert "vencida" not in r, r

    # si el archivo cambia, la reporta vencida
    open(os.path.join(d, "a.py"), "w").write("x=2\n")
    r2 = resumen(d)
    assert "1 vencida" in r2, r2

    # bloqueantes y deudas aparecen con su emoji
    datos = cuaderno.leer(proof)
    datos["bloqueante"].append("Falta decidir el borrado")
    datos["sin_probar"].append("Checkout — deuda asumida por Tincho 27/08")
    cuaderno.escribir(proof, datos)
    r3 = resumen(d)
    assert "🔴" in r3 and "Falta decidir el borrado" in r3, r3
    assert "⚠️" in r3 and "Checkout" in r3, r3

    print("session_report.py OK")


if __name__ == "__main__":
    import sys
    if "--autotest" in sys.argv:
        _autotest()
    else:
        main()
