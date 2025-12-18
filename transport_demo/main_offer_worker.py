"""Entry point for the offer worker.

Initialises SQLite via :mod:`db`, then creates a RabbitMQ client and delegates
to :func:`transport_demo.offer_worker.run_offer_worker`. Run alongside
``main_supervisor`` during manual testing.
"""

from __future__ import annotations

import logging

from . import db
from .offer_worker import run_offer_worker
from .rabbitmq_client import RabbitMQClient


logging.basicConfig(level=logging.INFO)


def main() -> None:
    with db.get_connection() as conn:
        db.init_db(conn)
        conn.commit()
    rabbit = RabbitMQClient()
    run_offer_worker(db.db_session, rabbit)


if __name__ == "__main__":  # pragma: no cover
    main()
