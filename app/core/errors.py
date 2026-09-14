"""业务异常：由 main.py 统一捕获，包装为 {code, message, data: None} 返回"""


class BizError(Exception):
    def __init__(self, message: str, code: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
