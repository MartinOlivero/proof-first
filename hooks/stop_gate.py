#!/usr/bin/env python3
"""
El control de salida: cuando el agente quiere cerrar el turno, le pide el remito.

Por que existe: la regla "no confies en el reporte, pedi el artefacto" ya esta
en SKILL.md, pero depende de que el modelo la lea y la obedezca. Este hook la
vuelve obligatoria para lo caro, y solo para lo caro.

La valvula de escape es lo que hace que se pueda usar: no se puede ESQUIVAR la
pregunta, pero si RESPONDER que se asume la deuda. Declararla alcanza para
pasar; ignorarla no. Sin esa salida el plugin es insoportable y se desinstala,
y un plugin desinstalado no protege nada.

Entrada: JSON por stdin (formato de hook Stop).
Salida: JSON con {"decision": "approve"} o {"decision": "block", "reason": ...}
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))

import cuaderno  # noqa: E402
import deteccion  # noqa: E402
import huella  # noqa: E402


def _cubierto(nombre, datos, expired_set=None):
    """Un archivo esta cubierto si tiene acta o si su deuda ya fue declarada."""
    if expired_set is None:
        expired_set = set()

    for a in datos["actas"]:
        # No contar actas expiradas como cobertura.
        if a["que"] in expired_set:
            continue
        if nombre == a["que"] or nombre in a["cubre"]:
            return True

    for d in datos["sin_probar"]:
        # Extraer el que (path) antes del primer separador " — ".
        que = d.split(" — ")[0] if " — " in d else d
        if nombre == que:
            return True

    for p in datos["postergado"]:
        # Extraer el que (path) antes del primer separador " — ".
        que = p.split(" — ")[0] if " — " in p else p
        if nombre == que:
            return True

    return False


def decidir(raiz):
    proof = os.path.join(raiz, "PROOF.md")
    datos = cuaderno.leer(proof)

    # 1. Un bloqueante abierto frena todo, haya o no cambios.
    # Esto se evalua antes del git check porque un bloqueante es una decision
    # deliberada de una persona, no una inferencia sobre lo que cambio.
    if datos["bloqueante"]:
        lista = "\n".join(f"  · {b}" for b in datos["bloqueante"])
        return {"decision": "block", "reason":
                f"Hay algo bloqueante sin resolver en PROOF.md:\n{lista}\n\n"
                "Resolvé con el usuario antes de cerrar, o movelo a POSTERGADO "
                "dejando escrito quién lo decidió."}

    cambiados = deteccion.cambios_sin_commitear(raiz)
    if cambiados is None:
        # Sin git no se puede saber que se toco. Degradacion: nunca bloquea.
        return {"decision": "approve"}

    # Computar el conjunto de actas vencidas que cubren codigo caro.
    todas_vencidas = huella.vencidas(datos["actas"], raiz)
    expired_set = set()
    for a in todas_vencidas:
        caras_cubierto = deteccion.clasificar(a["cubre"])
        if caras_cubierto:
            expired_set.add(a["que"])

    # 2. Actas vencidas que cubren codigo caro deben ser reportadas.
    # Aun si la deuda se paso a postergado (si cambio fue committeado).
    if expired_set:
        afectadas = [a for a in todas_vencidas if a["que"] in expired_set]
        lista = "\n".join(f"  · {a['que']} (cubría {', '.join(a['cubre'])})" for a in afectadas)
        return {"decision": "block", "reason":
                f"Estas actas quedaron vencidas porque cambiaron los archivos que "
                f"cubrían:\n{lista}\n\n"
                "Volvé a verificarlas con el subagente `witness` y actualiza el acta, "
                "o declara la deuda en PROOF.md con quién lo decidió."}

    # 3. Categorias caras tocadas sin acta ni deuda declarada.
    caras = deteccion.clasificar(cambiados)
    pendientes = {}
    for clave, archivos in caras.items():
        sueltos = [f for f in archivos if not _cubierto(f, datos, expired_set)]
        if sueltos:
            pendientes[clave] = sueltos

    if pendientes:
        detalle = []
        for clave, archivos in pendientes.items():
            cat = deteccion.CATEGORIAS[clave]
            detalle.append(f"  · {cat['nombre']} (nivel {cat['nivel']}): "
                           f"{', '.join(archivos)}")
        return {"decision": "block", "reason":
                "Se tocó código caro sin evidencia observable desde afuera:\n"
                + "\n".join(detalle) + "\n\n"
                "Nivel 5 significa que un tercero sin interés lo confirma: el cargo en "
                "el panel del proveedor, el mail que llegó de verdad, el 401 sin token. "
                "Un test propio no alcanza.\n\n"
                "Opciones:\n"
                "1. Lanzá el subagente `witness` para conseguir la prueba y escribir el "
                "acta en PROOF.md.\n"
                "2. Si el usuario decide seguir sin probar, registrá la deuda en PROOF.md "
                "con su nombre y la fecha. Declararla alcanza para cerrar."}

    return {"decision": "approve"}


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
        print(json.dumps(decidir(raiz), ensure_ascii=False))
    except Exception as e:  # noqa: BLE001
        # Un hook roto nunca puede trabar la sesion del usuario.
        print(json.dumps({"decision": "approve",
                          "systemMessage": f"proof-first no pudo evaluar: {e}"}))
    sys.exit(0)


def _autotest():
    import tempfile, os, subprocess, sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
    import cuaderno, huella

    d = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q"], cwd=d, check=True)
    proof = os.path.join(d, "PROOF.md")

    # sin cambios: aprueba
    assert decidir(d)["decision"] == "approve"

    # un cambio barato: aprueba
    os.makedirs(os.path.join(d, "src"), exist_ok=True)
    open(os.path.join(d, "src", "estilos.css"), "w").write("body{}\n")
    assert decidir(d)["decision"] == "approve", decidir(d)

    # un cambio caro sin acta: bloquea y nombra la categoria
    os.makedirs(os.path.join(d, "src", "auth"), exist_ok=True)
    ruta_auth = os.path.join(d, "src", "auth", "login.ts")
    open(ruta_auth, "w").write("export const login = () => {}\n")
    r = decidir(d)
    assert r["decision"] == "block", r
    assert "auth" in r["reason"].lower(), r["reason"]
    assert "nivel 5" in r["reason"], r["reason"]

    # declarar la deuda alcanza para pasar: la valvula de escape
    cuaderno.agregar_deuda(proof, que="src/auth/login.ts", motivo="sin nivel 5",
                           quien="Tincho", fecha="27/08")
    assert decidir(d)["decision"] == "approve", decidir(d)

    # un acta vigente tambien alcanza
    os.remove(proof)
    h = huella.calcular(["src/auth/login.ts"], d)
    cuaderno.agregar_acta(proof, que="src/auth/login.ts", nivel=5, prueba="401 sin token",
                          cubre=["src/auth/login.ts"], huella=h, fecha="27/08")
    assert decidir(d)["decision"] == "approve", decidir(d)

    # si el archivo cambia despues, el acta vence y vuelve a bloquear
    open(ruta_auth, "w").write("export const login = (x) => x\n")
    r2 = decidir(d)
    assert r2["decision"] == "block", r2
    assert "vencid" in r2["reason"].lower(), r2["reason"]

    # un bloqueante abierto frena aunque no haya nada caro
    d2 = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q"], cwd=d2, check=True)
    p2 = os.path.join(d2, "PROOF.md")
    datos = cuaderno.leer(p2)
    datos["bloqueante"].append("Falta decidir si el borrado es real o logico")
    cuaderno.escribir(p2, datos)
    r3 = decidir(d2)
    assert r3["decision"] == "block", r3
    assert "borrado" in r3["reason"], r3["reason"]

    # sin git no bloquea nunca: degradacion
    d3 = tempfile.mkdtemp()
    assert decidir(d3)["decision"] == "approve"

    # Fix 1: deuda declarada para path erroneo no cubre el path real (substring bug)
    d4 = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q"], cwd=d4, check=True)
    p4 = os.path.join(d4, "PROOF.md")
    # Declarar deuda para un path que CONTIENE el path real como substring
    cuaderno.agregar_deuda(p4, que="packages/legacy-vendor/src/auth/index.ts",
                           motivo="vendor legacy, no se toca", quien="Tincho", fecha="27/08")
    # Pero el cambio real es en un path diferente que es substring del declarado
    os.makedirs(os.path.join(d4, "src", "auth"), exist_ok=True)
    ruta_real = os.path.join(d4, "src", "auth", "index.ts")
    open(ruta_real, "w").write("export const auth = () => {}\n")
    r4 = decidir(d4)
    assert r4["decision"] == "block", f"Fix 1 failed: {r4}"
    assert "auth" in r4["reason"].lower(), f"Fix 1: no 'auth' in reason: {r4['reason']}"

    # Fix 1b: pero si se declara la deuda exacta, si aprueba (escape valve funciona)
    cuaderno.agregar_deuda(p4, que="src/auth/index.ts", motivo="cambio menor",
                           quien="Tincho", fecha="27/08")
    r4b = decidir(d4)
    assert r4b["decision"] == "approve", f"Fix 1b escape valve failed: {r4b}"

    # Fix 2: acta expirada no debe quedar enterrada si el cambio se comittea
    d5 = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q"], cwd=d5, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=d5, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=d5, check=True)
    p5 = os.path.join(d5, "PROOF.md")
    os.makedirs(os.path.join(d5, "src", "db"), exist_ok=True)
    # Usar archivo que matchea patron "schema" (categoria datos, nivel 5)
    ruta_schema = os.path.join(d5, "src", "db", "schema.sql")
    open(ruta_schema, "w").write("CREATE TABLE users (id INT)\n")
    # Commitear el archivo inicial primero
    subprocess.run(["git", "add", "."], cwd=d5, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=d5, check=True)
    # Crear acta para el archivo
    h5 = huella.calcular(["src/db/schema.sql"], d5)
    cuaderno.agregar_acta(p5, que="src/db/schema.sql", nivel=5, prueba="test exitoso",
                          cubre=["src/db/schema.sql"], huella=h5, fecha="27/08")
    # Cambiar el archivo
    open(ruta_schema, "w").write("CREATE TABLE users (id INT, name VARCHAR(100))\n")
    # Sin commitear, debe bloquear
    r5a = decidir(d5)
    assert r5a["decision"] == "block", f"Fix 2 pre-commit should block: {r5a}"
    assert "vencid" in r5a["reason"].lower(), f"Fix 2 pre-commit missing 'vencid': {r5a['reason']}"
    # Commitear el cambio
    subprocess.run(["git", "add", "src/db/schema.sql"], cwd=d5, check=True)
    subprocess.run(["git", "commit", "-m", "update"], cwd=d5, check=True)
    # Despues de commitear, el acta expirada SIGUE siendo bloqueante (no quedó enterrada)
    r5b = decidir(d5)
    assert r5b["decision"] == "block", f"Fix 2 post-commit should block: {r5b}"
    assert "vencid" in r5b["reason"].lower(), f"Fix 2 post-commit missing 'vencid': {r5b['reason']}"

    # Fix 3: JSON no-dict no debe crashear (debe aprobar gracefully)
    # Este test esta en el e2e, aca solo verificamos que _cubierto y decidir no lo usan

    # Ruling 1: bloqueante sin git debe bloquear (bloqueante es independiente de git)
    d6 = tempfile.mkdtemp()
    p6 = os.path.join(d6, "PROOF.md")
    datos6 = cuaderno.leer(p6)
    datos6["bloqueante"].append("Falta revisar algo")
    cuaderno.escribir(p6, datos6)
    r6 = decidir(d6)
    assert r6["decision"] == "block", f"Ruling 1 (no git + bloqueante) failed: {r6}"
    assert "algo" in r6["reason"], f"Ruling 1: no bloqueante text in reason: {r6['reason']}"

    print("stop_gate.py OK")


if __name__ == "__main__":
    import sys
    if "--autotest" in sys.argv:
        _autotest()
    else:
        main()
