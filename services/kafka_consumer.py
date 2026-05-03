from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    "ride_requests",
    bootstrap_servers="localhost:9092",
    value_deserializer=lambda x: json.loads(x.decode("utf-8"))
)

def consume_events():
    for message in consumer:
        print("Event:", message.value)