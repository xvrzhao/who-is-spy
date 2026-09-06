import logging

from src.core import ctx


class TraceFilter(logging.Filter):
    def filter(self, record):
        record.trace_id = ctx.get_trace_id()
        return super().filter(record)