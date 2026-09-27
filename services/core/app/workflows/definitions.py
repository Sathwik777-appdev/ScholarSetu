"""Durable workflows (ARCHITECTURE.md §5.1, §6.3, §6.6). Deterministic: time comes from workflow.now(),
everything else from activities."""

from datetime import datetime, timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from app.workflows import activities as acts

ACTIVITY_TIMEOUT = timedelta(seconds=30)
MAX_TIERS = 3


@workflow.defn
class SLAWorkflow:
    """Watches one application: sleeps until its stage deadline, then records a breach and escalates
    up the officer chain for that stage. Ends when the application leaves the stages that have an SLA."""

    @workflow.run
    async def run(self, application_id: str) -> str:
        tier, watched_since = 0, None
        for _ in range(200):  # bounded history; continue-as-new keeps long waits cheap
            snap = await workflow.execute_activity(acts.sla_snapshot, application_id,
                                                   start_to_close_timeout=ACTIVITY_TIMEOUT)
            if snap["sla_seconds"] is None:
                return "no SLA for current stage"
            if snap["state_changed_at"] != watched_since:  # a new stage: start again from the first tier
                tier, watched_since = 0, snap["state_changed_at"]
            since = datetime.fromisoformat(snap["state_changed_at"])
            deadline = since + timedelta(seconds=snap["sla_seconds"] + tier * snap["escalation_seconds"])
            wait = (deadline - workflow.now()).total_seconds()
            if wait > 0:
                await workflow.sleep(timedelta(seconds=wait))
                continue
            if tier < snap.get("tiers", MAX_TIERS):
                result = await workflow.execute_activity(
                    acts.record_sla_breach, args=[application_id, snap["state"], snap["state_changed_at"], tier],
                    start_to_close_timeout=ACTIVITY_TIMEOUT)
                if result["breached"]:
                    tier += 1
                    continue
            # All tiers reminded: check back after one more escalation interval.
            await workflow.sleep(timedelta(seconds=snap["escalation_seconds"]))
        workflow.continue_as_new(application_id)


@workflow.defn
class DBTRetryWorkflow:
    """Follows a re-submitted payment until PFMS settles it (credited or failed)."""

    @workflow.run
    async def run(self, retry_id: str) -> str:
        delay = 10
        for _ in range(60):
            status = await workflow.execute_activity(acts.settle_dbt_retry, retry_id,
                                                     start_to_close_timeout=ACTIVITY_TIMEOUT)
            if status in (None, "CREDITED", "FAILED"):
                return status or "missing"
            await workflow.sleep(timedelta(seconds=delay))
            delay = min(delay * 2, 600)
        return "still pending after retries"
