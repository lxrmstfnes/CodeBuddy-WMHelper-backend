"""话术库 / 群发"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.response import ok
from app.db import get_db
from app.deps import manager_id
from app.schemas import MassSendRequest, ScriptCreateRequest
from app.services import scripts

router = APIRouter(prefix="/api", tags=["话术与群发"])


@router.get("/script-items")
def list_scripts(
    category: str | None = Query(default=None),
    db: Session = Depends(get_db),
    mid: str = Depends(manager_id),
):
    return ok(scripts.list_scripts(db, mid, category))


@router.post("/script-items")
def create_script(req: ScriptCreateRequest, db: Session = Depends(get_db), mid: str = Depends(manager_id)):
    return ok(scripts.create_script(db, mid, req))


@router.delete("/script-items/{script_id}")
def delete_script(script_id: int, db: Session = Depends(get_db), mid: str = Depends(manager_id)):
    return ok(scripts.delete_script(db, script_id, mid))


@router.post("/mass-send")
def mass_send(req: MassSendRequest, db: Session = Depends(get_db), mid: str = Depends(manager_id)):
    return ok(scripts.mass_send(db, mid, req))
