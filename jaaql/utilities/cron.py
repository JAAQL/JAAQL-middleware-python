from datetime import datetime

_DOW_NAMES = {"sun": 0, "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6}
_FIELD_RANGES = [
    (0, 59),   # minute
    (0, 23),   # hour
    (1, 31),   # day of month
    (1, 12),   # month
    (0, 6),    # day of week (0 = Sun)
]


def _expand_token(token: str, lo: int, hi: int) -> set[int]:
    """
    Expand a single comma‑separated token (e.g. '*/5', '10‑20/2', '7').
    Returns the set of integers it represents.
    """
    if token in ("*", "?"):
        return set(range(lo, hi + 1))

    # range (/step)?
    if "/" in token:
        base, step = token.split("/", 1)
        step = int(step)
    else:
        base, step = token, 1

    if base == "*":
        rng = range(lo, hi + 1, step)
    elif "-" in base:
        start, end = base.split("-", 1)
        rng = range(int(start), int(end) + 1, step)
    else:
        rng = range(int(base), int(base) + 1, step)

    return set(v for v in rng if lo <= v <= hi)


def _parse_field(field: str, idx: int) -> tuple[set[int], bool]:
    """
    Parse one cron field into a set of allowed values.
    Returns (allowed_values, is_restricted_bool)
    """
    lo, hi = _FIELD_RANGES[idx]

    # Translate names to numbers for day‑of‑week
    if idx == 4:  # DOW
        for name, num in _DOW_NAMES.items():
            field = field.lower().replace(name, str(num))

    allowed: set[int] = set()
    for token in field.split(","):
        allowed |= _expand_token(token.strip(), lo, hi)

    restricted = field not in ("*", "?")
    return allowed, restricted


def check_if_should_fire_cron(cron_expr: str, *, now: datetime | None = None) -> bool:
    """
    True  -> run job this minute
    False -> skip
    """
    if not cron_expr:
        return False

    parts = cron_expr.split()
    if len(parts) != 5:
        print("Cron expression " + cron_expr + " is invalid!")
        return False

    if now is None:
        now = datetime.now().astimezone().replace(second=0, microsecond=0)  # Use server local timezone

    minute, hour, dom, month, dow = (
        now.minute,
        now.hour,
        now.day,
        now.month,
        now.weekday(),
    )

    fields = [
        (minute, parts[0]),
        (hour,   parts[1]),
        (dom,    parts[2]),
        (month,  parts[3]),
        (dow,    parts[4]),
    ]

    matches = []
    restricted_flags = []

    for idx, (value, field_text) in enumerate(fields):
        allowed, restricted = _parse_field(field_text, idx)
        matches.append(value in allowed)
        restricted_flags.append(restricted)

    # minute, hour, month must always match if restricted
    if not all(matches[i] for i in (0, 1, 3)):
        return False

    # day‑of‑month vs. day‑of‑week rule
    dom_match, dow_match = matches[2], matches[4]
    dom_restricted, dow_restricted = restricted_flags[2], restricted_flags[4]

    if dom_restricted and dow_restricted:
        return dom_match or dow_match
    elif dom_restricted:
        return dom_match
    elif dow_restricted:
        return dow_match
    else:  # both are '*'
        return True