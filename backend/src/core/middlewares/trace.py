from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.core import ctx


TRACE_ID_HEADER = "X-Trace-Id"

class TraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        trace_id = request.headers.get(TRACE_ID_HEADER, str(uuid4()))
        ctx.set_trace_id(trace_id)
        response = await call_next(request)
        response.headers[TRACE_ID_HEADER] = trace_id
        return response