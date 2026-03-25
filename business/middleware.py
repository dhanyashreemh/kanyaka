import logging
import time
import uuid

logger = logging.getLogger(__name__)

class APILoggingMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        start_time = time.time()

        # Unique request ID
        request_id = str(uuid.uuid4())
        request.META["REQUEST_ID"] = request_id

        method = request.method
        path = request.get_full_path()
        ip = request.META.get("REMOTE_ADDR")

        user = "Anonymous"
        if hasattr(request, "user") and request.user.is_authenticated:
            user = str(request.user)

        logger.info(
            f"[{request_id}] ➡️ {method} {path} | User: {user} | IP: {ip}"
        )

        try:
            response = self.get_response(request)

        except Exception:
            logger.error(
                f"[{request_id}] ERROR {method} {path}",
                exc_info=True
            )
            raise

        duration = round(time.time() - start_time, 3)

        logger.info(
            f"[{request_id}] {method} {path} | "
            f"Status: {response.status_code} | Time: {duration}s"
        )

        return response