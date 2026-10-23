# proof-first

**Your agent said it works. Who checked?**

> The rule: never trust the agent's report, only an artifact you can observe
> from outside the agent. A green test suite is the agent grading its own
> homework. A charge appearing in the Stripe dashboard is not.

<details>
<summary>🇪🇸 <strong>¿Hablás español?</strong> — resumen rápido</summary>

<br>

**proof-first** aplica una sola regla: nunca confiar en el reporte del
agente, solo en un artefacto observable desde afuera de él. Un test verde
escrito por el mismo agente que escribió el código es el alumno corrigiendo
su propio examen; un cargo real en el panel de Stripe, no.

Cuando el turno tocó código caro — plata, login, datos de usuario, permisos,
deploy, mails, backup, tareas programadas o una integración externa — el hook
`Stop` frena el cierre si no hay evidencia de nivel 5 (un tercero sin interés
que lo confirme) registrada en `PROOF.md`. El hook es un detector determinista
por ruta de archivo, no un modelo que opina: por eso mismo solo ve ocho de las
diez categorías del catálogo (integraciones externas no tiene una huella de
archivo confiable) y pide `/proof` a mano para esa. La válvula de escape:
declarar la deuda en `PROOF.md`, con quién la asumió y cuándo, alcanza para
cerrar el turno. No hay forma de esquivar la pregunta — sí de responderla con
sinceridad.

El subagente `witness` es quien sale a buscar la prueba: arranca sin el
contexto de cómo se construyó el código, con la consigna invertida
("demostrá que esto NO funciona") y sin herramienta de escritura: lo único que
puede escribir es el acta, corriendo el comando `lib/cuaderno.py` que le llega
con su ruta absoluta en el prompt.

**Lo que se commitea dentro del turno también cuenta** (desde la 1.1). Hasta la
1.0 el detector leía solo `git status`, y un commit a mitad de turno se llevaba
el cambio caro fuera de su vista. Se creía un caso raro; el uso real dijo otra
cosa: en un proyecto en producción, 58 de 70 archivos caros commiteados en tres
semanas —el webhook de Stripe, en seis commits de un mismo día— pasaron sin
que el hook nombrara ninguno. Ahora el hook guarda el `HEAD` al abrir la sesión
y cada vez que deja cerrar un turno, y suma lo commiteado desde ahí. Si esa
marca no existe (una sesión abierta antes de actualizar), vuelve a mirar solo
`git status`.

**Pasar la segunda vuelta deja rastro** (desde la 1.1). Cuando el agente ignora
el freno, el hook lo deja cerrar igual —nunca te encierra—, pero ahora anota lo
pendiente en `⬜ ABIERTO` con la leyenda *el turno cerró sin prueba ni deuda
declarada*. No cuenta como deuda (no destraba nada) y encabeza el parte de la
próxima sesión. Antes ese aviso salía solo por pantalla, y en tres semanas de
uso real unos quince turnos cerraron así sin dejar nada escrito.

**Sin git, el hook nunca bloquea *por código detectado*: aprueba siempre**,
porque no puede saber qué archivo se tocó — pero un 🔴 BLOQUEANTE escrito a
mano en `PROOF.md` frena igual, con o sin git, porque esa es una decisión de
una persona, no una inferencia sobre un diff. **Sin hooks, la skill sigue
funcionando igual**: el criterio vive ahí completo, los hooks solo lo vuelven
obligatorio.

**Si dejás al agente trabajando solo** ("seguí vos, mañana lo veo"), lo que no
pueda probar sin vos queda como deuda firmada `Claude (a confirmar por <tu
nombre>)`, y al abrir la sesión siguiente el parte arranca con
`⏳ te esperan: 6 deudas a confirmar · 4 postergados · lo más viejo, de hace 24
días → /proof deuda`. Desde ahí las mandás a probar o las asumís vos.

Las dos cosas que la 1.0.0 declaraba sin probar — que Claude Code dispare los
hooks en una sesión viva, y que el testigo llegue a ✅ PROBADO contra un sistema
real — las contestó un mes de uso en tres proyectos en producción. Los números,
los falsos positivos que aparecieron y lo que costó en tokens están en
[`docs/evidencia/uso-real-2026-10.md`](docs/evidencia/uso-real-2026-10.md).

Instalación:

```bash
/plugin marketplace add MartinOlivero/proof-first
/plugin install proof-first
```

Hecho por **Martín Olivero / [IamAutom](https://iamautom.com)**.

</details>

## The problem

An agent writes code faster than a human can read it. The bottleneck stopped
being *writing* — it's *verifying*. When the agent says "done, the payment
works now," that sentence isn't evidence: it's a claim from the same party
that did the work. And the usual way to "verify" it — a green test the same
agent wrote — is the student grading their own exam. It always passes.

Existing methods don't close this gap. Spec-Driven Development orders *what*
to build, but a prose spec isn't machine-verifiable — someone still has to
read it and judge. TDD produces tests, but if the agent that wrote the code
also wrote the test, they share the same assumptions and the same blind
spots. Neither answers the question that matters once the system is actually
running: **does this that claims to work, work, from the outside?**

## The scale

One axis orders everything: **the distance between who claims and who
checks.**

| Level | What it is | Who checks |
|:---:|---|---|
| 0 | "Done, it's implemented" | Nobody. It's a claim. |
| 1 | Shows the code it wrote | Nobody. Showing isn't proving. |
| 2 | Green test written by the same agent | The builder. Self-approved. |
| 3 | Pre-existing test, or written by the verifier | Someone else. |
| 4 | The thing running: a screenshot, a log, a `curl` | The machine. The fact, not the account of it. |
| 5 | A disinterested third party confirms it | Stripe, the mail server, DNS. |
| 6 | A real person used it and it worked | Reality. |

0 through 2 is trusting. 3 and up is checking.

## The rule

```
Money, auth, user data, permissions, deploy, messages, backup,
cron, external integrations
    → level 5 or it isn't done
Everything else
    → level 4 is enough
```

**The more expensive it is to be wrong, the further the proof has to stand
from the agent.** All ten categories below are level 5.

## The catalogue

For each kind of work: the proof that counts, and the false proof usually
accepted instead — the ❌ column is the one people screenshot and share,
because it's the one that looks fine until it isn't. Full detail, commands
included, in [`skills/proof-first/references/catalogo.md`](skills/proof-first/references/catalogo.md).

| # | Category | ✅ Proof that counts | ❌ False proof |
|---|---|---|---|
| 1 | Charge / payment | The charge exists on the provider's dashboard **and** the webhook reached the server | The user saw the "thanks for your purchase" screen |
| 2 | Login / auth | Real session from a clean browser **+ an unauthorized request that gets rejected** | The already-logged-in user got in |
| 3 | Saving data | The row is in the database, queried **from outside the app** | The screen shows the value |
| 4 | Deleting data | The row **is gone**, queried from outside | It disappeared from the screen |
| 5 | Permissions / multi-tenant | User B **cannot** see user A's data | User A can see their own data |
| 6 | Mail / notifications | The message landed in a real inbox and opens | The API returned `200 OK` |
| 7 | Deploy / release | `curl` to the public domain **from outside the machine**, on the new version | It works on localhost / the build passed |
| 8 | Scheduled task / cron | It ran **on its own**, on time, unattended, and logged it | It ran when triggered by hand |
| 9 | External integration | Real response from the third-party API, in production | The mock returned what was expected |
| 10 | Backup | **A tested restore** | The backup file exists |

## What it does

- **The `Stop` hook** (`hooks/stop_gate.py`) is a plain command hook — no
  model, no judgment call. It's a deterministic detector: it reads `git
  status` for uncommitted changes, plus whatever was committed since the
  last time it let a turn close, and matches their paths against the
  catalogue's patterns (`lib/deteccion.py`) — separately, it also recomputes
  the fingerprint of every file a proven *acta* covers, committed or not, so
  an acta expires the moment its code changes, whether or not that change is
  staged. It catches **eight of the ten**
  categories this way — payment, auth, permissions, deploy, messages, backup,
  scheduled tasks, and a single `datos` key that covers *saving* and
  *deleting* user data together (catalogue entries #3 and #4 — the same
  files, migrations and schemas, trigger both). **External integrations
  (#9) has no reliable file signature** — it can live in any module that
  calls a third-party API — so the hook can't catch it on its own; that one
  needs a person to ask for it with `/proof`. That's a declared limit, not a
  silent hole: a hook that's honest about what it can't see beats one that
  looks like it covers more than it does.
- **The `witness` subagent** (`agents/witness.md`) is who actually goes and
  gets the proof. It starts with no memory of how the code was built, works
  under an inverted instruction — *prove this does NOT work* — and has no
  `Write` tool at all: the one write it can make is running `lib/cuaderno.py`,
  the command that records the acta in `PROOF.md`. It receives the catalogue
  row for its category, and the absolute path to that command, in the prompt;
  it never opens the catalogue file itself, and never guesses the path.
- **`PROOF.md`** (`lib/cuaderno.py`) is the log at the project root, checked
  into git so a third party can audit it. What's proven gets an *acta* with
  the proof's *coordinate* (a charge ID, a status code, a user ID) — never a
  copy, because copies rot too — and a fingerprint (`lib/huella.py`) over the
  files it covers, so the acta expires on its own the moment those files
  change again. What's knowingly left unproven gets a debt entry instead,
  with who decided that and when.
- **The escape valve** is what makes the hook usable at all: it can't be
  dodged, but it can be answered. Declaring the debt in `PROOF.md` — who
  decided to skip the proof, and the date — is enough to close the turn.
  Without that valve the hook would be unbearable and get uninstalled by day
  two, and an uninstalled plugin protects nothing.

## Install

```bash
/plugin marketplace add MartinOlivero/proof-first
/plugin install proof-first
```

Then just work normally. The `proof-first` skill activates on its own
whenever the conversation is about verifying something works; the `Stop`
hook (every turn) and the session-start report (on startup and resume) need
nothing further once the plugin is installed. Ask on demand with `/proof` (status, or
`/proof <a claim>` to send `witness` after one specific thing).

## How it degrades

- **No git in the project:** the hook can't tell which files changed, so it
  never blocks *on that basis* — it approves. An explicit 🔴 `BLOQUEANTE`
  entry someone wrote into `PROOF.md` still blocks either way, git or not,
  because that's a person's decision, not an inference from a diff. This is
  a deliberate trade-off: a false approve on undetectable changes is
  recoverable, a false block on a project the hook can't reason about isn't.
- **Commits made during the turn count too (since 1.1):** up to 1.0 the
  detector only read `git status`, so a commit mid-turn took the expensive
  change out of its view. Real usage showed this was the common case, not the
  rare one: in one production project, 58 of 70 expensive files committed
  over three weeks — the Stripe webhook among them, six commits in one day —
  went through without the hook naming any. The hook now records `HEAD` at
  session start and every time it lets a turn close, and adds whatever was
  committed since. With no such mark (a session opened before upgrading) it
  falls back to `git status` alone.
- **Getting through on the second pass leaves a trace (since 1.1):** the hook
  still never locks you in, but what was left unproven is now written to
  `⬜ ABIERTO` as *the turn closed with no proof and no declared debt*. It
  doesn't count as debt (it unblocks nothing) and it heads the next session's
  report. Before, that warning only went to the screen.
- **A first block that feels wrong:** the detector matches file *paths*
  against broad patterns — `models`, `job`, `schedule`, `token` — so an
  ordinary file can trip it (`src/models/Button.tsx`, `lib/job-queue-ui.ts`).
  Since 1.0.1 it skips what never ships: images, video, docs (`.md`, `.pdf`),
  test files and the witness's own `.proof-tmp/` scratch folder.
  That's the design, not a bug: it's tuned to ask too often rather than let a
  broken charge through, and one line of declared debt closes the turn. If a
  pattern keeps firing on the same harmless file, that's what the debt entry
  is for.
- **No hooks at all** (a CLI that doesn't support them, or the plugin's hook
  disabled): the `proof-first` skill still works exactly the same. The
  criterion — the scale, the rule, the catalogue — lives entirely in
  `skills/proof-first/SKILL.md`; the hook only adds *obligation* on top of a
  method that already stands on its own.

## Where it fits

| Method | What it covers |
|---|---|
| **SDD** (Spec-Driven Development) | Orders *what* to build. A prose spec still needs a human to read and judge it — it doesn't verify anything once the system runs. |
| **TDD** | Produces tests, but level 2 on the scale above when the same agent writes the test and the code: they share assumptions and blind spots. |
| **RDD** (Receipt-Driven Development, from [gentle-ai](https://github.com/Gentleman-Programming/gentle-ai)) | Reviews the *frozen code candidate* — a very elaborate level 3. It never leaves the code to check the world; proof-first exists to make that trip, out to level 5. |
| **[engram](https://github.com/Gentleman-Programming/engram)** | A searchable history across sessions and projects. `PROOF.md` is this project's present, versioned state, not a long-term memory store — complementary, not overlapping. |
| **[Superpowers](https://github.com/obra/superpowers)** | Supplies process — brainstorming, TDD, debugging, plans. Its testing rung is TDD, which is level 2 when the same agent writes code and test. Complementary: proof-first adds the trip outside. |
| **[`saas-builder`](https://github.com/MartinOlivero/saas-builder)** (same author) | Builds the product. Its own README leaves the gap on purpose — its coverage table has a "Dev process — brainstorm, TDD, debug, git, review" row reading *"Superpowers owns this (not duplicated)"* — and what Superpowers puts there is TDD — level 2. `proof-first` is the optional companion that covers what's expensive to get wrong. |

Each row is a claim about someone else's project, so the links are there to be
checked — in a README arguing that an unsourced claim is level 0, they're the
minimum.

None of these compete with proof-first — none of them answer "does this,
which claims to work, work, from the outside?" That question is this
plugin's whole job.

## Proven against its own rule

`PROOF.md` in this repo is `proof-first` applied to itself, as two separate
actas written through `lib/cuaderno.py` — the hook evidence and the witness
evidence are different claims, over different files, so they aren't lumped
into one:

- **The `Stop` hook**, invoked exactly as Claude Code invokes it (a JSON
  payload on stdin, the decision read back on stdout), was put through five
  situations: it blocks on untested auth code with no acta; it approves once
  the debt is declared in `PROOF.md` — written by the same `cuaderno.py`
  command the witness runs; it blocks again once that acta's fingerprint
  expires from a change that got committed; it approves unconditionally with
  no git at all; and with `stop_hook_active` set it approves even while
  something is still unproven, naming it instead of trapping the turn. These
  are situations the hook was exercised in — not literally "the scenarios"
  from the design spec: two of them (no git, the anti-loop) aren't on that
  list, and the spec's own second scenario is the witness, covered next as its
  own claim.
- **The `witness` subagent** was run twice for real — by hand, by the
  project's controller, outside the plugin's own machinery (the plugin has
  never fired inside a live Claude Code session; that's the open item right
  below) — reaching two of its three possible verdicts. Against a Stripe
  webhook whose handler was an empty `TODO`, it returned **❌ REFUTADO**,
  pasted the source in raw, and found — unprompted — that the webhook
  signature was never verified either. Against the same webhook fixed but
  with no credentials, server, or logs, it returned **⚠️ NO VERIFICABLE**,
  with the raw Stripe permission error and five concrete things missing and
  who has to supply each — it did not fabricate a payment or a log just to
  reach "verified." Both runs demonstrate the same contract: an inverted
  instruction (told to disprove, not confirm), the raw artifact instead of a
  summary, no invention, no hands (nothing edited but `PROOF.md`), and
  working from its catalogue row instead of opening the catalogue itself.
  Both runs, and the hook's situations, are written up in
  [`docs/evidencia/`](docs/evidencia/) — reports by the person who ran them,
  quoting the commands and the tool output verbatim, not literal session
  transcripts. `PROOF.md`'s coordinates point there, not at anything
  gitignored.

**What 1.0.0 declared unexercised, and what answered it:** whether Claude Code
really fires these hooks in a live session, and whether the witness ever
reaches **✅ PROBADO** against a real system. A month of use on three
production projects settled both — the hook's block message shows up in the
harness's own session transcripts, and the witness wrote some thirty actas with
real credentials (and refuted a logout that revoked nothing). It also cost
about 1% of those sessions' output tokens. The numbers, the false positives it
surfaced and the fixes they led to (1.0.1) are in
[`docs/evidencia/uso-real-2026-10.md`](docs/evidencia/uso-real-2026-10.md).

## License

[MIT](./LICENSE) — Copyright © 2026 Martín Olivero / IamAutom.
