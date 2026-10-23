#!/usr/bin/env python3
"""
Muestra el estado del cuaderno al abrir la sesion.

Por que existe: sin esto PROOF.md existe pero nadie lo abre, y la memoria entre
sesiones no sirve de nada.

Presupuesto: cinco lineas (header + cuatro items). Si hay mas items que lugar,
los ultimos cuatro estan dedicados a bloqueantes y deudas por prioridad, y si
algo queda afuera, la ultima linea dice cuantos no entraron.

Cinco lineas de verdad, no cinco items: cada uno se recorta a ANCHO caracteres.
Un item de 400 caracteres son doce lineas envueltas en una terminal comun, y el
presupuesto seria una promesa falsa. El detalle completo esta en PROOF.md.

Salida: JSON con systemMessage, o nada si no hay cuaderno.
"""

import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))

import cuaderno  # noqa: E402
import deteccion  # noqa: E402
import huella  # noqa: E402

MAX_ITEMS = 4  # ponytail: changed to total budget, not per-category
ANCHO = 100  # una linea de terminal comun; lo que no entra se lee en PROOF.md


def _recortar(texto):
    """Una linea es una linea: lo que no entra se corta con puntos suspensivos."""
    if len(texto) <= ANCHO:
        return texto
    return texto[:ANCHO - 1].rstrip() + "…"


def _fecha_vencimiento(acta, raiz):
    """
    Cuando dejo de valer un acta: el ultimo cambio de los archivos que cubria.

    No hay un registro del momento exacto, pero el mtime del archivo que la
    invalido es esa fecha. Si no se puede leer, se omite: mejor sin fecha que
    con una inventada.
    """
    marcas = []
    for rel in acta.get("cubre", []):
        try:
            marcas.append(os.path.getmtime(os.path.join(raiz, rel)))
        except OSError:
            continue
    if not marcas:
        return None
    return datetime.date.fromtimestamp(max(marcas)).strftime("%d/%m")


_RE_FECHA = re.compile(r"\b(\d{1,2})/(\d{1,2})\b")


def _dias(item, hoy):
    """
    Hace cuantos dias se anoto un item, segun la ultima fecha dd/mm que trae.

    ponytail: el cuaderno no guarda el año; una fecha "futura" se toma como del
    año pasado. Si algun dia hay deudas de mas de un año, guardar el año.
    """
    fechas = _RE_FECHA.findall(item)
    if not fechas:
        return None
    dia, mes = int(fechas[-1][0]), int(fechas[-1][1])
    try:
        f = datetime.date(hoy.year, mes, dia)
        if f > hoy:
            f = f.replace(year=hoy.year - 1)
    except ValueError:
        return None
    return (hoy - f).days


def _te_esperan(datos, hoy):
    """
    Una linea con lo que quedo esperando a la persona, o None.

    Por que existe: en el primer mes de uso el agente trabajo de noche con la
    consigna "segui vos, mañana lo veo" y dejo seis deudas "a confirmar por
    Martin"; otro proyecto junto cuatro postergados durante tres semanas. El
    cuaderno las guardaba bien y nadie se entero: lo postergado ni se mostraba.
    """
    a_confirmar = [s for s in datos["sin_probar"] if cuaderno.A_CONFIRMAR in s]
    postergado = datos["postergado"]
    sin_prueba = [a for a in datos["abierto"] if cuaderno.SIN_PRUEBA in a]
    if not a_confirmar and not postergado and not sin_prueba:
        return None
    partes = []
    if sin_prueba:
        # Primero: es lo unico que ni siquiera tiene a alguien que lo haya decidido.
        n = len(sin_prueba)
        partes.append(f"{n} cerrado{'s' if n != 1 else ''} sin prueba")
    if a_confirmar:
        n = len(a_confirmar)
        partes.append(f"{n} deuda{'s' if n != 1 else ''} a confirmar")
    if postergado:
        n = len(postergado)
        partes.append(f"{n} postergado{'s' if n != 1 else ''}")
    dias = [d for d in (_dias(i, hoy) for i in sin_prueba + a_confirmar + postergado) if d]
    if dias:
        viejo = max(dias)
        partes.append(f"lo más viejo, de hace {viejo} día{'s' if viejo != 1 else ''}")
    return "⏳ te esperan: " + " · ".join(partes) + " → /proof deuda"


def resumen(raiz, hoy=None):
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
    espera = _te_esperan(datos, hoy or datetime.date.today())
    if espera:
        # Va primero: es lo unico de la lista que solo puede resolver la persona.
        items.append(espera)
    for b in datos["bloqueante"]:
        items.append(f"🔴 {b}")
    for s in datos["sin_probar"]:
        items.append(f"⚠️ {s}")
    # Lo abierto va despues de las deudas: si nadie lo lee aca, no lo lee nadie.
    for ab in datos["abierto"]:
        items.append(f"⬜ {ab}")
    if fuera:
        nombres = []
        for a in fuera:
            cuando = _fecha_vencimiento(a, raiz)
            nombres.append(f"{a['que']} (venció el {cuando})" if cuando else a["que"])
        items.append(f"↺ volver a probar: {', '.join(nombres)}")

    items = [_recortar(i) for i in items]

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
        # El punto de partida del primer turno: lo que se commitee desde aca
        # lo ve el hook Stop aunque ya no figure en git status.
        deteccion.guardar_marca(raiz, entrada.get("session_id"))
    except Exception:  # noqa: BLE001
        pass

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

    # si el archivo cambia, la reporta vencida y con la fecha en que dejo de valer
    open(os.path.join(d, "a.py"), "w").write("x=2\n")
    r2 = resumen(d)
    assert "1 vencida" in r2, r2
    import datetime as _dt
    assert f"venció el {_dt.date.today().strftime('%d/%m')}" in r2, r2

    # lo que esta en ABIERTO tambien se ve: si no se muestra aca, no lo lee nadie
    datos_ab = cuaderno.leer(proof)
    datos_ab["abierto"].append("Recuperar contraseña")
    cuaderno.escribir(proof, datos_ab)
    r_ab = resumen(d)
    assert "⬜" in r_ab and "Recuperar contraseña" in r_ab, r_ab

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

    # un item larguisimo no puede romper el presupuesto: 5 lineas, y cortas
    d4 = tempfile.mkdtemp()
    proof4 = os.path.join(d4, "PROOF.md")
    datos4 = cuaderno.leer(proof4)
    datos4["abierto"].append("x" * 400)
    datos4["bloqueante"].append("y" * 400)
    cuaderno.escribir(proof4, datos4)
    r6 = resumen(d4)
    lineas6 = r6.split("\n")
    assert len(lineas6) <= 5, lineas6
    assert all(len(l) <= ANCHO for l in lineas6), [len(l) for l in lineas6]
    assert lineas6[1].endswith("…"), lineas6[1]

    # lo que espera a la persona va en la primera linea, con su antiguedad
    d5 = tempfile.mkdtemp()
    proof5 = os.path.join(d5, "PROOF.md")
    cuaderno.agregar_deuda(proof5, que="Link de agenda", motivo="falta una reserva real",
                           quien="Claude (a confirmar por Martin)", fecha="04/10")
    cuaderno.agregar_deuda(proof5, que="Checkout", motivo="nivel 2", quien="Martin", fecha="04/10")
    datos5 = cuaderno.leer(proof5)
    datos5["postergado"].append("Probar el checkout en producción. Lo decidió Martín el 10/09")
    datos5["bloqueante"].append("Falta decidir el borrado")
    cuaderno.escribir(proof5, datos5)
    r7 = resumen(d5, hoy=_dt.date(2026, 10, 4)).split("\n")
    assert r7[1] == ("⏳ te esperan: 1 deuda a confirmar · 1 postergado · "
                     "lo más viejo, de hace 24 días → /proof deuda"), r7[1]
    assert r7[2].startswith("🔴"), r7
    # una deuda ya a nombre de una persona no "espera" a nadie
    cuaderno.confirmar_deuda(proof5, "Link de agenda", "Martin", "05/10")
    datos5 = cuaderno.leer(proof5); datos5["postergado"] = []; cuaderno.escribir(proof5, datos5)
    assert "te esperan" not in resumen(d5), resumen(d5)
    # una fecha de diciembre leida en enero es del año pasado, no del futuro
    assert _dias("algo — deuda asumida por T 30/12", _dt.date(2027, 1, 2)) == 3

    # lo que cerro por la segunda vuelta encabeza lo que espera a la persona
    import datetime as _dt
    sp = tempfile.mkdtemp()
    cuaderno.anotar_abierto(os.path.join(sp, "PROOF.md"), que="src/pagos/webhook.ts",
                            motivo=f"se tocó cobro y {cuaderno.SIN_PRUEBA}", fecha="20/10")
    parte = resumen(sp, hoy=_dt.date(2026, 10, 23))
    assert "⏳ te esperan: 1 cerrado sin prueba · lo más viejo, de hace 3 días" in parte, parte

    print("session_report.py OK")


if __name__ == "__main__":
    import sys
    if "--autotest" in sys.argv:
        _autotest()
    else:
        main()
