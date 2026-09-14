"""合规接口（§3.7 / §4.4）：词库拉取（前端缓存）+ 实时检查"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response import ok
from app.db import get_db
from app.schemas import ComplianceCheckRequest
from app.services import compliance

router = APIRouter(prefix="/api/compliance", tags=["合规"])


@router.get("/words")
def words(db: Session = Depends(get_db)):
    return ok(compliance.list_words(db))


@router.post("/check")
def check_text(req: ComplianceCheckRequest, db: Session = Depends(get_db)):
    return ok(compliance.check(db, req.text))
