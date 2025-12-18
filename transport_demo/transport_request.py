from fastapi import APIRouter, Depends, HTTPException

from . import db
from transport_demo.config_loader import load_config, build_amqp_url
from transport_demo.rabbitmq_client import RabbitMQClient
from .transport_requests_services import TransportRequestService
from .schemas import RideCreate, OfferAccept
from pathlib import Path


router = APIRouter(prefix="/requests")

def get_service():
    config_path = Path(__file__).resolve().parent / "config.json"
    config = load_config(config_path)

    amqp_url = build_amqp_url(config.rabbitmq.amqp)

    rabbit = RabbitMQClient(
        url=amqp_url,
        exchange=config.rabbitmq.amqp.exchange,
    )

    return TransportRequestService(
        rabbit=rabbit,
        routing_keys=config.rabbitmq.routing_keys,
    )


@router.post("/create-transport-request")
def create_transport_request(
    payload: RideCreate,
    service: TransportRequestService = Depends(get_service),
):
    service.create_request(payload)
    return {"status": "event published"}


@router.post("/accept-transport-request")
def accept_transport_request(
    payload: OfferAccept,
    service: TransportRequestService = Depends(get_service),
):
    service.accept_request(payload.ride_id, payload.attempt_no)
    return {"status": "accept event published"}

