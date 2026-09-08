TE20_MONITOR_AUDIO_FULL_SCALE = 220


def normalize_te20_monitor_audio_level(value) -> int | None:
    """Normalize authoritative Huawei monitor-audio raw evidence to percent."""
    if isinstance(value, bool):
        return None
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return None
    normalized_value = min(max(numeric_value, 0.0), float(TE20_MONITOR_AUDIO_FULL_SCALE))
    return round(normalized_value / TE20_MONITOR_AUDIO_FULL_SCALE * 100)


def format_te20_monitor_audio_level(value) -> str:
    """Convert the TE20 web meter width (0..220) to a percentage."""
    percent = normalize_te20_monitor_audio_level(value)
    if percent is None:
        return str(value)
    return f"{percent}%"
