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
        bajo = ruta.lower()
        for clave, cat in CATEGORIAS.items():
            if any(p in bajo for p in cat["patrones"]):
                resultado.setdefault(clave, []).append(ruta)
    return resultado


def cambios_sin_commitear(raiz):
    """
    Archivos modificados segun git, sin commitear.

    Devuelve None si no hay git: es la senal de degradacion. El hook informa
    pero no bloquea, porque sin git no puede saber que se toco.
    """
    try:
        salida = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=raiz, capture_output=True, text=True, timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if salida.returncode != 0:
        return None

    archivos = []
    for linea in salida.stdout.splitlines():
        if len(linea) < 4:
            continue
        ruta = linea[3:].strip().strip('"')
        # git muestra los renombrados como "viejo -> nuevo"; nos interesa el nuevo
        if " -> " in ruta:
            ruta = ruta.split(" -> ", 1)[1]
        archivos.append(ruta)
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

    print("deteccion.py OK")


if __name__ == "__main__":
    _autotest()
