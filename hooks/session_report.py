#!/usr/bin/env python3
"""
Muestra el estado del cuaderno al abrir la sesion.

Por que existe: sin esto PROOF.md existe pero nadie lo abre, y la memoria entre
sesiones no sirve de nada.

Presupuesto: cinco lineas (header + cuatro items). Si hay mas items que lugar,
los ultimos cuatro estan dedicados a bloqueantes y deudas por prioridad, y si
algo queda afuera, la ultima linea dice cuantos no entraron.

Salida: JSON con systemMessage, o nada si no hay cuaderno.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))

import cuaderno  # noqa: E402
import huella  # noqa: E402

MAX_ITEMS = 4  # ponytail: changed to total budget, not per-category


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

    # Collect all items in priority order: blockers, debts, then expired line
    items = []
    for b in datos["bloqueante"]:
        items.append(f"🔴 {b}")
    for s in datos["sin_probar"]:
        items.append(f"⚠️ {s}")
    if fuera:
        nombres = ", ".join(a["que"] for a in fuera)
        items.append(f"↺ volver a probar: {nombres}")

    # Budget: 5 lines total, 1 is header, so 4 for items
    if len(items) <= MAX_ITEMS:
        # All items fit, no omission line needed
        lineas.extend(items)
    else:
        # Some items don't fit; show what fits in (MAX_ITEMS - 1) lines, then omission line
        shown = MAX_ITEMS - 1
        lineas.extend(items[:shown])
        omitted = len(items) - shown
        lineas.append(f"… y {omitted} más sin mostrar (mirá PROOF.md)")

    return "\n".join(lineas)


def main():
    # Windows usa cp1252 por defecto y no puede enviar acentos. Reconfigurar a UTF-8.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    try:
        entrada = json.load(sys.stdin)
        # Si el JSON no es un objeto (ej: array), tratar como entrada vacia.
        if not isinstance(entrada, dict):
            entrada = {}
    except (json.JSONDecodeError, ValueError):
        entrada = {}
    raiz = entrada.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()

    try:
        texto = resumen(raiz)
    except Exception:  # noqa: BLE001
        texto = None

    try:
        if texto:
            print(json.dumps({"systemMessage": texto}, ensure_ascii=False))
    except Exception:  # noqa: BLE001
        pass

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

    # 4 blockers and 4 debts: output is at most 5 lines, last line reports omitted
    d2 = tempfile.mkdtemp()
    proof2 = os.path.join(d2, "PROOF.md")
    datos2 = cuaderno.leer(proof2)
    for i in range(1, 5):
        datos2["bloqueante"].append(f"Bloqueante {i}")
    for i in range(1, 5):
        datos2["sin_probar"].append(f"Deuda {i} — sin nivel 5 — deuda asumida por T 27/08")
    cuaderno.escribir(proof2, datos2)
    r4 = resumen(d2)
    lines4 = r4.split("\n")
    assert len(lines4) <= 5, f"Expected at most 5 lines, got {len(lines4)}: {r4}"
    assert "más sin mostrar" in lines4[-1], f"Last line should report omitted items: {r4}"

    # Exactly 4 items (3 blockers + 1 expired): no omission line needed
    d3 = tempfile.mkdtemp()
    proof3 = os.path.join(d3, "PROOF.md")
    open(os.path.join(d3, "b.py"), "w").write("y=1\n")
    h3 = huella.calcular(["b.py"], d3)
    cuaderno.agregar_acta(proof3, que="Test", nivel=5, prueba="test ok",
                          cubre=["b.py"], huella=h3, fecha="27/08")
    # Change file to create an expired acta
    open(os.path.join(d3, "b.py"), "w").write("y=2\n")
    datos3 = cuaderno.leer(proof3)
    datos3["bloqueante"].append("Block 1")
    datos3["bloqueante"].append("Block 2")
    datos3["bloqueante"].append("Block 3")
    cuaderno.escribir(proof3, datos3)
    r5 = resumen(d3)
    lines5 = r5.split("\n")
    # Should have: header + 3 blockers + 1 expired line = 5 lines, no omission
    assert len(lines5) == 5, f"Expected 5 lines, got {len(lines5)}: {r5}"
    assert "más sin mostrar" not in r5, f"Should not have omission line: {r5}"
    assert "↺" in r5, f"Should have expired line: {r5}"

    print("session_report.py OK")


if __name__ == "__main__":
    import sys
    if "--autotest" in sys.argv:
        _autotest()
    else:
        main()
