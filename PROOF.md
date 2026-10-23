# PROOF

Cuaderno de obra. Lo vivo arriba, lo probado plegado abajo.
Generado y mantenido por proof-first.

## 🔴 BLOQUEANTE

## ⬜ ABIERTO

## ⚠️ HECHO SIN PROBAR
- hooks/session_report.py — el detector lo marca como auth por el token 'session' en el nombre (falso positivo de su propio catálogo); su evidencia son sus autochequeos, nivel 3, y no hay nivel 5 posible para un parte de arranque — deuda asumida por el implementador de la ronda de arreglos previa al merge 27/08
- hooks/hooks.json — el matcher de SessionStart sumó clear|fork para que la marca exista también tras /clear; las corridas lo simulan por stdin, pero falta verlo en una sesión viva: abrir una sesión en un repo, hacer /clear y ver que aparezca .git/proof-first/marca-<id nuevo> — deuda asumida por Claude (a confirmar por Tincho) 23/10

## ⏸️ POSTERGADO

<details>
<summary>▸ PROBADO (4)</summary>

✅ 27/08 · El testigo (witness), corrido a mano por el controlador, en dos casos reales: REFUTADO y NO VERIFICABLE · nivel 4
   prueba: Corrido a mano por el controlador, fuera de la maquinaria del plugin — caso 1: "VEREDICTO DEVUELTO: ❌ REFUTADO" sobre "// TODO: marcar el pedido como pagado", hallazgo propio: firma del webhook nunca verificada · caso 2: "VEREDICTO DEVUELTO: ⚠️ NO VERIFICABLE", "Error: Your API key does not have the required permissions for 'GetCharges'.", listó 5 cosas concretas y quién las provee — el reporte de cada corrida, con los comandos y las salidas citados literales (no una transcripción de la sesión), en docs/evidencia/witness-run-1.md y docs/evidencia/witness-run-2.md
   cubre: agents/witness.md · huella: d0166b

✅ 04/10 · Claude Code dispara los hooks Stop en sesiones interactivas reales · nivel 5
   prueba: Transcripts que escribe el harness (~/.claude/projects/*/*.jsonl), leídos el 04/10: el texto de bloqueo de stop_gate.py figura como feedback de hook Stop en sesiones de cuatro proyectos entre el 05/09 y el 04/10 (categorías datos, auth, backup y cobro). Lo leyó un agente, no una persona: por eso 5 y no 6. SessionStart no deja rastro en el transcript y no se verificó por esta vía — resumen en docs/evidencia/uso-real-2026-10.md
   cubre: hooks/hooks.json · huella: 5d3ccd

✅ 04/10 · El testigo llega a PROBADO contra sistemas reales con credenciales reales · nivel 5
   prueba: 39 lanzamientos de proof-first:witness en los transcripts de dos proyectos en producción (23 y 16), unas 30 actas en sus PROOF.md, varias de nivel 5 y 6; también refutó (un logout que no revocaba la sesión). Los cuadernos son de proyectos privados y no se publican — resumen en docs/evidencia/uso-real-2026-10.md
   cubre: agents/witness.md · huella: d0166b

✅ 23/10 · El hook Stop y el parte de arranque en catorce situaciones reales, incluido lo commiteado dentro del turno (1.1) · nivel 4
   prueba: Corridas fuera de los autotests, con el JSON del harness por stdin sobre repos temporales: L frena el webhook de cobro commiteado con git status vacío · M la segunda vuelta aprueba y lo anota en ABIERTO · N la sesión nueva abre con '⏳ te esperan: 1 cerrado sin prueba' · O otra sesión no hereda la marca · P src/sesión.ts frena como auth (la primera corrida la refutó) · G H D I J K C F como en la 1.0.1 — guion en docs/evidencia/correr-1.1.sh, salidas literales en docs/evidencia/uso-real-2026-10-23.md; además, repetido sobre la historia real de un proyecto en producción nombra el webhook de Stripe que la 1.0 dejó pasar
   cubre: hooks/stop_gate.py, hooks/session_report.py, lib/deteccion.py, lib/cuaderno.py, lib/huella.py, hooks/hooks.json · huella: 5b0a4d

</details>
