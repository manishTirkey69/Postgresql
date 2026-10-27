from __future__ import annotations

import pytest
from fastapi import HTTPException

from app import EventBroadcaster, format_sse_event, parse_last_event_id


def test_publish_wakes_every_subscriber() -> None:
    broadcaster = EventBroadcaster()
    first_client = broadcaster.subscribe()
    second_client = broadcaster.subscribe()

    broadcaster.publish()

    assert first_client.is_set()
    assert second_client.is_set()


def test_unsubscribed_client_is_not_woken() -> None:
    broadcaster = EventBroadcaster()
    client = broadcaster.subscribe()
    broadcaster.unsubscribe(client)

    broadcaster.publish()

    assert not client.is_set()


def test_format_sse_event_includes_replay_cursor_and_payload() -> None:
    frame = format_sse_event(
        42,
        "job_created",
        '{"id":7,"title":"API Engineer"}',
    )

    assert frame == (
        'id: 42\nevent: job_created\n'
        'data: {"id":7,"title":"API Engineer"}\n\n'
    )


@pytest.mark.parametrize(("value", "expected"), [(None, 0), ("", 0), ("42", 42)])
def test_parse_last_event_id(value: str | None, expected: int) -> None:
    assert parse_last_event_id(value) == expected


@pytest.mark.parametrize("value", ["abc", "-1"])
def test_parse_last_event_id_rejects_invalid_cursors(value: str) -> None:
    with pytest.raises(HTTPException) as error:
        parse_last_event_id(value)

    assert error.value.status_code == 400
