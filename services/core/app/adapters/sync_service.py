from pydantic import BaseModel
from app.adapters.nsp_adapter import NSPAdapter
from app.adapters.sfmp_adapter import SFMPAdapter
from app.adapters.nos_adapter import NOSAdapter

class SyncResult(BaseModel):
    student_id: str
    applications_synced: int
    errors: list[str]

class AdapterSyncService:
    """Periodically syncs external system state into the canonical ledger."""
    
    def __init__(self):
        self.adapters = [NSPAdapter(), SFMPAdapter(), NOSAdapter()]
    
    async def sync_student(self, student_id: str) -> SyncResult:
        """Pull latest from all adapters and reconcile with ledger."""
        synced = 0
        errors = []
        for adapter in self.adapters:
            try:
                apps = await adapter.fetch_applications(student_id)
                synced += len(apps)
            except Exception as e:
                errors.append(str(e))
                
        return SyncResult(student_id=student_id, applications_synced=synced, errors=errors)
    
    async def sync_all_active(self) -> list[SyncResult]:
        """Background job: sync all active applications."""
        return []
