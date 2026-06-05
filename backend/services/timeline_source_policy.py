from typing import Literal

TimelineSourceMode = Literal["SNAPSHOT_ONLY", "LEGACY_MIXED"]


def get_timeline_source_mode(*, legacy_mixed_feed_enabled: bool) -> TimelineSourceMode:
    if legacy_mixed_feed_enabled:
        return "LEGACY_MIXED"
    return "SNAPSHOT_ONLY"
