#!/usr/bin/env python3
"""
Dice si lo que se toco cae en alguna de las categorias caras del catalogo.

Por que existe: el hook necesita saber si frenar, y esa decision tiene que ser
determinista y barata. No reemplaza al criterio de la skill: es la red de
seguridad. La skill juzga con contexto; esto solo detecta senales fuertes.

Deliberadamente conservador en v1: preferimos dejar pasar algo (el usuario
tiene /proof a mano) antes que frenar de mas. Un plugin que molesta con
falsos positivos se desinstala el segundo dia, y ahi no protege nada.
"""

import os
import re
import subprocess

# nivel 5 = hace falta un tercero sin interes que lo confirme (spec §4)
CATEGORIAS = {
    "pago": {
        "nombre": "Cobro / pago",
        "nivel": 5,
        "patrones": ["pago", "pagos", "payment", "checkout", "billing", "stripe",
                     "mercadopago", "subscription", "suscripcion", "invoice", "webhook"],
    },
    "auth": {
        "nombre": "Login / auth",
        "nivel": 5,
        "patrones": ["auth", "login", "logout", "session", "sesion", "token",
                     "password", "oauth", "signup", "register"],
    },
    "datos": {
        "nombre": "Datos de usuario",
        "nivel": 5,
        "patrones": ["migration", "migracion", "schema", "esquema", "prisma",
                     "models", "modelo", "seed", "database", "rls"],
    },
    "permisos": {
        "nombre": "Permisos / multi-tenant",
        "nivel": 5,
        "patrones": ["permission", "permiso", "role", "rol", "policy", "policies",
                     "tenant", "acl", "guard"],
    },
    "deploy": {
        "nombre": "Deploy / publicación",
        "nivel": 5,
        "patrones": ["dockerfile", "deploy", "vercel.json", "netlify.toml",
                     "workflow", "pipeline", "ci.yml", "cd.yml"],
    },
    "mensajes": {
        "nombre": "Mails / notificaciones",
        "nivel": 5,
        "patrones": ["mail", "email", "smtp", "resend", "sendgrid", "notificacion",
                     "notification", "whatsapp", "twilio"],
    },
    "backup": {
        "nombre": "Backup",
        "nivel": 5,
        "patrones": ["backup", "restore", "dump", "snapshot"],
    },
    "programado": {
        "nombre": "Tarea automática / cron",
        "nivel": 5,
        "patrones": ["cron", "scheduler", "schedule", "job", "worker", "queue"],
    },
}


def clasificar(archivos):
    """Categoria cara -> archivos que la dispararon. Vacio si nada es caro."""
    resultado = {}
    for ruta in archivos:
        # ponytail: tokenizar por separadores comunes, no substring matching
        # evita falsos positivos como "rol" en "controller" o "acl" en "oracle"
        ruta_bajo = ruta.lower()
        tokens = []
        current_token = []
        for char in ruta_bajo:
            if char in "/\\-_. ":
                if current_token:
                    tokens.append("".join(current_token))
                    current_token = []
            else:
                current_token.append(char)
        if current_token:
            tokens.append("".join(current_token))

        # basename es el filename completo (ultimo componente del path)
        basename = ruta_bajo.split("/")[-1].split("\\")[-1]

        for clave, cat in CATEGORIAS.items():
            # un patron dispara si es token exacto o un prefijo de un token
            # (ej: "migration" matchea "migrations", pero "rol" no matchea "controller")
            # si el patron contiene un punto, matchea contra el basename
            for patron in cat["patrones"]:
                if "." in patron:
                    if basename == patron:
                        resultado.setdefault(clave, []).append(ruta)
                        break
                else:
                    for token in tokens:
                        if token == patron or token.startswith(patron + "_") or token.startswith(patron + "s"):
                            resultado.setdefault(clave, []).append(ruta)
                            break
                if ruta in resultado.get(clave, []):
                    break
    return resultado


# Carpetas que no son del proyecto aunque git las liste: dependencias, entornos
# y salidas de build. Se comparan como SEGMENTO de ruta, nunca como substring,
# para no descartar "src/build_pipeline.ts" por contener "build".
RUIDO = {"node_modules", ".venv", "venv", "dist", "build", "target",
         "vendor", ".next", "__pycache__", ".git"}


def _segmentos(ruta):
    """Los tramos de una ruta, con separador de unix o de windows."""
    return [t for t in re.split(r"[/\\]", ruta) if t]


def _es_ruido(ruta):
    return any(seg in RUIDO for seg in _segmentos(ruta))


def _git(args, raiz):
    """Corre git y devuelve stdout, o None si no hay git o el comando fallo."""
    try:
        salida = subprocess.run(["git"] + args, cwd=raiz,
                                capture_output=True, text=True, timeout=5)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    if salida.returncode != 0:
        return None
    return salida.stdout


def cambios_sin_commitear(raiz):
    """
    Archivos modificados segun git, sin commitear, relativos a `raiz`.

    Devuelve None si no hay git: es la senal de degradacion. El hook informa
    pero no bloquea, porque sin git no puede saber que se toco.

    Dos cuidados que parecen detalles y no lo son:

    - `--untracked-files=all`, y el ruido se filtra despues por nombre de
      carpeta (RUIDO). El default de git (`=normal`) colapsa CUALQUIER carpeta
      enteramente sin trackear en una sola linea —"?? src/"— y eso pasa
      tambien en un repo con historia: un agente que crea `src/auth/` en un
      turno dejaba de ser visto por el hook, que aprobaba codigo caro sin
      probar. Ceguera silenciosa es peor que ruido. Con `=all` se ven los
      archivos uno por uno y se descartan los que viven dentro de una carpeta
      de dependencias o de build.
      El limite de este filtro: un proyecto cuyo codigo propio viva dentro de
      una carpeta con uno de esos nombres (un `dist/` escrito a mano, un
      paquete llamado `vendor`) queda invisible para el hook. Se prefiere eso
      a bloquear el primer turno por `node_modules/stripe/index.js`.
    - git imprime las rutas relativas a la raiz del REPO, no al directorio de
      la sesion. En un monorepo trabajando en apps/web, sin traducirlas el
      hook nombraria los paquetes hermanos y la huella se calcularia sobre
      rutas que no existen desde ahi. Por eso se traducen contra `raiz` y lo
      que cae afuera se descarta.
    """
    salida = _git(["status", "--porcelain", "--untracked-files=all"], raiz)
    if salida is None:
        return None
    techo = _git(["rev-parse", "--show-toplevel"], raiz)
    if techo is None:
        return None
    # realpath en los dos lados: en macOS /var y /private/var son el mismo lugar
    # y git devuelve uno mientras la sesion usa el otro. Sin esto, todo cae afuera.
    techo = os.path.realpath(techo.strip())
    base = os.path.realpath(raiz)

    archivos = []
    for linea in salida.splitlines():
        if len(linea) < 4:
            continue
        ruta = linea[3:].strip().strip('"')
        # git muestra los renombrados como "viejo -> nuevo"; nos interesa el nuevo
        if " -> " in ruta:
            ruta = ruta.split(" -> ", 1)[1]
        if _es_ruido(ruta):
            continue
        rel = os.path.relpath(os.path.join(techo, ruta), base)
        # Lo que quedo fuera del directorio de la sesion no es asunto de este turno.
        if rel == os.pardir or rel.startswith(os.pardir + os.sep):
            continue
        archivos.append(rel)
    return archivos


def _autotest():
    import tempfile, os, subprocess

    # rutas caras se clasifican en su categoria
    r = clasificar(["src/auth/session.ts", "app/checkout/stripe_webhook.py"])
    assert "auth" in r, r
    assert "pago" in r, r
    assert r["auth"] == ["src/auth/session.ts"], r

    # presentacion no dispara nada
    assert clasificar(["src/styles/main.css", "README.md", "docs/guia.md"]) == {}

    # una migracion es cara aunque no diga "auth" ni "pago"
    assert "datos" in clasificar(["db/migrations/003_add_users.sql"])

    # el nombre del directorio alcanza, no hace falta que este en el archivo
    assert "pago" in clasificar(["billing/index.ts"])

    # sin git devuelve None, que NO es lo mismo que lista vacia
    d = tempfile.mkdtemp()
    assert cambios_sin_commitear(d) is None

    # con git, un archivo nuevo aparece
    subprocess.run(["git", "init", "-q"], cwd=d, check=True)
    open(os.path.join(d, "nuevo.py"), "w").write("x = 1\n")
    assert cambios_sin_commitear(d) == ["nuevo.py"], cambios_sin_commitear(d)

    # monorepo: desde apps/web solo se ven sus propios cambios, y relativos a ahi
    m = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q"], cwd=m, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=m, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=m, check=True)
    web = os.path.join(m, "apps", "web", "src")
    api = os.path.join(m, "apps", "api", "src")
    os.makedirs(web); os.makedirs(api)
    open(os.path.join(web, "login.ts"), "w").write("a\n")
    open(os.path.join(api, "pagos.ts"), "w").write("b\n")
    subprocess.run(["git", "add", "."], cwd=m, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=m, check=True)
    open(os.path.join(web, "login.ts"), "w").write("a2\n")
    open(os.path.join(api, "pagos.ts"), "w").write("b2\n")
    desde_web = cambios_sin_commitear(os.path.join(m, "apps", "web"))
    assert desde_web == ["src/login.ts"], desde_web
    # y desde la raiz del repo se ven los dos, con el prefijo entero
    desde_raiz = sorted(cambios_sin_commitear(m))
    assert desde_raiz == ["apps/api/src/pagos.ts", "apps/web/src/login.ts"], desde_raiz

    # node_modules no aparece, ni siquiera con archivos adentro, PERO el archivo
    # caro que esta al lado si: ceguera cero, ruido cero
    n = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q"], cwd=n, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=n, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=n, check=True)
    os.makedirs(os.path.join(n, "node_modules", "stripe"))
    open(os.path.join(n, "node_modules", "stripe", "index.js"), "w").write("x\n")
    open(os.path.join(n, "node_modules", "passport.js"), "w").write("x\n")
    os.makedirs(os.path.join(n, "src", "auth"))
    open(os.path.join(n, "src", "auth", "login.ts"), "w").write("x\n")
    assert cambios_sin_commitear(n) == ["src/auth/login.ts"], cambios_sin_commitear(n)

    # una carpeta nueva ENTERA se ve archivo por archivo, tambien con historia:
    # con -unormal git la colapsaba en "?? src/" y el hook quedaba ciego
    open(os.path.join(n, "README.md"), "w").write("x\n")
    subprocess.run(["git", "add", "README.md"], cwd=n, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=n, check=True)
    assert cambios_sin_commitear(n) == ["src/auth/login.ts"], cambios_sin_commitear(n)

    # el filtro es por segmento, no por substring: esto NO es build/
    b = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q"], cwd=b, check=True)
    os.makedirs(os.path.join(b, "src"))
    open(os.path.join(b, "src", "build_pipeline.ts"), "w").write("x\n")
    assert cambios_sin_commitear(b) == ["src/build_pipeline.ts"], cambios_sin_commitear(b)

    # falsos positivos: "rol" no debe matching en "controller", "acl" en "oracle", etc.
    assert clasificar(["src/controllers/user_controller.py"]) == {}, "controller no es rol"
    assert clasificar(["app/control/index.ts"]) == {}, "control no es rol"
    assert clasificar(["lib/oracle_client.py"]) == {}, "oracle no es acl"
    assert clasificar(["components/Modal.tsx"]) == {}, "Modal no es nada"

    # patterns con punto: filenames son caros
    assert "deploy" in clasificar(["vercel.json"]), "vercel.json es deploy"
    assert "deploy" in clasificar(["netlify.toml"]), "netlify.toml es deploy"
    assert "deploy" in clasificar(["Dockerfile"]), "Dockerfile es deploy"

    # backslash como separador (windows paths)
    assert "auth" in clasificar(["src\\auth\\session.ts"]), "backslash-separated path"

    print("deteccion.py OK")


if __name__ == "__main__":
    _autotest()
