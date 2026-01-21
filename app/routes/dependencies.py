"""
Engine 路由的依赖注入函数
"""
from fastapi import Request


def get_business(http_request: Request) -> str:
    """
    从请求头获取业务类型（依赖注入）
    
    Args:
        http_request: FastAPI Request 对象
        
    Returns:
        业务类型字符串，默认值为 "DEMO"
        
    Example:
        ```python
        @router.get("/blocks")
        async def get_blocks(business: Annotated[str, Depends(get_business)]):
            return {"business": business}
        ```
    """
    return http_request.headers.get("X-Business", "DEMO")