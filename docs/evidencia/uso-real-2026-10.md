# Corridas del hook tras los arreglos de uso real — 04/10/2026

Corridas por el controlador (Claude, en la sesión de Tincho) sobre repos
temporales, invocando `hooks/stop_gate.py` y `hooks/session_report.py` con el
mismo JSON por stdin que les pasa Claude Code. Salidas literales; lo único
editado es la ruta del directorio temporal (`<repo>`, `<sin-git>`).

Las situaciones G–K son nuevas (lo que cambió en la 1.0.1). C–F repiten las del
27/08 (`hook-runs.md`) sobre el código nuevo; A y B quedan cubiertas por H e I.

```
### G · solo capturas, un informe, un test y la sonda del testigo
?? .proof-tmp/seed.mjs
?? docs/reporte-logout.md
?? src/constants/modelosIA.ts
?? tests/pagos.test.ts
?? videos/promo/snapshots/frame-00.png
{"decision": "approve"}

### H · al lado aparece codigo caro de verdad
{"decision": "block", "reason": "Se tocó código caro sin evidencia observable desde afuera:\n  · Backup (nivel 5): scripts/backup.sh\n  · Login / auth (nivel 5): src/auth/login.ts\n\nNivel 5 significa que un tercero sin interés lo confirma: el cargo en el panel del proveedor, el mail que llegó de verdad, el 401 sin token. Un test propio no alcanza.\n\nOpciones:\n1. Lanzá el subagente `witness` para conseguir la prueba y escribir el acta en PROOF.md.\n2. Si el usuario decide seguir sin probar, registrá la deuda en PROOF.md con su nombre y la fecha. Declararla alcanza para cerrar.\n3. Si el usuario no está (te dejó trabajando solo) y la prueba necesita algo que no tenés, registrá la deuda con --quien \"Claude (a confirmar por <su nombre>)\". Se le muestra al abrir la próxima sesión."}

### I · el agente, solo, declara las dos deudas a confirmar
deuda registrada en <repo>/PROOF.md: src/auth/login.ts — asumida por Claude (a confirmar por Martin) 20/09
deuda registrada en <repo>/PROOF.md: scripts/backup.sh — asumida por Claude (a confirmar por Martin) 04/10
{"decision": "approve"}

### J · parte de arranque de la sesion siguiente
{"systemMessage": "proof-first · 0 actas vigentes\n⏳ te esperan: 2 deudas a confirmar · lo más viejo, de hace 14 días → /proof deuda\n⚠️ src/auth/login.ts — falta una sesion real de admin — deuda asumida por Claude (a confirmar por M…\n⚠️ scripts/backup.sh — no hay donde restaurar — deuda asumida por Claude (a confirmar por Martin) 0…"}

### K · la persona confirma una; la otra sigue esperando; confirmar dos veces falla
deuda confirmada en <repo>/PROOF.md: src/auth/login.ts — por Martin 04/10
proof-first: no hay ninguna deuda «src/auth/login.ts» esperando confirmación en <repo>/PROOF.md
exit=2
{"systemMessage": "proof-first · 0 actas vigentes\n⏳ te esperan: 1 deuda a confirmar → /proof deuda\n⚠️ src/auth/login.ts — falta una sesion real de admin — deuda confirmada por Martin 04/10\n⚠️ scripts/backup.sh — no hay donde restaurar — deuda asumida por Claude (a confirmar por Martin) 0…"}

{"decision": "approve"}

11:- src/auth/login.ts — falta una sesion real de admin — deuda confirmada por Martin 04/10
12:- scripts/backup.sh — no hay donde restaurar — deuda asumida por Claude (a confirmar por Martin) 04/10
### C · acta escrita por la CLI aprueba; al cambiar y commitear el archivo, vence y bloquea
acta escrita en <repo>/PROOF.md: El login rechaza sin token · nivel 5 · cubre 1 archivo(s) · huella 52c0f6
{"decision": "approve"}

{"decision": "block", "reason": "Estas actas quedaron vencidas porque cambiaron los archivos que cubrían:\n  · El login rechaza sin token (cubría src/auth/login.ts)\n\nVolvé a verificarlas con el subagente `witness` y actualizá el acta, o declará la deuda en PROOF.md con quién lo decidió."}

### D · sin git aprueba
{"decision": "approve"}

### E · segunda vuelta (stop_hook_active) aprueba y nombra lo pendiente
{"decision": "approve", "systemMessage": "proof-first: ya frené este turno una vez y no lo vuelvo a frenar. Cierra igual, pero esto quedó sin evidencia y sin deuda declarada:\nEstas actas quedaron vencidas porque cambiaron los archivos que cubrían:\n  · El login rechaza sin token (cubría src/auth/login.ts)"}

### F · acta sin cubre cuyo que es una ruta: rechazada
proof-first: «src/auth/login.ts» parece una ruta de archivo y el acta no cubre ningún archivo. Un acta así nunca vencería: pasá los archivos en --cubre, o nombrá la afirmación en términos humanos ("El login rechaza sin token").
exit=2
```

# El uso real que motivó los arreglos — 05/09 al 04/10/2026

Sale de leer los transcripts que Claude Code guarda de cada sesión
(`~/.claude/projects/*/*.jsonl`): un registro que escribe el harness, no el
agente. Tres proyectos en producción (un CRM propio, un proyecto de cliente y
una comunidad paga).

- **El harness dispara los hooks.** El mensaje de bloqueo de `stop_gate.py`
  aparece como feedback de hook `Stop` en sesiones interactivas de cuatro
  proyectos, entre el 05/09 y el 04/10. Categorías que frenaron: datos de
  usuario, login/auth, backup y cobro.
- **El testigo llegó a ✅ PROBADO** con sistemas y credenciales reales: 39
  lanzamientos entre los dos proyectos más activos, unas 30 actas en sus
  cuadernos, varias de nivel 5 y 6. También refutó: un "cerrar sesión" que no
  revocaba nada (403 tragado en silencio) y una función que respondía a
  cualquiera sin login.
- **Costo medido:** los testigos fueron ~1 % de los tokens de salida y ~3 % de
  la entrada nueva de esas sesiones (mediana: 100–240 mil tokens por testigo,
  casi todo lectura).
- **Falsos positivos:** 74 capturas de video bajo `snapshots/` frenaron como
  *Backup*; un `.md` como *Login*; `modelosIA.ts`, un `.test.ts` y la sonda del
  testigo en `.proof-tmp/` como *Datos de usuario*.
- **El hueco:** seis deudas "asumida por Claude (a confirmar por Martin)",
  escritas de madrugada con la consigna "seguí vos, mañana lo veo", y cuatro
  postergados de tres semanas. Bien anotados; nadie se los mostró a la persona.
