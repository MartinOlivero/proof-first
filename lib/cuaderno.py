#!/usr/bin/env python3
"""
Lee y escribe PROOF.md, el cuaderno de obra del proyecto.

Por que existe: es la unica pieza que conoce el formato del archivo. Si el
formato cambia, cambia aca y en ningun otro lado. Los hooks nunca parsean
markdown a mano.

El archivo tiene que ser legible por una persona (lo abre Tincho, lo ve un
cliente en un diff de git) y parseable por una maquina. Por eso markdown con
secciones fijas y no JSON.

Tambien es la puerta de entrada por linea de comandos: el testigo no tiene
permiso de Write, asi que la unica forma que tiene de labrar un acta es
correr este archivo. Ver `agents/witness.md`.
"""

import os
import re

SECCIONES = [
    ("bloqueante", "## 🔴 BLOQUEANTE"),
    ("abierto", "## ⬜ ABIERTO"),
    ("sin_probar", "## ⚠️ HECHO SIN PROBAR"),
    ("postergado", "## ⏸️ POSTERGADO"),
]

# Un acta ocupa tres lineas. Se parsea con estas dos expresiones.
_RE_ACTA = re.compile(r"^✅ (?P<fecha>[^ ]+) · (?P<que>.+?) · nivel (?P<nivel>\d+)$")
_RE_CUBRE = re.compile(r"^\s+cubre: (?P<cubre>.*?) · huella: (?P<huella>\S*)$")

# Caracteres que convierten una entrada de `cubre` en un patron y no en un archivo.
_COMODINES = "*?["

# Extensiones que delatan que un texto es una ruta de archivo y no el nombre de
# una afirmacion. No pretende ser exhaustiva: cubre lo que se ve en la practica.
_EXTENSIONES = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".py", ".sql", ".go", ".rb",
                ".php", ".java", ".rs", ".css", ".scss", ".html", ".json", ".yml",
                ".yaml", ".sh", ".tf", ".prisma")


def _parece_ruta(texto):
    t = texto.strip()
    return "/" in t or "\\" in t or t.lower().endswith(_EXTENSIONES)


def _validar_texto(campo, valor):
    """
    Ningun campo libre puede traer un salto de linea.

    Por que: el acta ocupa tres lineas con un orden fijo. Un `\n` en medio de
    `prueba` escribe una cuarta linea que el parser puede leer como el `cubre`
    del acta, y el acta termina cubriendo otra cosa que la que se probo.
    """
    if "\n" in valor or "\r" in valor:
        raise ValueError(
            f"{campo}: no puede tener saltos de línea. El acta se escribe en "
            "líneas fijas y un salto la parte en dos; poné el texto en una sola línea.")


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


def _validar_cubre(raiz, cubre):
    """
    Cada entrada de `cubre` tiene que ser un archivo real.

    Por que corta fuerte: la huella de un glob o de un directorio no se puede
    calcular, cae al valor constante `<ausente>` y el acta queda certificando
    para siempre. Un acta que nunca vence es exactamente la falsa prueba que
    este plugin existe para atrapar, y falla en silencio. Mejor ruidoso.
    """
    for entrada in cubre:
        if os.path.isabs(entrada):
            raise ValueError(
                f"cubre: «{entrada}» es una ruta absoluta. Las entradas van "
                "relativas a la raíz del proyecto, que es donde vive PROOF.md.")
        if any(c in entrada for c in _COMODINES):
            raise ValueError(
                f"cubre: «{entrada}» tiene un comodín. Un acta con glob nunca "
                "vencería: poné los archivos uno por uno.")
        completa = os.path.join(raiz, entrada)
        adentro = os.path.relpath(os.path.realpath(completa), os.path.realpath(raiz))
        if adentro == os.pardir or adentro.startswith(os.pardir + os.sep):
            raise ValueError(
                f"cubre: «{entrada}» sale de la raíz del proyecto. Un acta solo "
                "puede cubrir archivos del proyecto que certifica.")
        if os.path.isdir(completa):
            raise ValueError(
                f"cubre: «{entrada}» es un directorio. Un acta sobre un directorio "
                "nunca vencería: poné los archivos uno por uno.")
        if not os.path.isfile(completa):
            raise ValueError(
                f"cubre: «{entrada}» no existe (buscado en {raiz}). Un acta sobre "
                "una ruta inexistente nunca vencería: revisá la ruta, que va "
                "relativa a la raíz del proyecto.")


def agregar_acta(ruta, que, nivel, prueba, cubre, huella, fecha):
    _validar_texto("que", que)
    _validar_texto("prueba", prueba)
    # Un acta sin `cubre` no vence nunca —legitimo cuando la prueba no cuelga de
    # ningun archivo (el DNS resuelve)—, pero si ademas el `que` es una ruta,
    # queda certificando ese archivo para siempre y sin huella detras. Es el
    # agujero que las huellas existen para tapar, entrando por la puerta.
    if not cubre and _parece_ruta(que):
        raise ValueError(
            f"«{que}» parece una ruta de archivo y el acta no cubre ningún archivo. "
            "Un acta así nunca vencería: pasá los archivos en --cubre, o nombrá la "
            "afirmación en términos humanos (\"El login rechaza sin token\").")
    _validar_cubre(os.path.dirname(os.path.abspath(ruta)), cubre)
    datos = leer(ruta)
    # Un acta nueva sobre lo mismo reemplaza a la anterior: el cuaderno no acumula.
    datos["actas"] = [a for a in datos["actas"] if a["que"] != que]
    datos["actas"].append({"fecha": fecha, "que": que, "nivel": nivel,
                           "prueba": prueba, "cubre": cubre, "huella": huella})
    # Si estaba como deuda, deja de estarlo.
    datos["sin_probar"] = [d for d in datos["sin_probar"] if not d.startswith(f"{que} — ")]
    escribir(ruta, datos)


def agregar_deuda(ruta, que, motivo, quien, fecha):
    _validar_texto("que", que)
    _validar_texto("motivo", motivo)
    # quien va en la misma linea que el resto: un salto forja una linea entera
    _validar_texto("quien", quien)
    datos = leer(ruta)
    entrada = f"{que} — {motivo} — deuda asumida por {quien} {fecha}"
    datos["sin_probar"] = [d for d in datos["sin_probar"] if not d.startswith(f"{que} — ")]
    datos["sin_probar"].append(entrada)
    escribir(ruta, datos)


# Marca con la que el agente firma una deuda cuando la persona no esta para
# decidir ("segui vos, mañana lo veo"). El parte de arranque las cuenta aparte.
A_CONFIRMAR = "a confirmar por"


def confirmar_deuda(ruta, que, quien, fecha):
    """
    La persona vuelve y hace suya una deuda que el agente dejo "a confirmar".

    Por que existe: sin esto la deuda queda para siempre a nombre del agente,
    que es el que no puede asumirla. Devuelve False si no habia tal deuda.
    """
    _validar_texto("quien", quien)
    datos = leer(ruta)
    for i, d in enumerate(datos["sin_probar"]):
        if d.startswith(f"{que} — ") and A_CONFIRMAR in d:
            # "…asumida por Claude (a confirmar por Martin) 04/10" -> "…confirmada por Martin 05/10"
            cuerpo = d.rsplit(" — deuda asumida por ", 1)[0]
            datos["sin_probar"][i] = f"{cuerpo} — deuda confirmada por {quien} {fecha}"
            escribir(ruta, datos)
            return True
    return False


# ---------------------------------------------------------------- linea de comandos


def _hoy():
    import datetime
    return datetime.date.today().strftime("%d/%m")


def _cli(argv):
    """
    Puerta de entrada por consola. El testigo no puede escribir archivos: esto
    es lo unico que corre para dejar el acta. Por eso el path de PROOF.md se
    recibe entero, absoluto, y no se adivina desde el directorio actual.
    """
    import argparse

    p = argparse.ArgumentParser(
        prog="cuaderno.py",
        description="Lee y escribe PROOF.md, el cuaderno de obra de proof-first.")
    p.add_argument("--autotest", action="store_true",
                   help="corre los chequeos internos y sale")
    sub = p.add_subparsers(dest="comando")

    pa = sub.add_parser("acta", help="registra un acta de algo probado")
    pa.add_argument("proof", help="ruta (absoluta) a PROOF.md")
    pa.add_argument("--que", required=True, help="qué se probó")
    pa.add_argument("--nivel", required=True, type=int, help="nivel de evidencia alcanzado (0-6)")
    pa.add_argument("--prueba", required=True, help="la coordenada de la prueba, no una copia")
    pa.add_argument("--cubre", default="",
                    help="archivos separados por coma, relativos a la raíz del proyecto. "
                         "Vacío si la prueba no cuelga de ningún archivo (el acta no vence).")
    pa.add_argument("--huella", default=None,
                    help="por defecto se calcula sobre --cubre; casi nunca hace falta pasarla")
    pa.add_argument("--fecha", default=None, help="dd/mm (por defecto, hoy)")

    pd = sub.add_parser("deuda", help="registra algo hecho sin probar, con quién lo decidió")
    pd.add_argument("proof", help="ruta (absoluta) a PROOF.md")
    pd.add_argument("--que", required=True, help="qué quedó sin probar")
    pd.add_argument("--motivo", required=True, help="por qué no se probó")
    pd.add_argument("--quien", required=True, help="quién asumió la deuda")
    pd.add_argument("--fecha", default=None, help="dd/mm (por defecto, hoy)")

    pc = sub.add_parser("confirmar", help="la persona hace suya una deuda que quedó 'a confirmar'")
    pc.add_argument("proof", help="ruta (absoluta) a PROOF.md")
    pc.add_argument("--que", required=True, help="el qué de la deuda, tal cual figura")
    pc.add_argument("--quien", required=True, help="la persona que la confirma")
    pc.add_argument("--fecha", default=None, help="dd/mm (por defecto, hoy)")

    args = p.parse_args(argv)

    if args.autotest or args.comando is None:
        _autotest()
        return 0

    try:
        return _ejecutar(args)
    except ValueError as e:
        # Un cubre invalido no es un bug: es alguien pasando un glob o un
        # directorio. Se avisa en una linea, sin traceback, y no se escribe nada.
        import sys
        print(f"proof-first: {e}", file=sys.stderr)
        return 2


def _ejecutar(args):
    """Hace el trabajo de _cli una vez parseados los argumentos."""
    proof = os.path.abspath(args.proof)
    fecha = args.fecha or _hoy()

    if args.comando == "deuda":
        agregar_deuda(proof, que=args.que, motivo=args.motivo,
                      quien=args.quien, fecha=fecha)
        print(f"deuda registrada en {proof}: {args.que} — asumida por {args.quien} {fecha}")
        return 0

    if args.comando == "confirmar":
        if not confirmar_deuda(proof, que=args.que, quien=args.quien, fecha=fecha):
            raise ValueError(f"no hay ninguna deuda «{args.que}» esperando confirmación en {proof}")
        print(f"deuda confirmada en {proof}: {args.que} — por {args.quien} {fecha}")
        return 0

    cubre = [c.strip() for c in args.cubre.split(",") if c.strip()]
    huella_valor = args.huella
    if huella_valor is None:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import huella as _huella  # noqa: E402
        _validar_cubre(os.path.dirname(proof), cubre)
        huella_valor = _huella.calcular(cubre, os.path.dirname(proof))
    agregar_acta(proof, que=args.que, nivel=args.nivel, prueba=args.prueba,
                 cubre=cubre, huella=huella_valor, fecha=fecha)
    print(f"acta escrita en {proof}: {args.que} · nivel {args.nivel} · "
          f"cubre {len(cubre)} archivo(s) · huella {huella_valor}")
    return 0


def _autotest():
    import subprocess
    import sys
    import tempfile

    d = tempfile.mkdtemp()
    ruta = os.path.join(d, "PROOF.md")

    # archivo inexistente devuelve estructura vacia
    vacio = leer(ruta)
    assert vacio["actas"] == [], vacio
    assert vacio["bloqueante"] == [], vacio

    # un acta ida y vuelta conserva todos sus campos
    os.makedirs(os.path.join(d, "src", "auth"), exist_ok=True)
    open(os.path.join(d, "src", "auth", "sesion.ts"), "w").write("export const s = 1\n")
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

    # un glob en cubre se rechaza: daria un acta que no vence nunca
    try:
        agregar_acta(ruta, que="Auth entera", nivel=5, prueba="401 sin token",
                     cubre=["src/auth/*.ts"], huella="ffffff", fecha="27/08")
        raise AssertionError("un glob en cubre tenia que ser rechazado")
    except ValueError as e:
        assert "src/auth/*.ts" in str(e), e
        assert "comod" in str(e), e

    # un directorio en cubre, tambien
    try:
        agregar_acta(ruta, que="Auth entera", nivel=5, prueba="401 sin token",
                     cubre=["src/auth"], huella="ffffff", fecha="27/08")
        raise AssertionError("un directorio en cubre tenia que ser rechazado")
    except ValueError as e:
        assert "src/auth" in str(e), e
        assert "directorio" in str(e), e

    # una ruta que no existe, tambien
    try:
        agregar_acta(ruta, que="Fantasma", nivel=5, prueba="x",
                     cubre=["src/no_existe.ts"], huella="ffffff", fecha="27/08")
        raise AssertionError("una ruta inexistente tenia que ser rechazada")
    except ValueError as e:
        assert "no_existe.ts" in str(e), e

    # el acta rechazada no dejo rastro
    assert len(leer(ruta)["actas"]) == 2, leer(ruta)["actas"]

    # un `que` que es una ruta, sin cubre, seria un acta inmortal sobre ese archivo
    try:
        agregar_acta(ruta, que="src/auth/login.ts", nivel=5, prueba="confia en mi",
                     cubre=[], huella="ffffff", fecha="27/08")
        raise AssertionError("un que con forma de ruta y sin cubre tenia que ser rechazado")
    except ValueError as e:
        assert "src/auth/login.ts" in str(e), e
        assert "--cubre" in str(e), e
    # pero con cubre pasa, y un que humano sin cubre tambien
    agregar_acta(ruta, que="El DNS de la app resuelve", nivel=5, prueba="dig da 76.76.21.21",
                 cubre=[], huella="000001", fecha="27/08")

    # rutas absolutas y escapes fuera del proyecto: no
    for mala, esperado in (("/etc/hosts", "absoluta"), ("../secreto.txt", "sale de la raíz")):
        try:
            agregar_acta(ruta, que="Fuga", nivel=5, prueba="x",
                         cubre=[mala], huella="ffffff", fecha="27/08")
            raise AssertionError(f"«{mala}» tenia que ser rechazada")
        except ValueError as e:
            assert esperado in str(e), (mala, str(e))

    # un salto de linea partiria el acta en dos: se rechaza en los campos libres
    for campo, kw in (("prueba", {"prueba": "200 OK\n   cubre: otra/cosa.ts · huella: aaaaaa"}),
                      ("que", {"que": "Login\nfalso"})):
        args = {"que": "Login", "nivel": 5, "prueba": "ok", "cubre": [], "huella": "a", "fecha": "27/08"}
        args.update(kw)
        try:
            agregar_acta(ruta, **args)
            raise AssertionError(f"{campo} con salto de linea tenia que ser rechazado")
        except ValueError as e:
            assert "saltos de línea" in str(e), e
    for campo, kw in (("motivo", {"motivo": "dos\nlineas"}),
                      ("quien", {"quien": "T\n- Pago falso — deuda asumida por nadie 27/08"})):
        args = {"que": "Pago", "motivo": "sin probar", "quien": "T", "fecha": "27/08"}
        args.update(kw)
        try:
            agregar_deuda(ruta, **args)
            raise AssertionError(f"{campo} con salto de linea tenia que ser rechazado")
        except ValueError as e:
            assert "saltos de línea" in str(e), e

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

    # la CLI: es el unico camino que tiene el testigo, asi que se prueba corriendola
    d6 = tempfile.mkdtemp()
    ruta3 = os.path.join(d6, "PROOF.md")
    open(os.path.join(d6, "pago.ts"), "w").write("export const cobrar = () => {}\n")
    yo = os.path.abspath(__file__)
    # desde OTRO directorio, con ruta absoluta: asi lo corre el testigo
    r = subprocess.run([sys.executable, yo, "acta", ruta3, "--que", "El cobro cobra",
                        "--nivel", "5", "--prueba", "charge ch_3Ab · webhook 200",
                        "--cubre", "pago.ts", "--fecha", "27/08"],
                       cwd=tempfile.mkdtemp(), capture_output=True, text=True)
    assert r.returncode == 0, (r.stdout, r.stderr)
    assert "acta escrita" in r.stdout, r.stdout
    leido = leer(ruta3)
    assert len(leido["actas"]) == 1, leido["actas"]
    assert leido["actas"][0]["que"] == "El cobro cobra", leido["actas"][0]
    assert leido["actas"][0]["cubre"] == ["pago.ts"], leido["actas"][0]
    # la huella la calculo sola, y es la de huella.py sobre ese archivo
    sys.path.insert(0, os.path.dirname(yo))
    import huella as _h
    assert leido["actas"][0]["huella"] == _h.calcular(["pago.ts"], d6), leido["actas"][0]

    # la CLI tambien registra deudas
    r2 = subprocess.run([sys.executable, yo, "deuda", ruta3, "--que", "Backup",
                         "--motivo", "no hay entorno para restaurar",
                         "--quien", "Tincho", "--fecha", "27/08"],
                        cwd=tempfile.mkdtemp(), capture_output=True, text=True)
    assert r2.returncode == 0, (r2.stdout, r2.stderr)
    assert "deuda registrada" in r2.stdout, r2.stdout
    assert "Backup" in leer(ruta3)["sin_probar"][0], leer(ruta3)["sin_probar"]

    # la CLI corta con un glob, y no escribe nada
    r3 = subprocess.run([sys.executable, yo, "acta", ruta3, "--que", "Auth",
                         "--nivel", "5", "--prueba", "x", "--cubre", "src/*.ts"],
                        cwd=tempfile.mkdtemp(), capture_output=True, text=True)
    assert r3.returncode != 0, r3.stdout
    assert len(leer(ruta3)["actas"]) == 1, leer(ruta3)["actas"]

    # una deuda "a confirmar" pasa a nombre de la persona, y solo esa
    dc = tempfile.mkdtemp()
    rc = os.path.join(dc, "PROOF.md")
    agregar_deuda(rc, que="Link de agenda", motivo="falta una reserva real",
                  quien="Claude (a confirmar por Martin)", fecha="04/10")
    agregar_deuda(rc, que="Checkout", motivo="nivel 2", quien="Martin", fecha="04/10")
    assert confirmar_deuda(rc, "Link de agenda", "Martin", "05/10")
    sp = leer(rc)["sin_probar"]
    assert sp[0] == "Link de agenda — falta una reserva real — deuda confirmada por Martin 05/10", sp
    assert A_CONFIRMAR not in sp[0] and len(sp) == 2, sp
    # lo que ya estaba a nombre de una persona no se toca, y lo inexistente tampoco
    assert not confirmar_deuda(rc, "Checkout", "Martin", "05/10")
    assert not confirmar_deuda(rc, "No existe", "Martin", "05/10")

    print("cuaderno.py OK")


if __name__ == "__main__":
    import sys
    raise SystemExit(_cli(sys.argv[1:]))
