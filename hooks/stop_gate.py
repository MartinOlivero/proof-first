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


def _cubierto(nombre, datos):
    """Un archivo esta cubierto si tiene acta o si su deuda ya fue declarada."""
    for a in datos["actas"]:
        if nombre == a["que"] or nombre in a["cubre"]:
            return True
    for d in datos["sin_probar"]:
        if nombre in d:
            return True
    for p in datos["postergado"]:
        if nombre in p:
            return True
    return False


def decidir(raiz):
    proof = os.path.join(raiz, "PROOF.md")
    datos = cuaderno.leer(proof)

    # 1. Un bloqueante abierto frena todo, haya o no cambios.
    if datos["bloqueante"]:
        lista = "\n".join(f"  · {b}" for b in datos["bloqueante"])
        return {"decision": "block", "reason":
                f"Hay algo bloqueante sin resolver en PROOF.md:\n{lista}\n\n"
                "Resolvelo con el usuario antes de cerrar, o movelo a POSTERGADO "
                "dejando escrito quien lo decidio."}

    cambiados = deteccion.cambios_sin_commitear(raiz)
    if cambiados is None:
        # Sin git no se puede saber que se toco. Degradacion: nunca bloquea.
        return {"decision": "approve"}

    # 2. Actas vencidas por cambios en los archivos que cubrian.
    afectadas = [a for a in huella.vencidas(datos["actas"], raiz)
                 if any(c in cambiados for c in a["cubre"])]
    if afectadas:
        lista = "\n".join(f"  · {a['que']} (cubria {', '.join(a['cubre'])})" for a in afectadas)
        return {"decision": "block", "reason":
                f"Estas actas quedaron vencidas porque cambiaron los archivos que "
                f"cubrian:\n{lista}\n\n"
                "Volve a verificarlas con el subagente `witness` y actualiza el acta, "
                "o declara la deuda en PROOF.md con quien lo decidio."}

    # 3. Categorias caras tocadas sin acta ni deuda declarada.
    caras = deteccion.clasificar(cambiados)
    pendientes = {}
    for clave, archivos in caras.items():
        sueltos = [f for f in archivos if not _cubierto(f, datos)]
        if sueltos:
            pendientes[clave] = sueltos

    if pendientes:
        detalle = []
        for clave, archivos in pendientes.items():
            cat = deteccion.CATEGORIAS[clave]
            detalle.append(f"  · {cat['nombre']} (nivel {cat['nivel']}): "
                           f"{', '.join(archivos)}")
        return {"decision": "block", "reason":
                "Se toco codigo caro sin evidencia observable desde afuera:\n"
                + "\n".join(detalle) + "\n\n"
                "Nivel 5 significa que un tercero sin interes lo confirma: el cargo en "
                "el panel del proveedor, el mail que llego de verdad, el 401 sin token. "
                "Un test propio no alcanza.\n\n"
                "Opciones:\n"
                "1. Lanza el subagente `witness` para conseguir la prueba y escribir el "
                "acta en PROOF.md.\n"
                "2. Si el usuario decide seguir sin probar, registra la deuda en PROOF.md "
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

    print("stop_gate.py OK")


if __name__ == "__main__":
    import sys
    if "--autotest" in sys.argv:
        _autotest()
    else:
        main()
