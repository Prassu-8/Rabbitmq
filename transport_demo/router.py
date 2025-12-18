#This is our API RouterKey

from fastapi import APIRouter, Depends, HTTPException, status

from transport_demo import db
from transport_demo.config_loader import load_config
from transport_demo.rabbitmq_client import RabbitMQClient
from transport_demo.transport_requests_services import TransportRequestService
from transport_demo.schemas import (
    RideCreate,
    OfferAccept,
)

router = APIRouter(
    prefix="/requests",
    tags=["Transport Requests"],
)


# -------------------------
# Dependency Injection
# -------------------------
def get_transport_request_service() -> TransportRequestService:
    config = load_config()

    rabbit = RabbitMQClient(
        rabbitmq_config=config.rabbitmq
    )

    return TransportRequestService(
        rabbit=rabbit,
        routing_keys=config.rabbitmq.routing_keys,
    )


# -------------------------
# Create Transport Request
# -------------------------
@router.post(
    "/create-transport-request",
    status_code=status.HTTP_201_CREATED,
)
def create_transport_request(
    payload: RideCreate,
    service: TransportRequestService = Depends(get_transport_request_service),
):
    """
    Equivalent to:
    POST /requests/create-transport-job-with-orderids-request
    """
    with db.db_session() as conn:
        try:
            ride_id = service.create_request(conn, payload)
            conn.commit()
            return {"ride_id": ride_id}
        except Exception as exc:
            conn.rollback()
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            )


# -------------------------
# Accept Transport Request
# -------------------------
@router.post(
    "/accept-transport-request",
    status_code=status.HTTP_200_OK,
)
def accept_transport_request(
    payload: OfferAccept,
    service: TransportRequestService = Depends(get_transport_request_service),
):
    """
    Equivalent to:
    POST /requests/accept-transport-request
    """
    with db.db_session() as conn:
        try:
            service.accept_request(
                conn,
                ride_id=payload.ride_id,
                attempt_no=payload.attempt_no,
            )
            conn.commit()
            return {"status": "accepted"}
        except Exception as exc:
            conn.rollback()
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            )


# -------------------------
# Reject Transport Request (optional)
# -------------------------
@router.post(
    "/reject-transport-request",
    status_code=status.HTTP_200_OK,
)
def reject_transport_request(
    payload: OfferAccept,
    service: TransportRequestService = Depends(get_transport_request_service),
):
    with db.db_session() as conn:
        try:
            service.reject_request(
                conn,
                ride_id=payload.ride_id,
                attempt_no=payload.attempt_no,
            )
            conn.commit()
            return {"status": "rejected"}
        except Exception as exc:
            conn.rollback()
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            )

