import json
from pathlib import Path
from urllib.parse import quote

from .config_schema import AppConfig


def load_config(path: Path) -> AppConfig:
    raw = json.loads(path.read_text())
    return AppConfig.model_validate(raw)

def build_amqp_url(amqp) -> str:
    user = quote(amqp.username, safe="")
    password = quote(amqp.password, safe="")
    vhost = quote(amqp.vhost, safe="")

    return (
        f"amqp://{user}:{password}"
        f"@{amqp.host}:{amqp.port}/{vhost}"
    )
