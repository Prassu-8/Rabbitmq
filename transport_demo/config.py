"""Configuration constants for the transport allocation prototype."""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DB_PATH = Path(os.environ.get("TRANSPORT_DB_PATH", BASE_DIR / "transport_demo.db"))


# ---------- RabbitMQ ----------Updated configuration (drop city & offer coupling)
RABBITMQ_URL = os.environ.get(
    "TRANSPORT_RABBITMQ_URL",
    "amqp://Main_user123:Dev%40ps231@localhost:5672/transport",
)


# from urllib.parse import quote_plus
# RABBITMQ_USER = "Main_user123"
# RABBITMQ_PASSWORD = quote_plus("Dev@ps231")
# RABBITMQ_HOST = "localhost"
# RABBITMQ_PORT = 5672
# RABBITMQ_VHOST = "transport"

# RABBITMQ_URL = (
#     f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASSWORD}"
#     f"@{RABBITMQ_HOST}:{RABBITMQ_PORT}/{RABBITMQ_VHOST}"
# )


# One exchange for events
EVENTS_EXCHANGE = os.environ.get(
    "TRANSPORT_EVENTS_EXCHANGE",
    "transport.events",
)
# ---------- Routing keys ----------
ROUTING_KEY_TRANSPORT_REQUEST_CREATED = os.environ.get(
    "ROUTING_KEY_TRANSPORT_REQUEST_CREATED",
    "transport.request.created",
)
ROUTING_KEY_TRANSPORT_REQUEST_ACCEPTED = os.environ.get(
    "ROUTING_KEY_TRANSPORT_REQUEST_ACCEPTED",
    "transport.request.accepted",               
)
# ---------- Queues ----------
QUEUE_REQUEST_PROJECTION = os.environ.get(
    "QUEUE_REQUEST_PROJECTION",
    "q.transport.request.projection",
)
QUEUE_ACCEPTANCE_HANDLER = os.environ.get(
    "QUEUE_ACCEPTANCE_HANDLER",
    "q.transport.request.accepted",
)
SUPERVISOR_POLL_INTERVAL_SEC = int(os.environ.get("TRANSPORT_SUPERVISOR_POLL", "5"))

SIM_ACCEPTANCE_RATE = float(os.environ.get("TRANSPORT_SIM_ACCEPTANCE_RATE", "0.0"))
