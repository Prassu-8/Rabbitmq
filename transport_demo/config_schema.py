#-- This guarantees the config is correct before your app starts.------------
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class TLSConfig(BaseModel):
    enabled: bool = False
    ca_cert: Optional[str] = None
    client_cert: Optional[str] = None
    client_key: Optional[str] = None
    verify_peer: bool = True


class AmqpConfig(BaseModel):
    host: str
    port: int = 5672
    vhost: str
    username: str
    password: str
    exchange: str
    tls: Optional[TLSConfig] = None


class RoutingKeysConfig(BaseModel):
    transport_request_created_v1: str
    transport_request_accepted_v1: str


class QueuesConfig(BaseModel):
    request_projection_v1: str
    acceptance_handler_v1: str


class RabbitMQConfig(BaseModel):
    amqp: AmqpConfig
    routing_keys: RoutingKeysConfig
    queues: QueuesConfig


class AppConfig(BaseModel):
    rabbitmq: RabbitMQConfig

class RideCreate(BaseModel):
    city_code: str
    area_code: str
    slot_start: datetime
    slot_end: datetime

class OfferAccept(BaseModel):
    ride_id: int
    attempt_no: int
