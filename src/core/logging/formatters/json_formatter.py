import logging, json

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "trace": record.trace_id,
            "message": record.getMessage(),
            "logger": record.name,
            "file:": record.pathname,
            "line": record.lineno,
            "func": record.funcName,
        }
        if record.exc_info:
            log_record["exc"] = self.formatException(record.exc_info)
        return json.dumps(log_record, ensure_ascii=False)
