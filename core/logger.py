import sys
import os
import time
import logging
from http import HTTPStatus
from loguru import logger
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Remove default logger handler
logger.remove()

# Custom color format for console logs
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

# Add colored console handler
logger.add(
    sys.stdout,
    colorize=True,
    format=LOG_FORMAT,
    level="DEBUG" if os.getenv("CURRENT_ENVIRONMENT", "production").lower() == "development" else "INFO",
    backtrace=True,
    diagnose=True,
)

# File logging with rotation
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
try:
    os.makedirs(LOG_DIR, exist_ok=True)
    logger.add(
        os.path.join(LOG_DIR, "dauth_{time:YYYY-MM-DD}.log"),
        rotation="10 MB",
        retention="14 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="INFO",
        encoding="utf-8",
    )
except Exception:
    pass


# Intercept standard library logging (e.g. uvicorn, fastapi)
class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging():
    """Redirect standard logging (uvicorn, fastapi) to loguru with colors."""
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(logging.INFO)

    for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
        mod_logger = logging.getLogger(logger_name)
        mod_logger.handlers = [InterceptHandler()]
        mod_logger.propagate = False


# Method color mapping
METHOD_COLORS = {
    "GET": "green",
    "POST": "blue",
    "PUT": "yellow",
    "DELETE": "red",
    "PATCH": "magenta",
    "OPTIONS": "cyan",
    "HEAD": "white",
}


def get_status_text(code: int) -> str:
    try:
        phrase = HTTPStatus(code).phrase
        return f"{code} {phrase}"
    except ValueError:
        return str(code)


# Request & Response Logging Middleware (Logs ALL Routes)
class ColoredRequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        start_time = time.perf_counter()
        client_ip = request.client.host if request.client else "unknown"
        origin = request.headers.get("origin") or request.headers.get("referer") or client_ip
        method = request.method
        method_color = METHOD_COLORS.get(method, "white")
        query_str = f"?{request.url.query}" if request.url.query else ""
        full_path = f"{path}{query_str}"

        # 1. Log Incoming Request with Source/Origin
        logger.info(
            f"<cyan>--> [INCOMING]</cyan> <{method_color}>[{method}]</{method_color}> <white><bold>{full_path}</bold></white> | From: <magenta>{origin}</magenta> (IP: <cyan>{client_ip}</cyan>)"
        )

        try:
            response: Response = await call_next(request)
            duration_s = time.perf_counter() - start_time
            duration_ms = duration_s * 1000
            status_code = response.status_code
            status_text = get_status_text(status_code)

            time_display = f"<bold>{duration_s:.3f}s</bold> ({duration_ms:.1f}ms)"

            # 2. Log Outgoing Response with Status and Elapsed Time
            if status_code < 300:
                logger.info(
                    f"<green><-- [RESPONDED]</green> <{method_color}>[{method}]</{method_color}> <white>{path}</white> | <bold><green>{status_text}</green></bold> | Took: <yellow>{time_display}</yellow> | To: <cyan>{client_ip}</cyan>"
                )
            elif status_code < 400:
                logger.info(
                    f"<cyan><-- [REDIRECT]</cyan>  <{method_color}>[{method}]</{method_color}> <white>{path}</white> | <bold><cyan>{status_text}</cyan></bold> | Took: <yellow>{time_display}</yellow> | To: <cyan>{client_ip}</cyan>"
                )
            elif status_code < 500:
                logger.warning(
                    f"<yellow><-- [CLIENT ERR]</yellow> <{method_color}>[{method}]</{method_color}> <white>{path}</white> | <bold><yellow>{status_text}</yellow></bold> | Took: <yellow>{time_display}</yellow> | To: <cyan>{client_ip}</cyan>"
                )
            else:
                logger.error(
                    f"<red><-- [SERVER ERR]</red> <{method_color}>[{method}]</{method_color}> <white>{path}</white> | <bold><red>{status_text}</red></bold> | Took: <yellow>{time_display}</yellow> | To: <cyan>{client_ip}</cyan>"
                )

            return response
        except Exception as exc:
            duration_s = time.perf_counter() - start_time
            duration_ms = duration_s * 1000
            time_display = f"{duration_s:.3f}s ({duration_ms:.1f}ms)"
            logger.exception(
                f"<red><-- [EXCEPTION]</red>  <{method_color}>[{method}]</{method_color}> <white>{path}</white> | <bold><red>500 FAILED</red></bold> | Took: <yellow>{time_display}</yellow> | From: <cyan>{client_ip}</cyan> | Error: {exc}"
            )
            raise exc


__all__ = ["logger", "setup_logging", "ColoredRequestLoggingMiddleware"]
