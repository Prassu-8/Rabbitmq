from pydantic import BaseModel, ValidationError
from transport_demo.rabbitmq_client import RabbitMQClient
from transport_demo import db, ride_repository
from transport_demo.config import RABBITMQ_URL, EVENTS_EXCHANGE 

class AcceptEvent(BaseModel):
    ride_id: int
    attempt_no: int
    

def handle_accept(message: dict):
    try:
        payload = AcceptEvent(**message["data"])
    except ValidationError:
        raise  # → DLQ

    with db.db_session() as conn:
        allocation = ride_repository.get_allocation_by_ride_id(
            conn, payload.ride_id
        )

        if not allocation:
            raise ValueError("Ride not found")

        ride_repository.mark_allocation_accepted(
            conn, allocation.allocation_id
        )

        ride_repository.mark_ride_accepted(
            conn, payload.ride_id
        )

        conn.commit()

rabbit = RabbitMQClient(
    url=RABBITMQ_URL,
    exchange=EVENTS_EXCHANGE,
)

rabbit.consume(
    queue="q.transport.accept.sqlite.v1",
    routing_key="transport.request.accepted.v1",
    callback=handle_accept,
)
