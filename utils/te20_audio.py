TE20_MONITOR_AUDIO_FULL_SCALE = 220


def format_te20_monitor_audio_level(value) -> str:
    """Convert the TE20 web meter width (0..220) to a percentage."""
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return str(value)

    normalized_value = min(
        max(numeric_value, 0.0),
        float(TE20_MONITOR_AUDIO_FULL_SCALE),
    )
    percent = round(
        normalized_value / TE20_MONITOR_AUDIO_FULL_SCALE * 100
    )
    return f"{percent}%"
