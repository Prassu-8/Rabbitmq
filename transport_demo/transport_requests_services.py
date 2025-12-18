from datetime import datetime, timezone

from transport_demo import ride_repository
from transport_demo.rabbitmq_client import RabbitMQClient


class TransportRequestService:
    def __init__(self, rabbit: RabbitMQClient, routing_keys):
        self.rabbit = rabbit
        self.routing_keys = routing_keys

    def create_request(self, payload) -> None:
        
        self.rabbit.publish(
            routing_key=self.routing_keys.transport_request_created_v1,
            event="transport_request.created.v1",
            data=payload.model_dump(mode="json"),
        )

    def accept_request(self, ride_id: int, attempt_no: int) -> None:
        
        self.rabbit.publish(
            routing_key=self.routing_keys.transport_request_accepted_v1,
            event="transport_request.accepted.v1",
            data={
                "ride_id": ride_id,
                "attempt_no": attempt_no,
                "accepted_at": datetime.now(timezone.utc).isoformat(),
            },
        )
