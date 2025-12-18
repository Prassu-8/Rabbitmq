"""Entry point for the supervisor loop.

Initialises the SQLite DB/SLA via :mod:`db` and :mod:`sla_repository`, then
creates a :class:`transport_demo.rabbitmq_client.RabbitMQClient` and hands
control to :func:`transport_demo.supervisor.run_supervisor_loop`. Pair this
module with ``main_offer_worker`` to run the full pipeline.
"""

from __future__ import annotations

import logging
import signal
import threading

from . import db, sla_repository
from .rabbitmq_client import RabbitMQClient
from .supervisor import run_supervisor_loop


logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


def main() -> None:
    with db.get_connection() as conn:
        db.init_db(conn)
        sla_repository.seed_default_sla(conn)
        conn.commit()

    rabbit = RabbitMQClient()
    stop_event = threading.Event()

    def _handle_signal(signum, frame):  # pragma: no cover - signal handler
        LOGGER.info("Received signal %s, stopping supervisor", signum)
        stop_event.set()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    run_supervisor_loop(db.db_session, rabbit, stop_event=stop_event)


if __name__ == "__main__":  # pragma: no cover
    main()
