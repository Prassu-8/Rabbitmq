"""Thin wrapper over pika for offer messaging."""
from __future__ import annotations
from typing import Callable, Optional
import json

try:
    import pika
except ImportError as e:
    raise RuntimeError(
        "pika is not installed. Make sure you are running inside the virtualenv."
    ) from e


from transport_demo.config import EVENTS_EXCHANGE, RABBITMQ_URL 


class RabbitMQClient:
    def __init__(
        self,
        url: str =RABBITMQ_URL ,
        exchange: str = EVENTS_EXCHANGE,
    ) -> None:
        self.parameters = pika.URLParameters(url)
        self.exchange = exchange
        self.connection: Optional[object] = None
        self.channel: Optional[object] = None

    def connect(self) -> None:
        if self.connection and getattr(self.connection, "is_open", False):
            return

        try:
            self.connection = pika.BlockingConnection(self.parameters)
            self.channel = self.connection.channel()
            self.channel.exchange_declare(
                exchange=self.exchange,
                exchange_type="topic",
                durable=True,
            )
        except Exception as e:
            # Raise a clearer runtime error so the FastAPI handler returns a
            # readable message. Do not include passwords or full URL in the message.
            raise RuntimeError(
                "Failed to connect to RabbitMQ broker. "
                "Check username/password, vhost and that the broker is reachable."
            ) from e


    def close(self) -> None:
        if self.connection and self.connection.is_open:
            self.connection.close()
        self.connection = None
        self.channel = None

    def publish(
        self,
        routing_key: str,
        event: str,
        data: dict,
    ) -> None:
        if pika is None:
           return  # allow API testing without RabbitMQ
        if not self.channel:
            self.connect()

        body = json.dumps({
            "event": event,
            "data": data,
        })

        self.channel.basic_publish(
            exchange=self.exchange,
            routing_key=routing_key,
            body=body,
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,
            ),
        )

    def consume(
        self,
        queue: str,
        routing_key: str,
        callback: Callable[[dict], None],
    ) -> None:
        if not self.channel:
            self.connect()

        assert self.channel is not None
    # Declare DLX
        self.channel.exchange_declare(
        exchange="transport.dlx",
        exchange_type="direct",
        durable=True
        )
    # Declare main queue with DLQ config
        self.channel.queue_declare(
        queue=queue,
        durable=True,
        arguments={
            "x-dead-letter-exchange": "transport.dlx",
            "x-dead-letter-routing-key": "transport.failed",
            },
        )
    # Declare DLQ
        self.channel.queue_declare(
        queue="q.transport.failed.v1",
        durable=True,
        )
    # Bind queues
        self.channel.queue_bind(
        queue=queue,
        exchange=self.exchange,
        routing_key=routing_key,
        )

        self.channel.queue_bind(
        queue="q.transport.failed.v1",
        exchange="transport.dlx",
        routing_key="transport.failed",
        )
    # Consume
        
        def _wrapped(ch, method, properties, body):
            try:
                message = json.loads(body)
                callback(message)
                ch.basic_ack(method.delivery_tag)
            except Exception:
                ch.basic_nack(method.delivery_tag, requeue=False)
                raise

        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue=queue, on_message_callback=_wrapped)
        self.channel.start_consuming()

