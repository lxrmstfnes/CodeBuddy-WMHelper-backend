"""AI 代理网关（§4 / §7 第二、三步）：前端只调本服务，DeepSeek Key 永不下发。

铁律：所有端点 LLM 失败都回退规则引擎，接口永远 200（§4.5）。
"""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response import ok
from app.db import get_db
from app.deps import manager_id
from app.schemas import (
    CrmExtractRequest, DiagnoseRequest, GradeRequest, MotScriptRequest, OpeningRequest, SummaryRequest,
)
from app.services import crm, diagnose, mot_script, training

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["AI 代理"])


@router.post("/training/grade")
def training_grade(req: GradeRequest, db: Session = Depends(get_db), mid: str = Depends(manager_id)):
    """§4.1 对练评分 + 客户下一句话"""
    logger.info("[grade] manager=%s script=%s round=%s", mid, req.script_id, req.round_idx)
    return ok(training.grade(db, req))


@router.post("/training/summary")
def training_summary(req: SummaryRequest, db: Session = Depends(get_db), mid: str = Depends(manager_id)):
    """§4.2 整场总结建议"""
    logger.info("[summary] manager=%s script=%s", mid, req.script_id)
    return ok(training.summary(db, req))


@router.post("/training/opening")
def training_opening(req: OpeningRequest, db: Session = Depends(get_db)):
    """生成全新客户开场白（前端 generateOpeningWithAI，spec 未列出，此处补齐）"""
    return ok(training.opening(db, req.script_id))


@router.post("/diagnose")
def client_diagnose(req: DiagnoseRequest, db: Session = Depends(get_db), mid: str = Depends(manager_id)):
    """§4.3 客户诊断（评分/雷达/配置/TOP3 产品/三场景大白话话术）"""
    logger.info("[diagnose] manager=%s form=%s", mid, req.model_dump(by_alias=True))
    return ok(diagnose.diagnose(db, req))


@router.post("/crm/extract")
def crm_extract(req: CrmExtractRequest, db: Session = Depends(get_db)):
    """CRM 跟进记录提取（前端 pages/assistant 在用，spec 未列出，此处补齐）。

    设计稿§3.1：传 customerId 时落客户档案 + 自动生成跟进待办；
    返回契约 {record, eventId, tasksCreated}。
    """
    return ok(crm.extract_and_archive(db, req.text, req.customer_id))


@router.post("/mot/script")
def mot_wechat_script(req: MotScriptRequest, db: Session = Depends(get_db), mid: str = Depends(manager_id)):
    """待办一键生成微信话术：按商机 + 客户档案 + 可售产品现场写稿，合规词库清洗。"""
    logger.info("[mot-script] manager=%s event=%s", mid, req.event_id)
    return ok(mot_script.generate(db, req.event_id))
