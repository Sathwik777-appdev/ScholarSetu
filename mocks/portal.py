"""Generic mock for the three scholarship portals (NSP, SFMP, NOS). Each speaks its own status vocabulary;
see adapters/<portal>/state_map.yaml. The /_admin endpoint lets demos and tests move an application along."""

from fastapi import APIRouter, HTTPException

from synthetic_data import PORTAL_APPS


def make_router(portal: str) -> APIRouter:
    router = APIRouter()

    def _app(app_id: str) -> dict:
        app = PORTAL_APPS[portal].get(app_id)
        if app is None:
            raise HTTPException(status_code=404, detail="NOT_FOUND")
        return app

    @router.get("/students/{aadhaar_ref}/applications")
    def list_applications(aadhaar_ref: str):
        return [{k: v for k, v in a.items() if k != "payments"}
                for a in PORTAL_APPS[portal].values() if a["aadhaar_ref"] == aadhaar_ref]

    @router.get("/applications/{app_id}")
    def get_application(app_id: str):
        return {k: v for k, v in _app(app_id).items() if k != "payments"}

    @router.get("/applications/{app_id}/payments")
    def get_payments(app_id: str):
        return _app(app_id)["payments"]

    @router.post("/_admin/applications/{app_id}")
    def admin_update(app_id: str, payload: dict):
        app = _app(app_id)
        for key in ("status", "status_updated_at", "payments", "remarks"):
            if key in payload:
                app[key] = payload[key]
        return app

    return router
