from transport_demo.rabbitmq_client import RabbitMQClient
from transport_demo import db, ride_repository
from transport_demo.config import EVENTS_EXCHANGE, RABBITMQ_URL
from transport_demo.schemas import RideCreate
from pydantic import ValidationError

def handle_transport_created(message: dict):
    # Schema validation + datetime parsing
    try:
        payload = RideCreate(**message["data"]) # ✅ datetime fixed
    except ValidationError as e:
        print("Invalid message, sending to DLQ:", e)
        raise  # IMPORTANT: raise so message goes to DLQ
  

    with db.db_session() as conn:
        ride_id = ride_repository.create_ride(conn, **payload.model_dump())
        ride_repository.create_initial_allocation_for_ride(
            conn, ride_id=ride_id, max_attempts=3
        )
        conn.commit()

rabbit = RabbitMQClient(
    url=RABBITMQ_URL,
    exchange=EVENTS_EXCHANGE,
)

rabbit.consume(
    queue="q.transport.sqlite.v1",
    routing_key="transport.request.created.v1",
    callback=handle_transport_created,
)
