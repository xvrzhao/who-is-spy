import logging

LOG_COLORS = {
    "DEBUG": "\033[90m",       # grey
    "INFO": "\033[32m",        # green
    "WARNING": "\033[33m",     # yellow
    "ERROR": "\033[31m",       # red
    "CRITICAL": "\033[1;31m",  # bold red
}

RESET = "\033[0m"


class ColoredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        color = LOG_COLORS.get(record.levelname, "")
        if not color: return super().format(record)

        orig_levelname, orig_msg = record.levelname, record.msg
        record.levelname, record.msg = f"{color}{record.levelname}{RESET}", f"{color}{record.msg}{RESET}"
        try:
            return super().format(record)
        finally:
            # 还原 record，避免污染其他 handler
            record.levelname, record.msg = orig_levelname, orig_msg
