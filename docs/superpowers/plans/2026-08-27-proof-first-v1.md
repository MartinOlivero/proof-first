# Proof-First v1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un plugin de Claude Code que impide dar por cerrado un cambio caro sin evidencia observable desde afuera del agente, y que registra esa evidencia con vencimiento automático.

**Architecture:** Tres módulos de Python puro (lectura/escritura de `PROOF.md`, huellas de archivos, detección de categorías caras) que dos hooks consumen. El criterio completo vive en la skill —los hooks solo agregan obligatoriedad—, y un subagente con contexto limpio va a buscar los artefactos externos.

**Tech Stack:** Python 3 (solo librería estándar), Markdown, git (opcional, con degradación).

**Spec:** `docs/superpowers/specs/2026-08-27-proof-first-design.md`

## Global Constraints

- **Solo librería estándar de Python 3.** Sin dependencias externas. El plugin tiene que instalarse en 10 segundos en macOS, Linux y Windows.
- **Sin git el plugin no bloquea.** Informa y sigue. Degradación, nunca error.
- **Ninguna instrucción esencial vive solo dentro de un hook** (spec §12). Los hooks refuerzan lo que la skill ya dice.
- **Idioma:** `description` de `plugin.json` y de `SKILL.md` en inglés (para GitHub). Cuerpo de la skill, docstrings y comentarios en español. Es la convención de `legal-docs`.
- **Autochequeo:** cada módulo Python termina en `if __name__ == "__main__": _autotest()` con asserts. Es la convención de los plugins de Tincho (`python3 archivo.py` corre su propio chequeo).
- **Licencia MIT**, igual que `saas-builder` y `legal-docs`.
- **Directorio de trabajo:** `<ruta-del-plugin>/` (ya existe, ya es repo git con dos commits de la spec).

---

## Estructura de archivos

| Archivo | Responsabilidad |
|---|---|
| `plugin.json` | Manifiesto |
| `README.md` | Inglés, con resumen en español (convención de los otros dos) |
| `LICENSE` | MIT |
| `lib/cuaderno.py` | Leer y escribir `PROOF.md`. Única pieza que conoce su formato |
| `lib/huella.py` | Calcular y comparar huellas de archivos. Detecta actas vencidas |
| `lib/deteccion.py` | Dados unos archivos, decir qué categorías caras tocan |
| `hooks/stop_gate.py` | El control de salida. Junta los tres módulos y decide |
| `hooks/session_report.py` | El parte de arranque |
| `hooks/hooks.json` | Registro de ambos hooks |
| `skills/proof-first/SKILL.md` | La escala + la regla operativa |
| `skills/proof-first/references/catalogo.md` | Las 10 entradas con su cómo |
| `agents/witness.md` | El verificador |
| `commands/proof.md` | Verificación a pedido |

`lib/` existe para que los dos hooks compartan código sin duplicarlo. Cada módulo tiene una responsabilidad y se puede probar solo.

---

### Task 1: El cuaderno — leer y escribir `PROOF.md`

**Files:**
- Create: `lib/cuaderno.py`

**Interfaces:**
- Consumes: nada (primera tarea)
- Produces:
  - `leer(ruta: str) -> dict` — devuelve `{"bloqueante": [str], "abierto": [str], "sin_probar": [str], "postergado": [str], "actas": [dict]}`. Cada acta es `{"fecha": str, "que": str, "nivel": int, "prueba": str, "cubre": [str], "huella": str}`. Si el archivo no existe, devuelve las cinco claves vacías.
  - `escribir(ruta: str, datos: dict) -> None`
  - `agregar_acta(ruta, que, nivel, prueba, cubre, huella, fecha) -> None`
  - `agregar_deuda(ruta, que, motivo, quien, fecha) -> None`
  - `PLANTILLA: str` — el `PROOF.md` vacío

- [ ] **Step 1: Write the failing test**

Crear `lib/cuaderno.py` con solo el autotest al final (todavía sin las funciones):

```python
def _autotest():
    import tempfile, os
    d = tempfile.mkdtemp()
    ruta = os.path.join(d, "PROOF.md")

    # archivo inexistente devuelve estructura vacía
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

    print("cuaderno.py OK")


if __name__ == "__main__":
    _autotest()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd <ruta-del-plugin> && uv run python3 lib/cuaderno.py`
Expected: FAIL con `NameError: name 'leer' is not defined`

- [ ] **Step 3: Write minimal implementation**

Agregar arriba del autotest:

```python
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
_RE_CUBRE = re.compile(r"^\s+cubre: (?P<cubre>.+?) · huella: (?P<huella>\S+)$")


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
                    acta_parcial["cubre"] = [c.strip() for c in mc.group("cubre").split(",")]
                    acta_parcial["huella"] = mc.group("huella")
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
    datos["sin_probar"] = [d for d in datos["sin_probar"] if not d.startswith(que)]
    escribir(ruta, datos)


def agregar_deuda(ruta, que, motivo, quien, fecha):
    datos = leer(ruta)
    entrada = f"{que} — {motivo} — deuda asumida por {quien} {fecha}"
    datos["sin_probar"] = [d for d in datos["sin_probar"] if not d.startswith(que)]
    datos["sin_probar"].append(entrada)
    escribir(ruta, datos)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python3 lib/cuaderno.py`
Expected: `cuaderno.py OK`

- [ ] **Step 5: Commit**

```bash
git add lib/cuaderno.py
git commit -m "feat: lectura y escritura de PROOF.md

Unica pieza que conoce el formato del cuaderno. Markdown y no JSON porque
tiene que leerlo una persona en un diff de git."
```

---

### Task 2: Huellas y vencimiento de actas

**Files:**
- Create: `lib/huella.py`

**Interfaces:**
- Consumes: nada
- Produces:
  - `calcular(archivos: list[str], raiz: str) -> str` — 6 caracteres hex. Ignora archivos inexistentes.
  - `vencidas(actas: list[dict], raiz: str) -> list[dict]` — las actas cuya huella ya no coincide.

- [ ] **Step 1: Write the failing test**

```python
def _autotest():
    import tempfile, os
    d = tempfile.mkdtemp()
    a = os.path.join(d, "uno.py")
    open(a, "w").write("print(1)\n")

    h1 = calcular(["uno.py"], d)
    assert len(h1) == 6, h1
    # misma entrada, misma huella
    assert calcular(["uno.py"], d) == h1

    # cambiar el contenido cambia la huella
    open(a, "w").write("print(2)\n")
    h2 = calcular(["uno.py"], d)
    assert h2 != h1, (h1, h2)

    # un archivo que no existe no rompe
    assert len(calcular(["fantasma.py"], d)) == 6

    # el acta con huella vieja aparece vencida; la actualizada no
    actas = [{"que": "viejo", "cubre": ["uno.py"], "huella": h1},
             {"que": "nuevo", "cubre": ["uno.py"], "huella": h2}]
    v = vencidas(actas, d)
    assert [x["que"] for x in v] == ["viejo"], v

    print("huella.py OK")


if __name__ == "__main__":
    _autotest()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python3 lib/huella.py`
Expected: FAIL con `NameError: name 'calcular' is not defined`

- [ ] **Step 3: Write minimal implementation**

```python
#!/usr/bin/env python3
"""
Calcula la huella de los archivos que cubre un acta, para saber cuando vencio.

Por que existe: un acta que dice "el pago se verifico el 12/08" es oro hasta
que alguien toca el checkout el 20/08. A partir de ahi sigue diciendo que esta
probado, y miente. Es la VTV del auto: certifica marzo, no dice nada de los
frenos que se cambiaron en julio.

No usa git a proposito: hashlib funciona igual en un proyecto sin git, en
Windows y en una carpeta suelta. La portabilidad vale mas que reusar git aca.
"""

import hashlib
import os

LARGO = 6


def calcular(archivos, raiz):
    """Huella combinada de varios archivos. Determinista: ordena antes de sumar."""
    h = hashlib.sha256()
    for rel in sorted(archivos):
        h.update(rel.encode("utf-8"))
        ruta = os.path.join(raiz, rel)
        try:
            with open(ruta, "rb") as f:
                h.update(f.read())
        except (FileNotFoundError, IsADirectoryError, PermissionError):
            # Un archivo borrado o ilegible tambien cambia la huella, que es
            # lo correcto: el acta que lo cubria ya no vale.
            h.update(b"<ausente>")
    return h.hexdigest()[:LARGO]


def vencidas(actas, raiz):
    """Las actas cuya huella ya no coincide con el estado real de sus archivos."""
    fuera = []
    for a in actas:
        if not a.get("cubre"):
            continue
        if calcular(a["cubre"], raiz) != a.get("huella"):
            fuera.append(a)
    return fuera
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python3 lib/huella.py`
Expected: `huella.py OK`

- [ ] **Step 5: Commit**

```bash
git add lib/huella.py
git commit -m "feat: huellas de archivos y deteccion de actas vencidas

hashlib y no git: funciona igual sin repo, en Windows y en carpeta suelta."
```

---

### Task 3: Detección de categorías caras

**Files:**
- Create: `lib/deteccion.py`

**Interfaces:**
- Consumes: nada
- Produces:
  - `CATEGORIAS: dict[str, dict]` — clave → `{"nombre": str, "nivel": int, "patrones": [str]}`
  - `clasificar(archivos: list[str]) -> dict[str, list[str]]` — categoría cara → archivos que la dispararon. Vacío si nada es caro.
  - `cambios_sin_commitear(raiz: str) -> list[str] | None` — rutas relativas modificadas según git. `None` si no hay git (señal de degradación, distinta de "no hay cambios").

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python3 lib/deteccion.py`
Expected: FAIL con `NameError: name 'clasificar' is not defined`

- [ ] **Step 3: Write minimal implementation**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python3 lib/deteccion.py`
Expected: `deteccion.py OK`

- [ ] **Step 5: Commit**

```bash
git add lib/deteccion.py
git commit -m "feat: deteccion de categorias caras y cambios sin commitear

Conservador a proposito: un falso positivo cuesta la desinstalacion,
un falso negativo lo cubre /proof a mano."
```

---

### Task 4: El control de salida (hook `Stop`)

**Files:**
- Create: `hooks/stop_gate.py`
- Create: `hooks/hooks.json`

**Interfaces:**
- Consumes: `cuaderno.leer`, `huella.vencidas`, `deteccion.clasificar`, `deteccion.cambios_sin_commitear`, `deteccion.CATEGORIAS`
- Produces:
  - `decidir(raiz: str) -> dict` — `{"decision": "approve"}` o `{"decision": "block", "reason": str}`
  - Ejecutado como script: lee JSON por stdin, imprime JSON de decisión por stdout, exit 0.

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python3 hooks/stop_gate.py --autotest`
Expected: FAIL con `NameError: name 'decidir' is not defined`

- [ ] **Step 3: Write minimal implementation**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python3 hooks/stop_gate.py --autotest`
Expected: `stop_gate.py OK`

- [ ] **Step 5: Create hooks.json**

```json
{
  "description": "Impide cerrar un turno que toco codigo caro sin evidencia observable desde afuera del agente, y muestra el estado del cuaderno al abrir la sesion.",
  "hooks": {
    "Stop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "\"${CLAUDE_PLUGIN_ROOT}\"/hooks/stop_gate.py",
            "timeout": 15
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "matcher": "startup|resume",
        "hooks": [
          {
            "type": "command",
            "command": "\"${CLAUDE_PLUGIN_ROOT}\"/hooks/session_report.py",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 6: Verificar que el script corre como lo va a invocar Claude Code**

```bash
chmod +x hooks/stop_gate.py
echo '{"cwd":"<ruta-del-plugin>"}' | ./hooks/stop_gate.py
```
Expected: un JSON con `{"decision": "approve"}` (el repo del plugin no tiene código caro sin acta)

- [ ] **Step 7: Commit**

```bash
git add hooks/stop_gate.py hooks/hooks.json
git commit -m "feat: hook Stop que frena lo caro sin evidencia

Con valvula de escape: declarar la deuda alcanza para cerrar, ignorarla no.
Sin git degrada a no bloquear nunca. Un hook roto aprueba, no traba."
```

---

### Task 5: El parte de arranque (hook `SessionStart`)

**Files:**
- Create: `hooks/session_report.py`

**Interfaces:**
- Consumes: `cuaderno.leer`, `huella.vencidas`
- Produces: `resumen(raiz: str) -> str | None` — el texto del parte, o `None` si no hay nada que decir.

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python3 hooks/session_report.py --autotest`
Expected: FAIL con `NameError: name 'resumen' is not defined`

- [ ] **Step 3: Write minimal implementation**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python3 hooks/session_report.py --autotest`
Expected: `session_report.py OK`

- [ ] **Step 5: Commit**

```bash
git add hooks/session_report.py
git commit -m "feat: parte de arranque con el estado del cuaderno

Sin esto PROOF.md existe pero nadie lo abre."
```

---

### Task 6: La skill — escala, regla y catálogo

**Files:**
- Create: `skills/proof-first/SKILL.md`
- Create: `skills/proof-first/references/catalogo.md`

**Interfaces:**
- Consumes: nada (es texto)
- Produces: el criterio completo. Los hooks solo lo hacen obligatorio; la skill tiene que servir sola (spec §12).

- [ ] **Step 1: Escribir `SKILL.md`**

Frontmatter con `description` en inglés (para GitHub y para el disparo en ambos idiomas), cuerpo en español:

```markdown
---
name: proof-first
description: This skill should be used when work touches money, authentication, user data, permissions, deploys, outbound messages, backups or scheduled jobs — anything where being wrong is expensive — and someone needs to know whether it actually works. It replaces the agent's own report with evidence observable from outside the agent, on a 0-6 scale, and carries a catalogue of what counts as real proof versus the false proof usually accepted for each kind of work. Trigger phrases (Spanish) include "¿cómo compruebo que esto funciona?", "¿esto ya está probado?", "verificá que el pago funcione", "¿cómo sé que el login anda?", "quedó andando?", "probalo de verdad". Trigger phrases (English) include "how do I verify this", "is this actually tested", "prove the payment works", "check that it really works", "show me the evidence". Use it INSTEAD of trusting a green test suite the agent itself wrote.
---

# Proof-First Development

**Nunca confiar en el reporte del agente. Solo en un artefacto observable desde
afuera del agente.**

Un test verde es el agente calificándose solo: lo escribió el mismo que escribió
el código, comparte sus supuestos y sus puntos ciegos. Un cargo apareciendo en
el panel de Stripe, no: lo emitió un tercero que no tiene interés en aprobarte.

## La escala

Un solo eje ordena todo: **la distancia entre el que afirma y el que comprueba.**

| Nivel | Qué es | Quién comprueba |
|:---:|---|---|
| 0 | "Listo, ya está implementado" | Nadie. Es una afirmación. |
| 1 | Muestra el código que escribió | Nadie. Mostrar no es probar. |
| 2 | Test verde escrito por el mismo agente | El constructor. Se aprueba solo. |
| 3 | Test preexistente, o escrito por el verificador | Alguien distinto. |
| 4 | La cosa ejecutándose: captura, log, `curl` | La máquina. El hecho, no el relato. |
| 5 | Un tercero sin interés lo confirma | Stripe, el servidor de mail, el DNS. |
| 6 | Una persona real lo usó y le funcionó | La realidad. |

Del 0 al 2 se está confiando. Del 3 para arriba, comprobando.

## La regla

```
Plata, auth, datos de usuario, permisos, deploy, mensajes, backup, cron
    → nivel 5 o no está hecho
Todo lo demás
    → nivel 4 alcanza
```

**Cuanto más caro es equivocarse, más lejos del agente tiene que estar la prueba.**

## Cómo se consigue cada prueba

Para saber qué es prueba válida y qué es falsa prueba en cada caso, leer
`references/catalogo.md`. Tiene las diez categorías con las tres columnas:
la prueba que vale, la falsa prueba habitual, y el comando concreto.

## El artefacto se pega crudo

> Si se resume, no cuenta.

No "verifiqué el pago y funciona". Va la respuesta literal del proveedor, el
`curl` con su status code, el JSON tal cual salió. Un resumen **es** el reporte
del agente, que es justamente lo que no se cree.

## Quién comprueba

Lanzá el subagente `witness`. No lo hagas vos: vos escribiste el código y ya
te convenciste de que está bien. El verificador arranca con contexto limpio y
con la consigna invertida —*demostrá que esto NO funciona*—, y no puede editar
código: si pudiera arreglar, aprobaría lo que él mismo arregló.

## Registrar

Todo lo que se prueba o se deja sin probar va a `PROOF.md` en la raíz del
proyecto, versionado en git para que sea auditable por un tercero.

- Probado → un acta con la **coordenada** de la prueba (el ID del cargo, el
  status, el usuario), nunca una copia. Las copias también se pudren.
- Sin probar por decisión del usuario → una deuda, **con su nombre y la fecha**.
  La diferencia entre "lo postergamos a propósito" y "nos olvidamos" es la
  información más valiosa del archivo.

## Si no hay hooks

Esta skill funciona sola. Los hooks solo agregan obligatoriedad; el criterio
está acá completo. Sin ellos se pierde el capataz, nunca el método.
```

- [ ] **Step 2: Escribir `references/catalogo.md`**

Copiar las 10 filas de la spec §5 (tabla completa con las tres columnas), y bajo cada fila el comando concreto. Contenido exacto de la tabla en `docs/superpowers/specs/2026-08-27-proof-first-design.md` §5 — copiarla verbatim y agregar por cada categoría un bloque así:

````markdown
### 1. Cobro / pago — nivel 5

| | |
|---|---|
| ✅ Prueba que vale | El cargo aparece en el panel del proveedor **y** el webhook llegó al servidor |
| ❌ Falsa prueba | El usuario vio la pantalla de "gracias por tu compra" |

**Por qué la falsa prueba engaña:** el redirect de éxito lo dispara el navegador
del cliente, no el proveedor. Se puede llegar a esa pantalla sin que exista
ningún cargo.

**Cómo se consigue la buena:**

```bash
# el cargo existe del lado del proveedor
curl -s https://api.stripe.com/v1/charges?limit=1 \
  -u "$STRIPE_SECRET_KEY:" | head -40

# el webhook llegó de verdad al servidor
grep -i "checkout.session.completed" logs/webhook.log | tail -3
```
````

Repetir la misma estructura para las 10 categorías de la spec.

- [ ] **Step 3: Verificar que el catálogo está completo**

```bash
grep -c "^### " skills/proof-first/references/catalogo.md
```
Expected: `10`

```bash
grep -c "Falsa prueba" skills/proof-first/references/catalogo.md
```
Expected: `10`

- [ ] **Step 4: Verificar coherencia con la detección**

Las claves de `deteccion.CATEGORIAS` (8) tienen que ser un subconjunto de las
categorías del catálogo (10). Las dos que faltan —"guardar datos" y "borrar
datos"— están fundidas en la categoría `datos` de la detección a propósito: se
detectan por los mismos archivos.

```bash
uv run python3 -c "
import sys; sys.path.insert(0, 'lib')
import deteccion
print(sorted(deteccion.CATEGORIAS))
"
```
Expected: `['auth', 'backup', 'datos', 'deploy', 'mensajes', 'pago', 'permisos', 'programado']`

- [ ] **Step 5: Commit**

```bash
git add skills/
git commit -m "feat: skill con la escala, la regla y el catalogo de 10 categorias

La columna de falsas pruebas es el corazon pedagogico: cada linea es un
'uh, yo hago exactamente eso'. Autosuficiente, funciona sin los hooks."
```

---

### Task 7: El verificador — `the witness`

**Files:**
- Create: `agents/witness.md`

**Interfaces:**
- Consumes: la escala y el catálogo de la skill (Task 6)
- Produces: un subagente invocable por nombre `witness`, que devuelve uno de tres veredictos y escribe el acta.

- [ ] **Step 1: Escribir el agente**

Formato verificado contra `feature-dev/agents/code-reviewer.md`:

```markdown
---
name: witness
description: Verifica que una afirmación sobre el sistema sea cierta, buscando un artefacto observable desde afuera del agente. Arranca sin contexto de cómo se construyó el código y con la consigna de refutar, no de confirmar. No puede editar código.
tools: Bash, Read, Grep, Glob, WebFetch
model: sonnet
color: green
---

Sos el testigo. Tu trabajo es comprobar si una afirmación sobre el sistema es
cierta, y traer el artefacto que lo demuestre.

No participaste de la construcción. No sabés cómo se resolvió, ni qué costó, ni
por qué debería funcionar. Eso es a propósito: el que construyó ya se convenció,
y por eso no puede comprobar.

## Tu consigna está invertida

**No se te pide confirmar que funciona. Se te pide demostrar que NO funciona.**

Salí a buscar la falla. Probá el caso que rompe, el usuario que no debería
entrar, el dato que no debería estar. Si con esa consigna encima no lo podés
voltear, recién ahí hay algo.

## No tenés manos

No podés editar código del proyecto. Si encontrás una falla, la reportás; no la
arreglás. Si pudieras arreglar, terminarías aprobando lo que vos mismo
arreglaste, y volveríamos al punto de partida.

Tu único permiso de escritura es `PROOF.md`.

## Qué cuenta como prueba

Leé `skills/proof-first/references/catalogo.md` para la categoría que te tocó.
Tiene la prueba que vale, la falsa prueba que hay que rechazar, y el comando.

La regla: **cuanto más caro es equivocarse, más lejos del agente tiene que estar
la prueba.** Para plata, auth, datos, permisos o deploy hace falta nivel 5 —un
tercero sin interés que lo confirme—. Un test propio no alcanza.

## El artefacto se pega crudo

Si lo resumís, no cuenta. Va la salida literal: el status code, el JSON tal cual
salió, la línea del log con su timestamp. Nunca "verifiqué y funciona".

## Devolvés uno de tres veredictos

**✅ PROBADO** — con el artefacto crudo y el nivel alcanzado. Escribí el acta en
`PROOF.md` con la *coordenada* de la prueba (el ID del cargo, el usuario, el
status), no con una copia.

**❌ REFUTADO** — encontraste la falla. Traé la evidencia de la falla, no tu
interpretación de por qué falla.

**⚠️ NO VERIFICABLE** — no pudiste conseguir la prueba. Decí exactamente qué
falta y quién lo tiene que proveer: una credencial, un entorno, una persona que
lo use. **Nunca inventes.** Este veredicto existe para que no tengas que hacerlo.
```

- [ ] **Step 2: Verificar que Claude Code lo reconoce**

```bash
grep -A1 "^name:" agents/witness.md | head -2
ls agents/
```
Expected: `name: witness` y el archivo listado. El agente aparece disponible tras reiniciar la sesión con el plugin instalado.

- [ ] **Step 3: Commit**

```bash
git add agents/witness.md
git commit -m "feat: subagente witness, el verificador sin manos

Contexto limpio, consigna invertida y sin permiso de editar codigo.
Tres veredictos, incluido 'no verificable' para que no invente."
```

---

### Task 8: El comando `/proof`

**Files:**
- Create: `commands/proof.md`

**Interfaces:**
- Consumes: `lib/cuaderno.py`, `lib/huella.py`, el agente `witness`
- Produces: el comando `/proof`, `/proof <afirmación>` y `/proof deuda`

- [ ] **Step 1: Escribir el comando**

```markdown
---
description: Muestra el estado del cuaderno de evidencia, o lanza al testigo a verificar una afirmación
---

Verificación a pedido, sin esperar al cierre del turno.

## Sin argumentos — el estado

Leé `PROOF.md` de la raíz del proyecto y mostralo así:

```
proof-first · 3 actas vigentes · 1 vencida
🔴 BLOQUEANTE  Falta decidir si el borrado es real o lógico
⚠️ SIN PROBAR  Checkout Stripe — deuda asumida por Tincho 27/08
↺ VENCIDA      Login con Google (cambió src/auth/sesion.ts)
```

Para saber cuáles vencieron:

```bash
uv run python3 -c "
import sys, os; sys.path.insert(0, os.path.expanduser('~/.claude/plugins/proof-first/lib'))
import cuaderno, huella
d = cuaderno.leer('PROOF.md')
for a in huella.vencidas(d['actas'], '.'):
    print('VENCIDA:', a['que'])
"
```

Si `PROOF.md` no existe, decilo en una línea y ofrecé crearlo. No lo crees sin
que te lo pidan.

## Con una afirmación — `/proof el checkout cobra de verdad`

1. Identificá a qué categoría del catálogo pertenece
   (`skills/proof-first/references/catalogo.md`).
2. Lanzá el subagente `witness` con **solo** la afirmación, la categoría y los
   archivos involucrados. **No le pases la conversación**: su contexto limpio es
   el requisito, no un detalle.
3. Mostrá el veredicto con el artefacto crudo, sin resumirlo.

## `/proof deuda` — lo que falta

Listá lo que está en `⚠️ HECHO SIN PROBAR`, ordenado por costo de equivocarse:
plata primero, después auth, datos, permisos, deploy, y al final el resto.

Por cada uno, decí en una línea qué prueba haría falta según el catálogo.
```

- [ ] **Step 2: Verificar el frontmatter**

```bash
head -3 commands/proof.md
```
Expected: la línea `description:` entre dos `---`

- [ ] **Step 3: Commit**

```bash
git add commands/proof.md
git commit -m "feat: comando /proof para verificar a pedido

Estado, verificacion de una afirmacion, y lista de deuda por costo."
```

---

### Task 9: Manifiesto, README y la prueba del propio plugin

**Files:**
- Create: `plugin.json`
- Create: `LICENSE`
- Create: `README.md`
- Create: `PROOF.md` (el del propio plugin, como demostración)

**Interfaces:**
- Consumes: todas las tareas anteriores
- Produces: el plugin instalable y la evidencia de que funciona (spec §13)

- [ ] **Step 1: Escribir `plugin.json`**

Estructura verificada contra `legal-docs/plugin.json`:

```json
{
  "name": "proof-first",
  "version": "1.0.0",
  "description": "Proof-First Development: never trust the agent's report, only an artifact observable from outside the agent. A green test suite is the agent grading its own homework; a charge in the Stripe dashboard is not. Blocks a turn from closing when money, auth, user data, permissions or deploys were touched without external evidence, sends a clean-context subagent to go get it, and records it in a PROOF.md that expires on its own when the code changes.",
  "author": {
    "name": "Martín Olivero / IamAutom",
    "url": "https://iamautom.com"
  },
  "homepage": "https://github.com/MartinOlivero/proof-first",
  "repository": "https://github.com/MartinOlivero/proof-first",
  "license": "MIT",
  "keywords": [
    "claude-code",
    "claude-code-plugin",
    "claude-skills",
    "proof-first",
    "verification",
    "evidence",
    "testing",
    "vibe-coding",
    "ai-agents",
    "quality-gate",
    "out-of-band"
  ]
}
```

- [ ] **Step 2: Escribir `LICENSE`**

```bash
curl -s https://raw.githubusercontent.com/MartinOlivero/saas-builder/main/LICENSE -o LICENSE || \
  cp ../legal-docs/LICENSE LICENSE
head -3 LICENSE
```
Expected: la licencia MIT con "Martín Olivero"

- [ ] **Step 3: Escribir `README.md`**

En inglés con `<details>` en español, siguiendo el formato de `saas-builder`. Debe abrir con la regla, no con la instalación:

```markdown
# proof-first

**Your agent said it works. Who checked?**

> The rule: never trust the agent's report, only an artifact you can observe
> from outside the agent. A green test suite is the agent grading its own
> homework. A charge appearing in the Stripe dashboard is not.
```

Secciones: The problem · The scale (tabla 0-6) · The catalogue (tabla de 10 con
la columna de falsas pruebas) · What it does (hook, witness, PROOF.md) · Install
· How it degrades (sin git, sin hooks) · Where it fits (vs SDD, vs TDD, vs RDD,
vs engram) · resumen en español en `<details>`.

- [ ] **Step 4: La prueba del propio plugin — el escenario completo**

Correr en un proyecto de prueba, no en el del plugin. Los cuatro pasos de la
spec §13, cada uno dejando su artefacto:

```bash
# preparar
D=$(mktemp -d) && cd "$D" && git init -q
mkdir -p src/auth && echo "export const login = () => {}" > src/auth/login.ts
```

Con el plugin instalado, en una sesión de Claude Code sobre `$D`:

1. Pedirle al agente cualquier cambio y que cierre → **el hook frena** nombrando
   `auth` y `nivel 5`. *Artefacto: la transcripción con el bloqueo.*
2. Lanzar el `witness` → devuelve `no verificable` diciendo qué credencial falta.
   *Artefacto: su respuesta.*
3. Asumir la deuda → aparece en `PROOF.md` con nombre y fecha.
   *Artefacto: `git diff PROOF.md`.*
4. Tocar de nuevo un archivo cubierto por un acta → aparece vencida al reabrir.
   *Artefacto: el parte de arranque de la sesión siguiente.*

**Si alguno de los cuatro no se puede mostrar en crudo, el plugin no está
terminado.** Es la propia regla aplicada a sí misma.

- [ ] **Step 5: Escribir el `PROOF.md` del propio plugin**

Con el acta real del paso anterior. Es la demostración más honesta que puede
tener el repo: el plugin verificado con su propio método, nivel 4, a la vista.

- [ ] **Step 6: Commit**

```bash
git add plugin.json LICENSE README.md PROOF.md
git commit -m "feat: manifiesto, README y la prueba del propio plugin

Los cuatro pasos de la spec §13 corridos en un proyecto real, con sus
artefactos. proof-first verificado con su propia regla."
```

---

## Notas de ejecución

**Orden:** las tareas 1-3 son independientes entre sí y pueden ir en paralelo.
La 4 y la 5 dependen de las tres. La 6, 7 y 8 son texto y pueden ir en paralelo
con cualquiera. La 9 va última.

**Lo que NO entra en v1** (spec §14): integración escrita con engram, promoción
automática al `CLAUDE.md`, `.proof-catalog.md` extensible, soporte para otros
CLIs, métricas.

**Después de v1:** publicar el repo en GitHub, agregar el complemento opcional
en el README de `saas-builder` (que hoy declara el hueco: *"dev process →
Superpowers owns this"*), y recién ahí los videos.
