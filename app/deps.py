"""公共依赖：经理身份标识（Demo 阶段不鉴权，预留 X-Manager-Id 请求头）。

未来接入登录后，只需在此解析 token → 经理ID，业务代码零改动。
"""
from fastapi import Header


def manager_id(x_manager_id: str = Header(default="demo-manager")) -> str:
    return x_manager_id
