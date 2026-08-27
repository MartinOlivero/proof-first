# PROOF

Cuaderno de obra. Lo vivo arriba, lo probado plegado abajo.
Generado y mantenido por proof-first.

## 🔴 BLOQUEANTE

## ⬜ ABIERTO
- El tercer veredicto del testigo, PROBADO, no se ejercitó: hace falta un sistema real corriendo con credenciales reales — es el mismo hueco de nivel 6 de abajo, no uno nuevo.
- Confirmar que Claude Code dispara los hooks Stop y SessionStart de este plugin en una sesión interactiva real (nivel 6) — la evidencia de abajo prueba la lógica del script del hook Stop invocándolo con el mismo contrato JSON que usa el harness, no que el harness lo dispare de verdad. Pendiente de una persona, en su propia sesión de Claude Code. Es el umbral entre "listo para mergear" y "listo para publicar" (spec §13).

## ⚠️ HECHO SIN PROBAR
- hooks/session_report.py — el detector lo marca como auth por el token 'session' en el nombre (falso positivo de su propio catálogo); su evidencia son sus autochequeos, nivel 3, y no hay nivel 5 posible para un parte de arranque — deuda asumida por el implementador de la ronda de arreglos previa al merge 27/08

## ⏸️ POSTERGADO
- Ver el código caro que ya se commiteó dentro del mismo turno — hoy el detector lee `git status`, así que un cambio caro commiteado a mitad de turno sale de su vista y el hook aprueba. Un acta que ya cubría ese archivo SÍ sigue venciendo bien: la huella se recalcula del archivo, commiteado o no. El hueco es solo para código caro que nunca tuvo acta. Taparlo pide guardar el HEAD en SessionStart para que Stop compare contra eso: es diseño nuevo, no una corrección — postergado a v1.1 por decisión del controlador, 27/08

<details>
<summary>▸ PROBADO (2)</summary>

✅ 27/08 · El hook Stop en seis situaciones reales (no las de la spec §13) · nivel 4
   prueba: A bloquea sobre una carpeta src/auth/ nueva y entera en un repo con historia, reason incluye "Login / auth (nivel 5): src/auth/login.ts" · B aprueba con la deuda declarada por la CLI de cuaderno.py · C acta escrita por esa misma CLI, aprueba, y tras cambiar y commitear el archivo vuelve a bloquear con "quedaron vencidas porque cambiaron los archivos que cubrían" · D aprueba sin git · E con stop_hook_active aprueba y nombra lo que quedó sin probar · F rechaza el acta sin cubre cuyo que es una ruta — las 6 corridas completas, crudas, en docs/evidencia/hook-runs.md
   cubre: hooks/stop_gate.py, lib/deteccion.py, lib/cuaderno.py, lib/huella.py · huella: e1d6cd

✅ 27/08 · El testigo (witness), corrido a mano por el controlador, en dos casos reales: REFUTADO y NO VERIFICABLE · nivel 4
   prueba: Corrido a mano por el controlador, fuera de la maquinaria del plugin — caso 1: "VEREDICTO DEVUELTO: ❌ REFUTADO" sobre "// TODO: marcar el pedido como pagado", hallazgo propio: firma del webhook nunca verificada · caso 2: "VEREDICTO DEVUELTO: ⚠️ NO VERIFICABLE", "Error: Your API key does not have the required permissions for 'GetCharges'.", listó 5 cosas concretas y quién las provee — el reporte de cada corrida, con los comandos y las salidas citados literales (no una transcripción de la sesión), en docs/evidencia/witness-run-1.md y docs/evidencia/witness-run-2.md
   cubre: agents/witness.md · huella: d0166b

</details>
