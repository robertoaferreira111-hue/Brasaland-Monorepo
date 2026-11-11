# PR evidence — DEV-55 async tasks

## Summary

`POST /reporting/pipeline-runs` enqueues `app.tasks.run_weekly_pipeline` and returns `202` with `{"task_id": "..."}`. The worker runs the weekly ETL in its own process. Redis is the broker. Failed tasks retry with backoff and land in `public.dlq_tasks`. `GET /tasks/{task_id}` reports `pending`, `started`, `success`, or `failure`.

## Endpoint choice

The converted endpoint is `POST /reporting/pipeline-runs`.

That route was the slow call. It ran the weekly ETL on a daemon thread inside the API process. Measured ETL runtimes were 16s to 85s, and Prefect startup on the request thread could poll for up to 180s. The request now publishes `week_start` and `trigger_type` only. `run_id` is created by the worker and is read from `GET /tasks/{task_id}` on success and from `GET /reporting/pipeline-runs/latest`.

## Latency

The API was restarted. The worker was running and no lease was live. Each call waited until that run finished before the next call.

Cold call, reported separately (known first-request cost): **302.2 ms**, task `61169b55-c238-43d9-be08-a48814f44818`.

Throwaway warm-up, not part of the ten: **65.4 ms**.

| # | ms | task_id |
| --- | ---: | --- |
| 1 | 100.9 | `874bd0f6-bdae-4a4b-af17-93d42c651397` |
| 2 | 79.3 | `45b9f7b3-aed9-49d3-b53d-10279dd6f8e1` |
| 3 | 136.3 | `ebcccdc1-1182-4dc2-87de-53f199289132` |
| 4 | 69.8 | `43099a32-38e1-4d0b-8745-9c9436aa8fc0` |
| 5 | 115.4 | `da726939-a816-42ed-9071-3ce11a204a5d` |
| 6 | 105.7 | `8ab1600a-597f-456b-9abf-cf5c0579f2bf` |
| 7 | 70.5 | `2932c81f-b647-44fd-91df-e34814c52840` |
| 8 | 121.9 | `ccdd925c-eb95-4eb8-b51f-5619a52e417e` |
| 9 | 93.4 | `12675f84-87b2-490c-9085-83cba25c071c` |
| 10 | 75.1 | `78cebd83-5199-4703-ac60-bddd345c1595` |

Median **97.15 ms**. Maximum **136.3 ms**. None of the ten exceeded 200 ms.

## Retry log

Worker log for task `026ccb89-a416-4771-83ac-c4f40f767b09` with `BRASALAND_PIPELINE_TASK_FAIL_FOR_TEST=1` set only in that worker process:

```text
18:18:45.267 attempt=1 status=failure duration_ms=0 error=BRASALAND_PIPELINE_TASK_FAIL_FOR_TEST is set
18:18:45.535 retry: Retry in 10s
18:18:55.292 attempt=2 status=failure duration_ms=0 error=BRASALAND_PIPELINE_TASK_FAIL_FOR_TEST is set
18:18:55.317 retry: Retry in 20s
18:19:15.313 attempt=3 status=failure duration_ms=0 error=BRASALAND_PIPELINE_TASK_FAIL_FOR_TEST is set
18:19:15.344 retry: Retry in 40s
18:19:55.329 attempt=4 status=failure duration_ms=0 error=BRASALAND_PIPELINE_TASK_FAIL_FOR_TEST is set
18:19:55.396 raised unexpected: RuntimeError('BRASALAND_PIPELINE_TASK_FAIL_FOR_TEST is set')
```

Gaps between attempts were about 10s, 20s, and 40s. `GET /tasks/{task_id}` stayed `started` with `result` null through the retries, then:

```json
{"task_id": "026ccb89-a416-4771-83ac-c4f40f767b09", "status": "failure", "result": "BRASALAND_PIPELINE_TASK_FAIL_FOR_TEST is set"}
```

The variable was unset, the worker was restarted, and task `1d087b05-9ec6-4042-8091-3a27bc801974` succeeded with `run_id` `10c7536c-75d7-44d2-ac97-2767bf23dbb3`.

## DLQ row

```text
task_id:      026ccb89-a416-4771-83ac-c4f40f767b09
task_name:    app.tasks.run_weekly_pipeline
attempt:      4
error_message: BRASALAND_PIPELINE_TASK_FAIL_FOR_TEST is set
created_at:   2026-11-10 23:19:55.373925+00
```

One row for that `task_id`.

## Status lifecycle

Task `2f25c7da-7957-4136-9324-33a878482d45` was queued while the worker was stopped (`202` in 72.7 ms). The API was restarted. The Redis list `celery` still had length 1, and the status route still returned `pending`. After the worker started:

```json
{"task_id": "2f25c7da-7957-4136-9324-33a878482d45", "status": "pending", "result": null}
{"task_id": "2f25c7da-7957-4136-9324-33a878482d45", "status": "started", "result": null}
{"task_id": "2f25c7da-7957-4136-9324-33a878482d45", "status": "success", "result": {"run_id": "ebc723cd-64b5-4909-aade-d108b573d086", "status": "success"}}
```

## Queue payload

While that task was queued, the Redis list `celery` held one JSON message. The decoded body arguments were `[null, "manual"]` and the kwargs were `{}`. Flower's task page for `78cebd83-5199-4703-ac60-bddd345c1595` showed `SUCCESS`, args `(None, 'manual')`, and kwargs `{}`.

With `FLOWER_UNAUTHENTICATED_API=true` set only on a temporary Flower container, `GET /api/tasks` returned one `SUCCESS` (`c52902b5-db5c-4835-ade0-920fd44bf395`) and one `FAILURE` (`ee298f47-a5f3-4722-8cc6-281e30e3bd45`). Both args were `(None, 'manual')`. The flag was then removed. `/api/tasks` returned 401 again and `GET /` returned 200. Recreating Flower clears its in-memory task list.

## What we will evaluate

- Redis in Docker, workers connected without configuration errors — **verified**. The worker consumed tasks from `brasaland-redis-1`.
- Modified endpoint returns `202` with `task_id` in under 200 ms, regardless of task duration — **verified** for the ten warm calls (median 97.15 ms, maximum 136.3 ms). The cold call was 302.2 ms and is not part of that ten.
- `GET /tasks/{task_id}` returns the status at each moment and the result when available — **verified** (`pending`, `started`, `success`, `failure`).
- Automatic retries use backoff and do not retry immediately — **verified** (10s, 20s, 40s).
- After the retries are exhausted, the task is in the DLQ with `task_id`, attempt, and error message — **verified** (attempt 4, one row).
- The API is a separate process; stopping it does not stop the worker or lose queued messages — **verified**. The queued task survived an API restart and completed after the worker started.
- Queue messages contain only identifiers — **verified** (`null` / `manual` only).
- Flower shows at least one completed task and one failed task — **verified** while the temporary API flag was on. After the flag was removed, Flower's web UI was up and its JSON API returned 401. The in-memory list does not survive recreating the Flower container.

## Follow-ups outside this PR

- `start_pipeline_run` has no caller and was left in place.
- `data/pipelines/PIPELINE_DESIGN.md`, `docs/telemetry/PREFECT_DESIGN.md`, `docs/telemetry/business_metrics.md`, and `company-BRIEFING.md` still describe the old `202` body.

## Screenshots and label

Add the label `async-tasks` to the PR.

Flower screenshots are not in this commit. Take them while Flower has been left running across the tasks (a recreate empties the list):

1. One completed task: open `http://127.0.0.1:5555/task/<success-task-id>` and capture the `SUCCESS` state. Args should be `(None, 'manual')`.
2. One failed or DLQ-bound task: open `http://127.0.0.1:5555/task/<failure-task-id>` and capture the `FAILURE` state.

One view is enough when both states are visible together. The Tasks table at `http://127.0.0.1:5555/tasks` is filled by `/api/tasks`, which returns 401 unless `FLOWER_UNAUTHENTICATED_API` is set on the Flower process. Task detail pages render without that variable. Do not commit the variable. If it is set for a screenshot, remove it afterwards.

## Test plan

- [ ] Warm `POST /reporting/pipeline-runs` returns `202` `{"task_id": "..."}` in under 200 ms.
- [ ] A second call during a live lease returns `409` with `active_run_id`.
- [ ] `GET /tasks/{task_id}` moves through `pending`, `started`, and `success`, and `result.run_id` is set.
- [ ] With the worker stopped, a `202` stays queued across an API restart and completes after the worker starts.
- [ ] With `BRASALAND_PIPELINE_TASK_FAIL_FOR_TEST` set on the worker only, retries wait 10s, 20s, and 40s, and one `dlq_tasks` row is written. Unset the variable and confirm a later run succeeds.
- [ ] Flower shows one `SUCCESS` and one `FAILURE`. Attach those screenshots.
- [ ] The PR has the `async-tasks` label.
