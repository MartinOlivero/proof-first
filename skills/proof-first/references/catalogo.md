# El catálogo

Para cada tipo de trabajo: la prueba que vale, la falsa prueba habitual, por
qué esa falsa prueba engaña, y el comando concreto para conseguir la buena.
La columna de la falsa prueba es el corazón pedagógico del plugin — no está
para señalar que está mal, sino para mostrar por qué parece que está bien.

Las diez categorías son **nivel 5**: hace falta un tercero sin interés que lo
confirme (ver la escala en `SKILL.md`).

---

### 1. Cobro / pago — nivel 5

| | |
|---|---|
| ✅ Prueba que vale | El cargo aparece en el panel del proveedor **y** el webhook llegó al servidor |
| ❌ Falsa prueba | El usuario vio la pantalla de "gracias por tu compra" |

**Por qué la falsa prueba engaña:** el redirect de éxito lo dispara el navegador
del cliente, no el proveedor. Se puede llegar a esa pantalla sin que exista
ningún cargo — basta con que el frontend redirija tras el submit del formulario,
falle silenciosamente el paso siguiente, y nadie lo note porque la UX "se ve
bien". Este es el antipatrón que ya figura documentado en el README de
`saas-builder`: un checkout que da por pagado el redirect del cliente.

**Cómo se consigue la buena:**

```bash
# el cargo existe del lado del proveedor
curl -s https://api.stripe.com/v1/charges?limit=1 \
  -u "$STRIPE_SECRET_KEY:" | head -40

# el webhook llegó de verdad al servidor
grep -i "checkout.session.completed" logs/webhook.log | tail -3
```

---

### 2. Login / auth — nivel 5

| | |
|---|---|
| ✅ Prueba que vale | Sesión real desde navegador limpio **+ un acceso no autorizado que es rechazado** |
| ❌ Falsa prueba | Entró el usuario que ya estaba logueado |

**Por qué la falsa prueba engaña:** la pestaña donde se prueba suele arrastrar
la cookie de sesión de una prueba anterior, o de un login manual de hace rato.
Ver contenido protegido no prueba que el flujo nuevo (usuario+contraseña → el
servidor valida → emite token) esté funcionando: puede ser un token viejo que
nunca se invalidó. Y aunque el login ande, si probar solo el caso feliz deja
sin revisar el rechazo, nunca se comprobó la mitad que importa: que alguien
sin credenciales no entra.

**Cómo se consigue la buena:**

```bash
# 1. login real, sin cookies previas (equivalente a una ventana de incógnito)
curl -s -c /tmp/cookies.txt -X POST https://<tu-dominio>/api/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"'"$TEST_PASSWORD"'"}'

# 2. con esa sesión, el recurso protegido responde 200
curl -s -o /dev/null -w "%{http_code}\n" -b /tmp/cookies.txt \
  https://<tu-dominio>/api/privado/perfil

# 3. sin ninguna cookie/token, el mismo recurso tiene que rechazar
curl -s -o /dev/null -w "%{http_code}\n" https://<tu-dominio>/api/privado/perfil
# tiene que imprimir 401 (o 403), no 200
```

---

### 3. Guardar datos — nivel 5

| | |
|---|---|
| ✅ Prueba que vale | La fila está en la base, consultada **por fuera de la app** |
| ❌ Falsa prueba | La pantalla muestra el dato |

**Por qué la falsa prueba engaña:** muchos formularios actualizan el estado
local (un `array` en memoria, un "optimistic update" de React) antes de que la
escritura al servidor termine, o incluso si esa escritura falla. La pantalla
muestra el dato correcto porque el navegador ya sabe lo que escribiste — no
porque haya esperado confirmación de que la base lo guardó.

**Cómo se consigue la buena:**

```bash
# postgres
psql "$DATABASE_URL" -c "select * from usuarios where email='test@example.com';"

# sqlite
sqlite3 datos.db "select * from usuarios where email='test@example.com';"

# o el endpoint de administración, no el de la app que se acaba de tocar
curl -s https://<tu-dominio>/api/admin/usuarios?email=test@example.com \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

### 4. Borrar datos — nivel 5

| | |
|---|---|
| ✅ Prueba que vale | El dato **ya no está**, consultado por fuera |
| ❌ Falsa prueba | Desapareció de la pantalla |

**Por qué la falsa prueba engaña:** mismo mecanismo que en "guardar", al
revés. La UI puede filtrar el elemento borrado de la lista local (un `filter`
sobre el state) sin que el `DELETE` al servidor haya llegado a confirmarse, o
incluso sin haberse disparado. Además, un borrado lógico (un flag
`eliminado=true`) también hace desaparecer el dato de la pantalla sin que la
fila deje de existir en la base — que puede o no ser lo que efectivamente se
pidió.

**Cómo se consigue la buena:**

```bash
# misma query que la categoría anterior, esperando vacío
psql "$DATABASE_URL" -c "select * from usuarios where email='test@example.com';"
# 0 filas si es borrado físico; si es lógico, confirmar el flag explícitamente:
psql "$DATABASE_URL" -c "select eliminado from usuarios where email='test@example.com';"
```

---

### 5. Permisos / multi-tenant — nivel 5

| | |
|---|---|
| ✅ Prueba que vale | El usuario B **no puede** ver lo de A |
| ❌ Falsa prueba | El usuario A ve lo suyo |

**Por qué la falsa prueba engaña:** que el dueño vea sus propios datos solo
confirma que el filtro "mostrame lo mío" funciona — no dice nada sobre si ese
mismo filtro también bloquea a otro. Un `WHERE user_id = ?` bien puesto en la
consulta de A puede convivir tranquilamente con un endpoint que no lo aplica,
o con un ID adivinable en la URL que cualquiera puede cambiar. Es la prueba
que un desarrollador rara vez escribe solo, porque no es el camino feliz.

**Cómo se consigue la buena:**

```bash
# sesión de A: crea o consulta un recurso propio, anotá su ID
curl -s -b cookies_a.txt https://<tu-dominio>/api/proyectos/123

# sesión de B (login separado, cookies distintas): pide el recurso de A por ID
curl -s -o /dev/null -w "%{http_code}\n" -b cookies_b.txt \
  https://<tu-dominio>/api/proyectos/123
# tiene que imprimir 403 (o 404), no 200
```

---

### 6. Mails / notificaciones — nivel 5

| | |
|---|---|
| ✅ Prueba que vale | El mensaje llegó a una casilla real y se puede abrir |
| ❌ Falsa prueba | La API devolvió `200 OK` |

**Por qué la falsa prueba engaña:** un `200` del proveedor (Resend, SendGrid,
Twilio) confirma que el proveedor **aceptó** el pedido de envío — no que lo
**entregó**. Entre la aceptación y la bandeja de entrada hay filtros de spam,
un dominio sin SPF/DKIM bien configurado, una dirección inválida, un rate
limit silencioso. El proveedor puede devolver éxito y el mensaje no llegar a
nadie.

**Cómo se consigue la buena:**

```bash
# casilla de prueba real: abrir el mensaje y pegar remitente + asunto + fecha,
# no un resumen de que "llegó bien"

# o el log de entrega del proveedor, que distingue "aceptado" de "entregado"
grep -i "email.delivered\|delivery" logs/resend.log | tail -3
```

---

### 7. Deploy / publicación — nivel 5

| | |
|---|---|
| ✅ Prueba que vale | `curl` al dominio público **desde fuera de la máquina**, con la versión nueva |
| ❌ Falsa prueba | Anda en localhost / el build pasó |

**Por qué la falsa prueba engaña:** `localhost` corre contra el código local,
con las variables de entorno locales, sin el proxy/CDN/build de producción en
el medio. Que el build "pase" solo confirma que el compilador no encontró
errores de sintaxis — no que ese artefacto llegó al servidor que atiende al
público, ni que ese servidor esté sirviendo la versión nueva y no una copia
cacheada de la anterior.

**Cómo se consigue la buena:**

```bash
# el dominio público responde, desde fuera de la máquina que hizo el deploy
curl -sI https://<tu-dominio> | grep -i "^http\|last-modified\|etag"

# comparar la versión servida contra la que se acaba de subir
curl -s https://<tu-dominio> | grep -o 'build-[a-f0-9]*'
```

---

### 8. Tarea automática / cron — nivel 5

| | |
|---|---|
| ✅ Prueba que vale | Corrió **sola**, a su hora, sin nadie mirando, y dejó log |
| ❌ Falsa prueba | Corrió cuando se la ejecutó a mano |

**Por qué la falsa prueba engaña:** ejecutar el script a mano prueba que el
**código** funciona, no que el **scheduler** lo dispara. Puede fallar por una
zona horaria mal configurada, el proceso que agenda la tarea caído, permisos
de usuario distintos a los tuyos, o una variable de entorno que existe en tu
shell pero no en el entorno donde corre el cron. Ninguna de esas fallas
aparece cuando lo corrés vos mismo.

**Cómo se consigue la buena:**

```bash
# esperar a que pase la hora programada sin tocar nada, después leer el log
tail -20 /var/log/mi-tarea.log
grep -i "$(date +%Y-%m-%d)" /var/log/mi-tarea.log

# si corre en n8n: revisar el historial de ejecuciones del workflow,
# filtrando por trigger "schedule" y confirmando el timestamp real
```

---

### 9. Integración externa — nivel 5

| | |
|---|---|
| ✅ Prueba que vale | Respuesta real de la API del tercero, en producción |
| ❌ Falsa prueba | El mock devolvió lo esperado |

**Por qué la falsa prueba engaña:** el mock lo escribió el mismo agente (o
vos), basado en la documentación o en una suposición de cómo responde la API
real. Si esa suposición está mal —un campo que cambió de nombre, un rate
limit, una versión de API distinta a la documentada, credenciales de sandbox
con permisos distintos a las de producción— el mock sigue devolviendo "éxito"
mientras la integración real está rota. El mock prueba que el código maneja
bien lo que se creyó que la API devuelve, no lo que la API devuelve.

**Cómo se consigue la buena:**

```bash
# llamada real, con credenciales de producción, sin mockear nada
curl -s https://api.<proveedor>.com/<endpoint-documentado> \
  -H "Authorization: Bearer $PROVEEDOR_API_KEY" | python3 -m json.tool
# pegar la respuesta cruda, no un resumen de que "vino bien"
```

---

### 10. Backup — nivel 5

| | |
|---|---|
| ✅ Prueba que vale | **Una restauración probada** |
| ❌ Falsa prueba | El backup existe |

**Por qué la falsa prueba engaña:** que el archivo esté ahí, y pese lo que
tiene que pesar, mide que el *proceso de backup se ejecutó* — no que ese
archivo sea *restaurable*. Un dump corrupto, generado con un usuario sin
permisos sobre alguna tabla, con una versión de la herramienta incompatible
con la del restore, o cortado a la mitad por quedarse sin disco, también
"existe" y pesa parecido. Es la falsa prueba más cara del catálogo, porque se
descubre el único día en que importa: cuando ya se perdieron los datos
originales y el backup es lo único que queda.

**Cómo se consigue la buena** (ejemplo con Postgres — adaptar al motor real):

```bash
# 1. levantar una base descartable, separada de la real
createdb backup_test

# 2. restaurar el backup ahí, nunca sobre producción
pg_restore -d backup_test /ruta/al/ultimo_backup.dump
# si es un dump plano en vez de formato custom:
# psql backup_test < /ruta/al/ultimo_backup.sql

# 3. verificar que los datos están, con una query concreta
psql backup_test -c "select count(*) from usuarios;"

# 4. borrar el entorno descartable
dropdb backup_test
```

---

## Notas

- La entrada #10 (Backup) es la falsa prueba más cara que existe, porque se
  descubre el único día en que importa.
- La entrada #1 (Cobro / pago) — "un checkout que da por pagado en el redirect
  del cliente" — ya figura como antipatrón en el README de `saas-builder`.
- El catálogo es fijo en v1: las diez filas no se extienden por proyecto
  todavía. La extensión vía `.proof-catalog.md` está diseñada pero se
  implementa en v1.1.
