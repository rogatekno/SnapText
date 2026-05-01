import os
from taskiq_redis import RedisAsyncResultBackend, ListQueueBroker
from taskiq import TaskiqEvents

# Get Redis URL from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Initialize result backend
# taskiq-redis==0.5.5 accepts: redis_url, keep_results, result_ex_time, result_px_time
# NOTE: prefix_str was added in a later version — isolation is handled by queue_name instead
result_backend = RedisAsyncResultBackend(
    redis_url=REDIS_URL,
    keep_results=True,
    result_ex_time=3600,  # Results stored for 1 hour
)

# Initialize Broker with unique queue name for isolation
broker = ListQueueBroker(
    url=REDIS_URL,
    queue_name="snaptext_ocr_tasks",
).with_result_backend(result_backend)

@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def startup(state):
    """Initialize resources for worker."""
    from app.services.ocr_service import get_ocr_service
    service = get_ocr_service()
    await service.initialize()
    state.ocr_service = service

# Import tasks to register them
import app.tasks.ocr_tasks
