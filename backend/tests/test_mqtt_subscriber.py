"""TB1 — MQTT abonesi: topic'ler sozlesmeden gelir, mesajlar boru hattina aynen iletilir."""

from __future__ import annotations

from types import SimpleNamespace

from app.ingest import MqttSubscriber


class FakePahoClient:
    """paho.mqtt.client.Client'in MqttSubscriber'in kullandigi yuzeyi (ag yok)."""

    def __init__(self) -> None:
        self.on_connect = None
        self.on_message = None
        self.on_disconnect = None
        self.subscriptions: list[list[tuple[str, int]]] = []

    def subscribe(self, topics):
        self.subscriptions.append(list(topics))
        return (0, 1)


SUCCESS = SimpleNamespace(is_failure=False)
REFUSED = SimpleNamespace(is_failure=True)


def _subscriber(contracts, received):
    client = FakePahoClient()
    sub = MqttSubscriber(
        "broker", 1883, contracts, on_message=lambda t, p: received.append((t, p)), client=client
    )
    return sub, client


def test_subscribes_to_contract_telemetry_topics_on_every_connect(contracts):
    sub, client = _subscriber(contracts, [])

    client.on_connect(client, None, {}, SUCCESS, None)
    client.on_connect(client, None, {}, SUCCESS, None)  # yeniden baglanti

    expected = [("gridup/pano/+/tel", 1), ("gridup/pano/+/evt", 1)]
    assert client.subscriptions == [expected, expected]
    assert sub.connected is True


def test_refused_connection_does_not_subscribe(contracts):
    sub, client = _subscriber(contracts, [])

    client.on_connect(client, None, {}, REFUSED, None)

    assert client.subscriptions == []
    assert sub.connected is False


def test_messages_are_forwarded_with_topic_and_raw_bytes(contracts):
    received: list[tuple[str, bytes]] = []
    _, client = _subscriber(contracts, received)

    client.on_message(client, None, SimpleNamespace(topic="gridup/pano/ADM-00001/tel", payload=b"{}"))

    assert received == [("gridup/pano/ADM-00001/tel", b"{}")]


def test_disconnect_marks_subscriber_offline(contracts):
    sub, client = _subscriber(contracts, [])
    client.on_connect(client, None, {}, SUCCESS, None)

    client.on_disconnect(client, None, {}, SUCCESS, None)

    assert sub.connected is False
