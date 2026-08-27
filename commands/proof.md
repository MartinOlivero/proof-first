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

Para saber cuáles vencieron, calculá la huella con `shasum` y comparala contra
la que quedó escrita en el acta. **No dependas de la ruta de instalación del
plugin:** `${CLAUDE_PLUGIN_ROOT}` no se sustituye dentro de un comando —solo en
hooks y MCP— y un path escrito a mano rompe en silencio en cuanto el plugin se
instala en otro lado.

Por cada acta del cuaderno, con sus archivos en `cubre` y su `huella`:

```bash
# repite exactamente lo que hace lib/huella.py: nombre + contenido, ordenado
uv run python3 - <<'PY'
import hashlib, os, re
texto = open("PROOF.md", encoding="utf-8").read()
actas = re.findall(
    r"✅ (\S+) · (.+?) · nivel (\d+)\n\s+prueba: .*\n\s+cubre: (.+?) · huella: (\S+)",
    texto)
for fecha, que, nivel, cubre, guardada in actas:
    archivos = [c.strip() for c in cubre.split(",")]
    h = hashlib.sha256()
    for rel in sorted(archivos):
        h.update(rel.encode("utf-8"))
        try:
            h.update(open(rel, "rb").read())
        except OSError:
            h.update(b"<ausente>")
    estado = "vigente" if h.hexdigest()[:6] == guardada else "VENCIDA"
    print(f"{estado:8} {que}  ({cubre})")
PY
```

Si `PROOF.md` no existe, decilo en una línea y ofrecé crearlo. No lo crees sin
que te lo pidan.

## Con una afirmación — `/proof el checkout cobra de verdad`

1. Identificá a qué categoría del catálogo pertenece y leé su fila completa
   (`skills/proof-first/references/catalogo.md`): la prueba que vale, la
   falsa prueba y el comando.
2. Lanzá el subagente `witness` pasándole **solo** la afirmación, esa fila del
   catálogo y los archivos involucrados. **No le pases la conversación**: su
   contexto limpio es el requisito, no un detalle. El testigo no abre el
   catálogo por su cuenta: si no le llega la fila, no la tiene.
3. Mostrá el veredicto con el artefacto crudo, sin resumirlo.

## `/proof deuda` — lo que falta

Listá lo que está en `⚠️ HECHO SIN PROBAR`, ordenado por costo de equivocarse:
plata primero, después auth, datos, permisos, deploy, y al final el resto.

Por cada uno, decí en una línea qué prueba haría falta según el catálogo.
