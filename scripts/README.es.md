# Carpeta `scripts`

Esta carpeta contiene **scripts auxiliares** del monorepo: automatizaciones de desarrollo, utilidades de mantenimiento, tareas repetitivas (setup, lint, migraciones, generación de datos, etc.) y tooling interno.

- **Propósito principal**: agrupar herramientas de soporte que no pertenecen a una app/agente/pipeline específico, pero facilitan el trabajo del equipo.
- **Recomendación**: documenta cada script (qué hace, parámetros, requisitos, ejemplos de uso) y procura que sean reproducibles (y seguros) en distintos entornos.

## Exportación nocturna de telemetría

`nightly_export.py` es un proceso aparte de la API FastAPI. Exporta un día UTC de `public.telemetry_events` a `data/raw/telemetry_YYYY-MM-DD.csv` y después ejecuta `data/pipelines/pipeline.py`. El horario está en [`nightly_export.crontab`](./nightly_export.crontab).

Cron lleva el reloj. Un planificador dentro del proceso de la API se detendría con la API y ataría la exportación a un worker de peticiones. El crontab arranca el script a las 02:00 UTC aunque la API no esté en marcha. `CRON_TZ=UTC` mantiene esa hora en UTC en las implementaciones de cron que lo respetan. Si el anfitrión ignora `CRON_TZ`, convierte las 02:00 UTC a la hora local de ese anfitrión. La fecha del script no usa la zona del anfitrión: sin `TARGET_DATE`, el día es ayer en UTC.

El crontab no guarda credenciales. Copia [`nightly_export.env.example`](./nightly_export.env.example) a `$HOME/.config/brasaland/nightly_export.env` y define allí `DATABASE_URL` y un `PATH` que incluya `uv`. El crontab carga ese archivo con `set -a` y `.`. La salida se añade a `$HOME/Library/Logs/brasaland-nightly_export.log`.

Instalar la línea en el crontab real es opcional. El comando del archivo es el que hay que ejecutar.

Una muerte forzada (`SIGKILL`) no recorre el camino de fallo del script. El índice único parcial bloquea las ejecuciones siguientes mientras una fila siga en `processing`. Quien opera la base la libera así:

```sql
update public.job_runs
set status = 'failed',
    finished_at = now(),
    error_message = 'operator release after a hard kill left this row processing'
where job_name = 'nightly_export'
  and status = 'processing';
```

No hay caducidad automática.

### Pruebas

`services/api` solo recoge su propio directorio `tests/`. Desde la raíz del repositorio, con `DATABASE_URL` definido para las suites que abren Postgres:

```bash
(cd services/api && uv run pytest)
uv run --project services/api pytest services/job_runner/tests
uv run --project services/api pytest scripts/tests
```
