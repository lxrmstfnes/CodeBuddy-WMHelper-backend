"""扫码建档接口：经理出码 / 客户校验 / 提交建档 / 二维码图片。"""
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.response import ok
from app.db import get_db
from app.deps import manager_id
from app.schemas import IntakeSubmitRequest
from app.services import intake

router = APIRouter(prefix="/api/intake", tags=["扫码建档"])


@router.post("/tickets")
def create_ticket(db: Session = Depends(get_db), mid: str = Depends(manager_id)):
    """理财经理出示采集码（同时作废该经理未使用的旧码）"""
    return ok(intake.create_ticket(db, mid))


@router.get("/tickets/{token}")
def get_ticket(token: str, db: Session = Depends(get_db)):
    """采集页校验 token 是否仍有效"""
    return ok(intake.get_ticket(db, token))


@router.get("/tickets/{token}/qr")
def ticket_qr(token: str, db: Session = Depends(get_db)):
    """PNG 二维码，内容为 pages/intake/intake?token=…"""
    return Response(content=intake.qr_png(db, token), media_type="image/png")


@router.post("/tickets/{token}/submit")
def submit_ticket(token: str, req: IntakeSubmitRequest, db: Session = Depends(get_db)):
    """客户提交：写主档 + 画像快照 + 建档动态 + 正式测评待办"""
    return ok(intake.submit(db, token, req))
