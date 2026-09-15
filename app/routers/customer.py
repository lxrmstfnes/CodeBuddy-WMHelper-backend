"""客户域数据接口（客户数据库与AI跟踪设计稿 §2.1）"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response import ok
from app.db import get_db
from app.schemas import EventCreateRequest, TaskDoneRequest
from app.services import customers

router = APIRouter(prefix="/api", tags=["客户"])


@router.get("/customers")
def list_customers(db: Session = Depends(get_db)):
    """客户列表（带 pendingTasks 待办数 / nearMaturity 临近到期徽标）"""
    return ok(customers.list_customers(db))


@router.get("/customers/{customer_id}")
def get_customer(customer_id: str, db: Session = Depends(get_db)):
    """客户详情：主档 + 统一动态时间线 + 待办"""
    return ok(customers.get_detail(db, customer_id))


@router.post("/customers/{customer_id}/events")
def add_event(customer_id: str, req: EventCreateRequest, db: Session = Depends(get_db)):
    """手工录入动态（赎回/买入/大额变动）"""
    return ok(customers.add_event(db, customer_id, req))


@router.get("/customers/{customer_id}/tasks")
def list_tasks(customer_id: str, db: Session = Depends(get_db)):
    """该客户待办列表"""
    return ok(customers.list_tasks(db, customer_id))


@router.post("/tasks/{task_id}/done")
def done_task(task_id: int, req: TaskDoneRequest, db: Session = Depends(get_db)):
    """完成待办（闭环）"""
    return ok(customers.done_task(db, task_id, req.done_note))
