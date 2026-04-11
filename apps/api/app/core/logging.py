import logging
import time
from collections.abc import Callable

from fastapi import Request, Response

logger = logging.getLogger("smart_bi_api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


async def request_logging_middleware(request: Request, call_next: Callable) -> Response:
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "request",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "elapsed_ms": round(elapsed_ms, 2),
        },
    )
    response.headers["X-Elapsed-Ms"] = str(round(elapsed_ms, 2))
    return response
