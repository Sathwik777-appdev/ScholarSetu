"""Temporal worker + reconciler. Run: python -m app.workflows.worker

The reconciler starts one SLA workflow per open application and one retry workflow per submitted DBT
retry. Starts are idempotent (fixed workflow ids), so the API never needs Temporal to be up.
"""

import asyncio
import logging

from temporalio.client import Client
from temporalio.common import WorkflowIDConflictPolicy
from temporalio.worker import Worker

from app.config import settings
from app.workflows import activities as acts
from app.workflows.definitions import DBTRetryWorkflow, SLAWorkflow

logging.basicConfig(level=settings.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("scholarsetu.worker")

ACTIVITIES = [acts.sla_snapshot, acts.record_sla_breach, acts.open_sla_applications, acts.submitted_dbt_retries,
              acts.settle_dbt_retry]


async def reconcile(client: Client) -> int:
    started = 0
    for app_id in await acts.open_sla_applications():
        await client.start_workflow(SLAWorkflow.run, app_id, id=f"sla-{app_id}", task_queue=settings.TEMPORAL_TASK_QUEUE,
                                    id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING)
        started += 1
    for retry_id in await acts.submitted_dbt_retries():
        await client.start_workflow(DBTRetryWorkflow.run, retry_id, id=f"dbt-retry-{retry_id}",
                                    task_queue=settings.TEMPORAL_TASK_QUEUE,
                                    id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING)
        started += 1
    return started


async def main() -> None:
    if not settings.TEMPORAL_ADDRESS:
        raise SystemExit("TEMPORAL_ADDRESS is not set")
    client = await Client.connect(settings.TEMPORAL_ADDRESS, namespace=settings.TEMPORAL_NAMESPACE)
    worker = Worker(client, task_queue=settings.TEMPORAL_TASK_QUEUE, workflows=[SLAWorkflow, DBTRetryWorkflow],
                    activities=ACTIVITIES)
    logger.info("worker connected to %s (queue %s)", settings.TEMPORAL_ADDRESS, settings.TEMPORAL_TASK_QUEUE)

    async def reconcile_forever():
        while True:
            try:
                count = await reconcile(client)
                logger.info("reconciled %d workflow(s)", count)
            except Exception:
                logger.exception("reconcile failed")
            await asyncio.sleep(settings.WORKFLOW_RECONCILE_SECONDS)

    tasks = [worker.run(), reconcile_forever()]
    if settings.WORKER_RUNS_BACKGROUND_JOBS:
        # The always-on worker also publishes the outbox to NATS, runs the notification consumers and polls
        # the portals, so the API can be purely request-driven (e.g. Cloud Run scaling to zero).
        from app.main import _poll_portals, _run_event_bus
        stop = asyncio.Event()
        tasks += [_run_event_bus(stop), _poll_portals(stop)]
        logger.info("worker also runs the outbox publisher, notification consumers and portal polling")
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
