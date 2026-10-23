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


def _extraer_que(entrada):
    """Extrae el que (path) de una entrada sin_probar o postergado."""
    return entrada.split(" — ")[0] if " — " in entrada else entrada


def _cubierto(nombre, datos, expired_set=None):
    """Un archivo esta cubierto si tiene acta o si su deuda ya fue declarada."""
    if expired_set is None:
        expired_set = set()

    for a in datos["actas"]:
        # No contar actas expiradas como cobertura.
        if a["que"] in expired_set:
            continue
        # Solo `cubre` cubre archivos. El `que` es el nombre humano de la
        # afirmacion ("Login con Google"): si tambien contara, un acta con `que`
        # con forma de ruta y `cubre` vacio taparia ese archivo para siempre,
        # sin ninguna huella detras que la haga vencer.
        if nombre in a["cubre"]:
            return True

    for d in datos["sin_probar"]:
        que = _extraer_que(d)
        if nombre == que:
            return True

    for p in datos["postergado"]:
        que = _extraer_que(p)
        if nombre == que:
            return True

    return False


def decidir(raiz, sesion=None):
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
    # Lo que el agente commiteo durante el turno tambien es de este turno.
    cambiados = sorted(set(cambiados) | set(deteccion.commiteados_en_el_turno(raiz, sesion)))

    # Computar el conjunto de actas vencidas que cubren codigo caro.
    todas_vencidas = huella.vencidas(datos["actas"], raiz)
    expired_set = set()
    for a in todas_vencidas:
        caras_cubierto = deteccion.clasificar(a["cubre"])
        if caras_cubierto:
            expired_set.add(a["que"])

    # 2. Actas vencidas que cubren codigo caro deben ser reportadas.
    # Pero solo las que no estan ya cubiertas por una deuda declarada.
    if expired_set:
        afectadas = [a for a in todas_vencidas if a["que"] in expired_set]
        # Extraer los ques de deudas (para comparar con paths en actas)
        deudas_ques = set(_extraer_que(d) for d in datos["sin_probar"] + datos["postergado"])
        # Filtrar solo actas sin cobertura por deuda
        sin_cobertura = [a for a in afectadas
                         if a["que"] not in deudas_ques
                         and not any(c in deudas_ques for c in a["cubre"])]
        if sin_cobertura:
            lista = "\n".join(f"  · {a['que']} (cubría {', '.join(a['cubre'])})" for a in sin_cobertura)
            return {"decision": "block",
                    "_pendientes": [(a["que"], f"el acta venció (cambió {', '.join(a['cubre'])}) "
                                     f"y {cuaderno.SIN_PRUEBA}") for a in sin_cobertura],
                    "reason":
                    f"Estas actas quedaron vencidas porque cambiaron los archivos que "
                    f"cubrían:\n{lista}\n\n"
                    "Volvé a verificarlas con el subagente `witness` y actualizá el acta, "
                    "o declará la deuda en PROOF.md con quién lo decidió."}

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
        return {"decision": "block",
                "_pendientes": [(f, f"se tocó {deteccion.CATEGORIAS[c]['nombre'].lower()} "
                                 f"y {cuaderno.SIN_PRUEBA}")
                                for c, archivos in pendientes.items() for f in archivos],
                "reason":
                "Se tocó código caro sin evidencia observable desde afuera:\n"
                + "\n".join(detalle) + "\n\n"
                "Nivel 5 significa que un tercero sin interés lo confirma: el cargo en "
                "el panel del proveedor, el mail que llegó de verdad, el 401 sin token. "
                "Un test propio no alcanza.\n\n"
                "Opciones:\n"
                "1. Lanzá el subagente `witness` para conseguir la prueba y escribir el "
                "acta en PROOF.md.\n"
                "2. Si el usuario decide seguir sin probar, registrá la deuda en PROOF.md "
                "con su nombre y la fecha. Declararla alcanza para cerrar.\n"
                "3. Si el usuario no está (te dejó trabajando solo) y la prueba necesita "
                "algo que no tenés, registrá la deuda con --quien \"Claude (a confirmar "
                "por <su nombre>)\". Se le muestra al abrir la próxima sesión."}

    return {"decision": "approve"}


def segunda_vuelta(raiz, sesion=None):
    """
    Respuesta cuando este mismo hook ya bloqueo el turno y el agente volvio.

    Es la invariante absoluta del plugin: un hook no puede dejar al usuario
    encerrado. Si el agente no puede escribir PROOF.md —permisos, disco de solo
    lectura, modo plan, un usuario que dice que no— sin esta salida el turno no
    cierra nunca. Aprueba, pero deja escrito por que se aprobo.

    "Deja escrito" era un aviso en pantalla, y la pantalla no es un cuaderno: en
    el uso real del 04 al 23/10 unos quince turnos cerraron por aca —el webhook
    de cobro, migraciones, un callback de OAuth— y al dia siguiente no quedaba
    rastro. Ahora lo pendiente se anota en ABIERTO, que no cuenta como deuda
    (no destraba nada) pero aparece en el parte de la proxima sesion. Es la
    multa por pasar el control sin parar: no te frena, pero te llega a casa.
    """
    try:
        decision = decidir(raiz, sesion)
    except Exception as e:  # noqa: BLE001
        decision = {"decision": "approve", "systemMessage": f"no se pudo evaluar: {e}"}

    aviso = ("proof-first: ya frené este turno una vez y no lo vuelvo a frenar. "
             "Cierra igual, pero esto quedó sin evidencia y sin deuda declarada")
    pendiente = decision.get("reason") or decision.get("systemMessage") or ""
    # Solo el primer parrafo: es el que nombra lo que falta. El resto del motivo
    # son instrucciones para destrabar, y ya no hay nada trabado.
    pendiente = pendiente.split("\n\n")[0].strip()
    if decision.get("decision") == "block" and pendiente:
        aviso += ":\n" + pendiente
        anotados = _anotar(raiz, decision.get("_pendientes", []))
        if anotados:
            aviso += f"\n\nQuedó anotado en PROOF.md (ABIERTO, {anotados}): se muestra al abrir la próxima sesión."
    else:
        aviso += "."
    return {"decision": "approve", "systemMessage": aviso}


def _anotar(raiz, pendientes):
    """Escribe lo que paso sin probar en ABIERTO. Devuelve cuantos, 0 si no pudo."""
    if not pendientes:
        return 0
    proof = os.path.join(raiz, "PROOF.md")
    fecha = cuaderno._hoy()
    try:
        for que, motivo in pendientes:
            cuaderno.anotar_abierto(proof, que=que, motivo=motivo, fecha=fecha)
    except (OSError, ValueError):
        return 0  # disco de solo lectura, o un que con salto de linea: queda el aviso
    return len(pendientes)


def _limpiar(decision):
    """Lo que empieza con _ es para uso interno: no viaja al harness."""
    return {k: v for k, v in decision.items() if not k.startswith("_")}


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
    # cwd es lo que manda el harness; las otras dos son para correrlo a mano.
    raiz = entrada.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()

    sesion = entrada.get("session_id")

    try:
        # Anti-bucle (spec 6.3): si este hook ya bloqueo el turno, no bloquea otra vez.
        if entrada.get("stop_hook_active"):
            decision = segunda_vuelta(raiz, sesion)
        else:
            decision = decidir(raiz, sesion)
        if decision["decision"] == "approve":
            # El turno cierra: lo commiteado hasta aca ya fue juzgado. Mientras
            # bloquea, la marca no se mueve, asi un commit no borra la deuda.
            deteccion.guardar_marca(raiz, sesion)
        print(json.dumps(_limpiar(decision), ensure_ascii=False))
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
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=d, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=d, check=True)
    proof = os.path.join(d, "PROOF.md")

    # sin cambios: aprueba
    assert decidir(d)["decision"] == "approve"

    # un cambio barato: aprueba
    os.makedirs(os.path.join(d, "src"), exist_ok=True)
    open(os.path.join(d, "src", "estilos.css"), "w").write("body{}\n")
    assert decidir(d)["decision"] == "approve", decidir(d)

    # un cambio caro sin acta: bloquea y nombra la categoria.
    # Se commitea la base primero solo para ejercitar el caso mas comun (editar
    # un archivo que ya existe). Con --untracked-files=all, un archivo nuevo en
    # una carpeta nueva tambien se ve: eso lo cubre el autotest de deteccion.py.
    os.makedirs(os.path.join(d, "src", "auth"), exist_ok=True)
    ruta_auth = os.path.join(d, "src", "auth", "login.ts")
    open(ruta_auth, "w").write("export const login = () => {}\n")
    subprocess.run(["git", "add", "."], cwd=d, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=d, check=True)
    open(ruta_auth, "w").write("export const login = (u) => u\n")
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
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=d4, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=d4, check=True)
    p4 = os.path.join(d4, "PROOF.md")
    # Declarar deuda para un path que CONTIENE el path real como substring
    cuaderno.agregar_deuda(p4, que="packages/legacy-vendor/src/auth/index.ts",
                           motivo="vendor legacy, no se toca", quien="Tincho", fecha="27/08")
    # Pero el cambio real es en un path diferente que es substring del declarado
    os.makedirs(os.path.join(d4, "src", "auth"), exist_ok=True)
    ruta_real = os.path.join(d4, "src", "auth", "index.ts")
    open(ruta_real, "w").write("export const auth = () => {}\n")
    subprocess.run(["git", "add", "."], cwd=d4, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=d4, check=True)
    open(ruta_real, "w").write("export const auth = (x) => x\n")
    r4 = decidir(d4)
    assert r4["decision"] == "block", f"Fix 1 failed: {r4}"
    assert "auth" in r4["reason"].lower(), f"Fix 1: no 'auth' in reason: {r4['reason']}"

    # Fix 1b: pero si se declara la deuda exacta, si aprueba (escape valve funciona)
    cuaderno.agregar_deuda(p4, que="src/auth/index.ts", motivo="cambio menor",
                           quien="Tincho", fecha="27/08")
    r4b = decidir(d4)
    assert r4b["decision"] == "approve", f"Fix 1b escape valve failed: {r4b}"

    # Fix 2: acta expirada no debe quedar enterrada si el cambio se commitea
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
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=d5, check=True)
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
    subprocess.run(["git", "commit", "-q", "-m", "update"], cwd=d5, check=True)
    # Despues de commitear, el acta expirada SIGUE siendo bloqueante (no quedo enterrada)
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

    # Round 2 Fix: expired acta must honor declared debt (escape valve)
    # Test 1: Expired acta with no debt -> block (existing scenario, just verify)
    # (This is already tested in Fix 2 scenario above, skipping duplicate)

    # Test 2: Expired acta with debt for the acta's que -> approve
    d7 = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q"], cwd=d7, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=d7, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=d7, check=True)
    p7 = os.path.join(d7, "PROOF.md")
    os.makedirs(os.path.join(d7, "src", "db"), exist_ok=True)
    ruta_mig = os.path.join(d7, "src", "db", "migration.sql")
    open(ruta_mig, "w").write("ALTER TABLE users ADD column;\n")
    subprocess.run(["git", "add", "."], cwd=d7, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=d7, check=True)
    # Acta para el archivo
    h7 = huella.calcular(["src/db/migration.sql"], d7)
    cuaderno.agregar_acta(p7, que="src/db/migration.sql", nivel=5, prueba="tested",
                          cubre=["src/db/migration.sql"], huella=h7, fecha="27/08")
    # Cambiar y commitear
    open(ruta_mig, "w").write("ALTER TABLE users ADD column age INT;\n")
    subprocess.run(["git", "add", "src/db/migration.sql"], cwd=d7, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "update"], cwd=d7, check=True)
    # Acta should be expired, but declare debt for its que -> approve
    cuaderno.agregar_deuda(p7, que="src/db/migration.sql", motivo="revisado",
                           quien="Tincho", fecha="27/08")
    r7 = decidir(d7)
    assert r7["decision"] == "approve", f"Round 2: debt for que should approve: {r7}"

    # Test 3: Expired acta with debt for path in cubre -> approve
    d8 = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q"], cwd=d8, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=d8, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=d8, check=True)
    p8 = os.path.join(d8, "PROOF.md")
    os.makedirs(os.path.join(d8, "src", "db"), exist_ok=True)
    ruta_seed = os.path.join(d8, "src", "db", "seed.sql")
    open(ruta_seed, "w").write("INSERT INTO users VALUES (1, 'test');\n")
    # el acta de abajo cubre los dos archivos: los dos tienen que existir
    open(os.path.join(d8, "src", "db", "schema.sql"), "w").write("CREATE TABLE users (id INT)\n")
    subprocess.run(["git", "add", "."], cwd=d8, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=d8, check=True)
    # Acta que cubre dos archivos
    h8 = huella.calcular(["src/db/seed.sql", "src/db/schema.sql"], d8)
    cuaderno.agregar_acta(p8, que="src/db/setup", nivel=5, prueba="tested",
                          cubre=["src/db/seed.sql", "src/db/schema.sql"], huella=h8, fecha="27/08")
    # Cambiar solo el seed
    open(ruta_seed, "w").write("INSERT INTO users VALUES (1, 'updated');\n")
    subprocess.run(["git", "add", "src/db/seed.sql"], cwd=d8, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "update"], cwd=d8, check=True)
    # Acta expired (seed changed), but declare debt for a path in cubre -> approve
    cuaderno.agregar_deuda(p8, que="src/db/seed.sql", motivo="seed update reviewed",
                           quien="Tincho", fecha="27/08")
    r8 = decidir(d8)
    assert r8["decision"] == "approve", f"Round 2: debt for cubre path should approve: {r8}"

    # Test 4: Two expired actas, only one covered by debt -> block uncovered only
    d9 = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q"], cwd=d9, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=d9, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=d9, check=True)
    p9 = os.path.join(d9, "PROOF.md")
    os.makedirs(os.path.join(d9, "src", "auth"), exist_ok=True)
    os.makedirs(os.path.join(d9, "src", "db"), exist_ok=True)
    ruta_auth = os.path.join(d9, "src", "auth", "login.ts")
    ruta_model = os.path.join(d9, "src", "db", "model.prisma")
    open(ruta_auth, "w").write("export const login = () => {}\n")
    open(ruta_model, "w").write("model User {}\n")
    subprocess.run(["git", "add", "."], cwd=d9, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=d9, check=True)
    # Two actas
    h9_auth = huella.calcular(["src/auth/login.ts"], d9)
    h9_model = huella.calcular(["src/db/model.prisma"], d9)
    cuaderno.agregar_acta(p9, que="src/auth/login.ts", nivel=5, prueba="401 test",
                          cubre=["src/auth/login.ts"], huella=h9_auth, fecha="27/08")
    cuaderno.agregar_acta(p9, que="src/db/model.prisma", nivel=5, prueba="schema test",
                          cubre=["src/db/model.prisma"], huella=h9_model, fecha="27/08")
    # Modify both
    open(ruta_auth, "w").write("export const login = (x) => x\n")
    open(ruta_model, "w").write("model User {id Int}\n")
    subprocess.run(["git", "add", "."], cwd=d9, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "update"], cwd=d9, check=True)
    # Declare debt for only one of them
    cuaderno.agregar_deuda(p9, que="src/auth/login.ts", motivo="auth reviewed",
                           quien="Tincho", fecha="27/08")
    # Should block but only report the uncovered acta (model.prisma)
    r9 = decidir(d9)
    assert r9["decision"] == "block", f"Round 2: uncovered acta should block: {r9}"
    assert "model.prisma" in r9["reason"], f"Round 2: should name uncovered acta: {r9['reason']}"
    assert "login.ts" not in r9["reason"], f"Round 2: should not name covered acta: {r9['reason']}"

    # Un acta cuyo `que` es una ruta pero no cubre archivos NO tapa ese archivo.
    # (cuaderno.agregar_acta ya la rechaza; se escribe a mano para probar que el
    # hook tampoco la acepta si aparece en un PROOF.md escrito por otro lado.)
    d11 = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q"], cwd=d11, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=d11, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=d11, check=True)
    os.makedirs(os.path.join(d11, "src", "auth"), exist_ok=True)
    open(os.path.join(d11, "src", "auth", "login.ts"), "w").write("export const login = () => {}\n")
    p11 = os.path.join(d11, "PROOF.md")
    datos11 = cuaderno.leer(p11)
    datos11["actas"].append({"fecha": "27/08", "que": "src/auth/login.ts", "nivel": 5,
                             "prueba": "confia en mi", "cubre": [], "huella": "000000"})
    cuaderno.escribir(p11, datos11)
    r11b = decidir(d11)
    assert r11b["decision"] == "block", f"un acta sin cubre no puede tapar un archivo: {r11b}"
    assert "src/auth/login.ts" in r11b["reason"], r11b["reason"]

    # stop_hook_active: aprueba igual, pero nombra lo que quedo sin probar.
    # Es la invariante: el hook nunca puede dejar el turno sin poder cerrar.
    d10 = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q"], cwd=d10, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=d10, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=d10, check=True)
    os.makedirs(os.path.join(d10, "src", "auth"), exist_ok=True)
    ruta10 = os.path.join(d10, "src", "auth", "login.ts")
    open(ruta10, "w").write("export const login = () => {}\n")
    subprocess.run(["git", "add", "."], cwd=d10, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=d10, check=True)
    open(ruta10, "w").write("export const login = (u) => u\n")
    assert decidir(d10)["decision"] == "block", decidir(d10)
    r10 = segunda_vuelta(d10)
    assert r10["decision"] == "approve", r10
    assert "src/auth/login.ts" in r10["systemMessage"], r10
    # y en un proyecto sin nada pendiente tambien aprueba, sin inventar un motivo
    r11 = segunda_vuelta(tempfile.mkdtemp())
    assert r11["decision"] == "approve", r11

    # El caso real del 07/10: el agente commitea el webhook de cobro dentro del
    # turno. Antes el hook aprobaba (git status vacio); con la marca, frena.
    import deteccion
    d12 = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q"], cwd=d12, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=d12, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=d12, check=True)
    open(os.path.join(d12, "README.md"), "w").write("x\n")
    subprocess.run(["git", "add", "."], cwd=d12, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=d12, check=True)
    deteccion.guardar_marca(d12, "ses")  # lo que hace SessionStart
    os.makedirs(os.path.join(d12, "functions", "stripe-webhook"))
    open(os.path.join(d12, "functions", "stripe-webhook", "index.ts"), "w").write("x\n")
    subprocess.run(["git", "add", "."], cwd=d12, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "webhook"], cwd=d12, check=True)
    assert decidir(d12)["decision"] == "approve", "sin sesion se comporta como antes"
    r12 = decidir(d12, "ses")
    assert r12["decision"] == "block", r12
    assert "functions/stripe-webhook/index.ts" in r12["reason"], r12["reason"]
    assert "_pendientes" not in _limpiar(r12), "lo interno no viaja al harness"
    # el agente no hace nada: la segunda vuelta deja pasar, pero lo anota
    r12b = segunda_vuelta(d12, "ses")
    assert r12b["decision"] == "approve", r12b
    assert "Quedó anotado en PROOF.md" in r12b["systemMessage"], r12b
    p12 = os.path.join(d12, "PROOF.md")
    abiertos = cuaderno.leer(p12)["abierto"]
    assert len(abiertos) == 1 and abiertos[0].startswith("functions/stripe-webhook/index.ts — "), abiertos
    assert cuaderno.SIN_PRUEBA in abiertos[0], abiertos
    # ABIERTO no es una deuda: no destraba. Pero si vuelve a pasar, no se duplica.
    segunda_vuelta(d12, "ses")
    assert len(cuaderno.leer(p12)["abierto"]) == 1, cuaderno.leer(p12)["abierto"]
    # el turno cerro: se mueve la marca y el turno siguiente arranca limpio
    deteccion.guardar_marca(d12, "ses")
    assert decidir(d12, "ses")["decision"] == "approve", decidir(d12, "ses")
    # cuando llega la prueba, la anotacion se va sola
    h12 = huella.calcular(["functions/stripe-webhook/index.ts"], d12)
    cuaderno.agregar_acta(p12, que="El webhook rechaza firmas falsas", nivel=5,
                          prueba="400 en el panel de Stripe",
                          cubre=["functions/stripe-webhook/index.ts"], huella=h12, fecha="23/10")
    assert cuaderno.leer(p12)["abierto"] == [], cuaderno.leer(p12)["abierto"]

    print("stop_gate.py OK")


if __name__ == "__main__":
    import sys
    if "--autotest" in sys.argv:
        _autotest()
    else:
        main()
