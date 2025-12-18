# check_rabbit.py
try:
    import pika
except ImportError as e:
    raise RuntimeError(
        "pika is not installed. Make sure you are running inside the virtualenv."
    ) from e

from urllib.parse import quote

user = quote("Main_user123", safe="")
password = quote("Dev@ps231", safe="")
host = "localhost"   # or localhost in your config.json
port = 5672
vhost = quote("transport", safe="")

url = f"amqp://{user}:{password}@{host}:{port}/{vhost}"
print("Testing AMQP URL:", url)
try:
    params = pika.URLParameters(url)
    conn = pika.BlockingConnection(params)
    print("Connected OK")
    conn.close()
except Exception as e:
    print("Connection failed:", type(e).__name__, e)
