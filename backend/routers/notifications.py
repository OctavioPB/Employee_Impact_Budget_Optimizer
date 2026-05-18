from fastapi import APIRouter, HTTPException

from backend.services.data_service import get_notifications, mark_notification_read

router = APIRouter()


@router.get("/notifications")
def list_notifications() -> list:
    return get_notifications()


@router.post("/notifications/{notification_id}/read")
def mark_read(notification_id: str) -> dict:
    ok = mark_notification_read(notification_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"status": "ok"}
