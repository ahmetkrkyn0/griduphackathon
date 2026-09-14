"""TB1 — MQTT abonesi: topic'ler sozlesmeden gelir, mesajlar boru hattina aynen iletilir."""

from __future__ import annotations

import json
from types import SimpleNamespace

from app.ingest import MqttSubscriber
from helpers import utc


class FakePahoClient:
    """paho.mqtt.client.Client'in MqttSubscriber'in kullandigi yuzeyi (ag yok)."""

    def __init__(self) -> None:
        self.on_connect = None
        self.on_message = None
        self.on_disconnect = None
        self.subscriptions: list[list[tuple[str, int]]] = []
        self.published: list[tuple] = []

    def subscribe(self, topics):
        self.subscriptions.append(list(topics))
        return (0, 1)

    def publish(self, topic, payload=None, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))
        return SimpleNamespace(rc=0)  # MQTT_ERR_SUCCESS


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


def test_edge_command_is_published_on_contract_cmd_topic(contracts):
    """Merkez -> kenar komutu (SCADA bakim modu / test alarmi): x-topics cmd sablonu ve QoS'u."""
    sub, client = _subscriber(contracts, [])
    client.on_connect(client, None, {}, SUCCESS, None)

    assert sub.publish_command("ADM-00001", "maint_mode", {"on": True}, ts=utc(2026, 9, 13, 10, 0, 0)) is True

    [(topic, payload, qos, retain)] = client.published
    assert topic == "gridup/pano/ADM-00001/cmd"
    assert json.loads(payload) == {"v": 1, "ts": "2026-09-13T10:00:00+00:00", "cmd": "maint_mode", "args": {"on": True}}
    assert (qos, retain) == (1, False)


def test_edge_command_is_refused_while_disconnected(contracts):
    """Kopukken kuyruga alinmaz: gec teslim edilen eski komut sahada surpriz yaratir, SCADA'ya 0x0B doner."""
    sub, client = _subscriber(contracts, [])

    assert sub.publish_command("ADM-00001", "test_alarm", {}, ts=utc(2026, 9, 13, 10, 0, 0)) is False
    assert client.published == []
