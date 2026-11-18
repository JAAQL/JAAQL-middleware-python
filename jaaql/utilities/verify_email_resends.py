"""
How often /resend-verify-email has Keycloak send one account its verification mail. The route needs no login, and every mail it asks for
goes out through the app's mail service, so without a limit anyone could have an unverified account mailed as fast as nginx lets one address
in (3 requests a second): a flood for the person behind it, and spam complaints that can get the sender throttled or suspended, and with it
the app's other mail.

Each process asks Keycloak to send an account its verification mail at most once every RESEND_VERIFY_EMAIL_COOLDOWN_SECONDS (default 60)
and at most RESEND_VERIFY_EMAIL_MAX_PER_HOUR times (default 5) in any hour; 0 or less lifts either limit, and both are read at every resend.
A send counts from the moment it is asked for, whatever Keycloak answers, so a send that fails cannot be repeated faster either, and the
send at a new account's first sign-in counts too, without being held back by them. A resend inside the limits sends nothing and is answered
as the account's last send was: sent (also while it is still being sent), refused, or not sent. Each gunicorn worker (GUNICORN_WORKERS,
default 5) keeps its own count, so a box can send one account up to that many times as many mails. At most
RESEND_VERIFY_EMAIL__max_tracked_accounts accounts are kept count of; beyond that the one longest not sent to is forgotten
"""
import os
import threading
import time
from collections import OrderedDict, deque

from jaaql.constants import ENVIRON__resend_verify_email_cooldown_seconds, ENVIRON__resend_verify_email_max_per_hour, \
    RESEND_VERIFY_EMAIL__default_cooldown_seconds, RESEND_VERIFY_EMAIL__default_max_per_hour, RESEND_VERIFY_EMAIL__max_tracked_accounts

OUTCOME__sent = "sent"
OUTCOME__refused = "refused"
OUTCOME__not_sent = "not sent"

HOUR__seconds = 3600

_lock = threading.Lock()
# Keycloak user id -> [the monotonic times of its sends in the last hour, the outcome of the last of them], the one longest not sent to first
_accounts = OrderedDict()


def _now() -> float:
    return time.monotonic()


def _setting(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def limits() -> (int, int):
    """
    (cooldown seconds, sends an hour), each 0 when it is lifted
    """
    cooldown = _setting(ENVIRON__resend_verify_email_cooldown_seconds, RESEND_VERIFY_EMAIL__default_cooldown_seconds)
    per_hour = _setting(ENVIRON__resend_verify_email_max_per_hour, RESEND_VERIFY_EMAIL__default_max_per_hour)
    return max(cooldown, 0), max(per_hour, 0)


def _forget(now: float, cooldown: int):
    # The accounts not sent to for longer than either limit looks back
    window = max(HOUR__seconds, cooldown)
    while _accounts:
        user_id, entry = next(iter(_accounts.items()))
        if now - entry[0][-1] < window:
            break
        del _accounts[user_id]


def _count(user_id: str, now: float, per_hour: int):
    # Only the last sends the hourly limit looks at are kept, and always the last one. Beyond the cap the account longest not sent to is
    # forgotten
    entry = _accounts.get(user_id)
    if entry is None:
        entry = _accounts[user_id] = [deque(), OUTCOME__sent]
    entry[0].append(now)
    while len(entry[0]) > max(per_hour, 1):
        entry[0].popleft()
    entry[1] = OUTCOME__sent
    _accounts.move_to_end(user_id)
    while len(_accounts) > RESEND_VERIFY_EMAIL__max_tracked_accounts:
        _accounts.popitem(last=False)


def claim(user_id: str) -> str | None:
    """
    None when the account may be sent its verification mail now, which is then counted as sent from now on; else the outcome of its last
    send, which the resend is to be answered with, sending nothing
    """
    cooldown, per_hour = limits()
    now = _now()
    with _lock:
        _forget(now, cooldown)
        entry = _accounts.get(user_id)
        if entry is not None:
            sends = entry[0]
            if cooldown and now - sends[-1] < cooldown:
                return entry[1]
            if per_hour and sum(1 for sent_at in sends if now - sent_at < HOUR__seconds) >= per_hour:
                return entry[1]
        _count(user_id, now, per_hour)
        return None


def record(user_id: str):
    """
    Counts a send the limits do not hold back (the one at a new account's first sign-in)
    """
    cooldown, per_hour = limits()
    now = _now()
    with _lock:
        _forget(now, cooldown)
        _count(user_id, now, per_hour)


def settle(user_id: str, outcome: str):
    """
    What Keycloak answered the account's last send, when it did not send it
    """
    with _lock:
        entry = _accounts.get(user_id)
        if entry is not None:
            entry[1] = outcome


def reset():
    with _lock:
        _accounts.clear()
