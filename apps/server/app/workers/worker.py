from redis import Redis
from rq import Connection, Queue, Worker

from app.core.config import settings


def main() -> None:
    redis = Redis.from_url(settings.redis_url)
    with Connection(redis):
        worker = Worker([settings.job_queue_name])
        worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()

