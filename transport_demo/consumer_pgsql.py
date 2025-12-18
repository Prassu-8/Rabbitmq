import json
from pathlib import Path
from psycopg2 import connect
from transport_demo.rabbitmq_client import RabbitMQClient
from transport_demo.event_schema import RideCreatedEvent
import transport_demo.config as tc 

# print("ACTUAL RABBITMQ_URL =", repr(tc.RABBITMQ_URL))


# Load config
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"
with open(CONFIG_PATH) as f:
    config = json.load(f)

pg = config["postgresql"]


def handle_pg(message: dict):
    payload = RideCreatedEvent(**message["data"])

    conn = connect(
        host=pg["host"],
        port=pg["port"],
        dbname=pg["dbname"],
        user=pg["user"],
        password=pg["password"],
    )

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO rides (
            job_id,
            slot_start,
            slot_end,
            priority_tier,
            offered_rate,
            status
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            payload.job_id,
            payload.slot_start,
            payload.slot_end,
            payload.priority_tier,
            payload.offered_rate,
            payload.status,
        ),
    )

    conn.commit()
    cur.close()
    conn.close()

# RabbitMQ consumer
rabbit = RabbitMQClient(
    url=tc.RABBITMQ_URL,
    exchange=tc.EVENTS_EXCHANGE,
)

rabbit.consume(
    queue=tc.QUEUE_REQUEST_PROJECTION,
    routing_key=tc.QUEUE_ACCEPTANCE_HANDLER,
    callback=handle_pg,
)
