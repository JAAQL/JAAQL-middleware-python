"""
What Sentinel's ingest route (POST /sentinel/reporting/error) stores for a report: the nine values its fixed INSERT binds, read from any
JSON object a reporter sends. The route is public and its callers cannot be updated (a browser tab keeps the BATON runtime it loaded, and
deployed apps keep theirs until they are redeployed), so a report is never refused for its shape:

- A body the route's former validation accepted is stored exactly as before: strings stripped, a digit string for a line or column read
  as an int, a missing line, column or user agent stored as NULL.
- Anything else is made to fit Sentinel's unchanged error table and domains (lengths, line 0..999999, column 1..999999, system_name
  [a-z0-9-], text without NUL or half a surrogate pair, a user agent its encryption can take), and every change is listed in an
  "Ingest adjustments:" section appended to the stored stacktrace, so the alert's head is unchanged and nothing is changed silently.
- A body over Flask's MAX_CONTENT_LENGTH (2 MB), which the route answered 413, is stored too, up to the route's own LIMIT__body: its
  stacktrace keeps its start and its end, so an older reporter's whole parameter values cannot push out the stack sections after them.
- Refused (400) are only a body holding no JSON object Python can parse (none at all, or one nested deeper than its parser goes, which no
  reporter sends) and an object holding none of the nine report keys, which no reporter sends either; and a body over LIMIT__body (413).

Nothing here touches the database; the route runs the INSERT with what read_report returns
"""
import json
import re
from http import HTTPStatus

from flask import json as flask_json

from jaaql.exceptions.http_status_exception import HttpStatusException

KEY__location = "location"
KEY__source_file = "source_file"
KEY__error_condensed = "error_condensed"
KEY__file_line_number = "file_line_number"
KEY__file_col_number = "file_col_number"
KEY__version = "version"
KEY__source_system = "source_system"
KEY__stacktrace = "stacktrace"
KEY__user_agent = "user_agent"
KEY__ip_address = "ip_address"
REPORT_KEYS = (KEY__location, KEY__source_file, KEY__error_condensed, KEY__file_line_number, KEY__file_col_number, KEY__version,
               KEY__source_system, KEY__stacktrace, KEY__user_agent)

# Sentinel's domains: full_url_allowing_anchor_and_parameters, filename, version, system_name, line_number and column_number
LIMIT__location = 512
LIMIT__source_file = 255
LIMIT__version = 40
LIMIT__source_system = 63
RANGE__line = (0, 999999)
RANGE__column = (1, 999999)
LIMIT__digits = 20
# A user agent the route did not take before (not ASCII, not a string, or in a body over the former cap) is cut to this before it is escaped
LIMIT__user_agent = 2048
# The route's own body cap, above Flask's MAX_CONTENT_LENGTH; a body between the two keeps at most LIMIT__stacktrace characters of its
# stacktrace, the last LIMIT__stacktrace_end of them its end
LIMIT__body = 16 * 1024 * 1024
LIMIT__stacktrace = 1024 * 1024
LIMIT__stacktrace_end = 64 * 1024

DEFAULT__error_condensed = "Unknown error"
DEFAULT__source_system = "baton-generator"

CONTENT__json = "application/json"
CONTENT__encoding = "charset=utf-8"

SHOWN__unknown_keys = 20
SHOWN__value_length = 1000
SHOWN__short_length = 100

ERR__not_an_object = "Expected a JSON object"
ERR__not_a_report = "Expected a report"
NOTES__heading = "Ingest adjustments:"

REGEX__system_name = re.compile(r"[A-Za-z0-9\-]*")
REGEX__not_system_name = re.compile(r"[^a-z0-9\-]+")
REGEX__unstorable = re.compile("[\u0000\ud800-\udfff]")
REGEX__digits = re.compile(r"[0-9]+")
REGEX__url = re.compile(r"[A-Za-z][A-Za-z0-9+.\-]*:")
REGEX__query_or_fragment = re.compile(r"[?#]")
# An unknown key that may hold what Sentinel stores encrypted (a user agent or an address) is noted without its value
REGEX__personal_key = re.compile(r"agent|^ua$|^ip|addr", re.I)

_MISSING = object()


def storable(text: str) -> (str, int):
    """
    The text with each NUL and each half of a surrogate pair (which Postgres cannot store and psycopg cannot encode) replaced by U+FFFD,
    one character for one, so a length limit still holds; and how many were replaced
    """
    return REGEX__unstorable.subn("\ufffd", text)


def json_text(value, ensure_ascii: bool = False) -> str:
    try:
        return json.dumps(value, ensure_ascii=ensure_ascii, default=str)
    except Exception:
        return "<%s that cannot be shown>" % type(value).__name__


def shown(value, length: int = SHOWN__value_length) -> str:
    """
    A value as ASCII JSON text for a note, at most length characters
    """
    text = json_text(value, True)
    return text if len(text) <= length else text[:length] + "..."


def type_name(value) -> str:
    if isinstance(value, bool):
        return "a boolean"
    if isinstance(value, (int, float)):
        return "a number"
    if isinstance(value, list):
        return "a list"
    if isinstance(value, dict):
        return "an object"
    return "a " + type(value).__name__


def content_type_accepted_before(content_type) -> bool:
    """
    Exactly what BaseJAAQLController.enforce_content_type_json lets through
    """
    if content_type is None or content_type.split(";")[0] != CONTENT__json:
        return False
    return len(content_type.split(";")) <= 1 or content_type.split(";")[1].strip().lower() == CONTENT__encoding


def lenient_int(digits: str):
    """
    An integer literal as its int, or, past the digits Python converts (4,300 by default), as its digits: a value no position can take
    """
    try:
        return int(digits)
    except ValueError:
        return digits


def parse_body(raw: bytes, notes: list):
    """
    The JSON in the body, read first exactly as request.json read it, then, when that fails, as UTF-8 with invalid bytes replaced, a leading
    BOM dropped, control characters allowed inside strings and an integer literal too long for an int kept as its digits. Nesting too deep
    for the parser is refused like any body that is not JSON
    """
    try:
        return flask_json.loads(raw)
    except Exception:
        pass
    try:
        raw.decode("utf-8")
        valid_utf8 = True
    except UnicodeDecodeError:
        valid_utf8 = False
    text = raw.decode("utf-8", "replace")
    if text.startswith("\ufeff"):
        text = text[1:]
    try:
        data = json.loads(text, strict=False, parse_int=lenient_int)
    except Exception:
        raise HttpStatusException(ERR__not_an_object, HTTPStatus.BAD_REQUEST)
    notes.append("the body is not valid UTF-8: its invalid bytes were read as U+FFFD" if not valid_utf8 else
                 "the body is not strict JSON (a control character inside a string, or an integer too long to read): read leniently")
    return data


def text_value(key: str, data: dict, default: str, notes: list, default_shown: str = None, cut=None) -> str:
    value = data.get(key, _MISSING)
    if value is _MISSING or value is None:
        notes.append("%s: %s, stored as %s" % (key, "missing" if value is _MISSING else "null", default_shown or shown(default)))
        value = default
    elif not isinstance(value, str):
        notes.append("%s: %s, stored as its JSON text" % (key, type_name(value)))
        value = json_text(value)
    value = value.strip()
    if cut is not None:
        value = cut(value)
    value, replaced = storable(value)
    if replaced:
        notes.append("%s: %d character(s) Postgres cannot store (NUL, half a surrogate pair) replaced by U+FFFD" % (key, replaced))
    return value


def at_most(key: str, value: str, limit: int, notes: list) -> str:
    if len(value) <= limit:
        return value
    notes.append("%s: %d characters, cut to the first %d" % (key, len(value), limit))
    return value[:limit]


def path_at_most(key: str, value: str, limit: int, notes: list) -> str:
    """
    A file keeps its name: a URL first loses its query and fragment, then anything still too long keeps its end
    """
    if len(value) <= limit:
        return value
    original = len(value)
    if REGEX__url.match(value):
        value = REGEX__query_or_fragment.split(value, 1)[0]
    if len(value) > limit:
        value = "..." + value[len(value) - limit + 3:]
        notes.append("%s: %d characters, cut to %d keeping its end" % (key, original, limit))
    else:
        notes.append("%s: %d characters, stored without its query and fragment" % (key, original))
    return value


def start_and_end(key: str, value: str, limit: int, end: int, notes: list) -> str:
    """
    At most limit characters: the start and the last end of them, the cut marked where it is. The stack sections an older reporter put
    after whole parameter values are at the end
    """
    if len(value) <= limit:
        return value
    marker = "\n\n[... %d characters cut ...]\n\n" % (len(value) - limit)
    start = limit - end - len(marker)
    notes.append("%s: %d characters in a body over the former size cap, cut to its first %d and last %d" % (key, len(value), start, end))
    return value[:start] + marker + value[len(value) - end:]


def position(key: str, data: dict, low: int, high: int, notes: list):
    """
    A line or column as an int within Sentinel's domain, or None (unknown). An int, or a digit string as the former validation read it, is
    taken as it is; an integral float, or a digit string with spaces or leading zeros, is read as its int, with a note; anything else (out of
    range, a column of 0, a fraction, NaN, a boolean, a list) is stored as NULL, with the value sent in a note
    """
    value = data.get(key, _MISSING)
    if value is _MISSING or value is None:
        return None
    number = None
    if isinstance(value, bool):
        pass
    elif isinstance(value, int):
        number = value
    elif isinstance(value, float) and value.is_integer():
        number = int(value)
    elif isinstance(value, str) and len(value) <= LIMIT__digits and REGEX__digits.fullmatch(value.strip()):
        number = int(value.strip())
    if number is None or not low <= number <= high:
        notes.append("%s: %s is not a %s number within %d..%d, stored as NULL" % (key, shown(value, SHOWN__short_length),
                                                                                  "line" if low == 0 else "column", low, high))
        return None
    if not ((isinstance(value, int) and not isinstance(value, bool)) or (isinstance(value, str) and str(number) == value)):
        notes.append("%s: %s stored as %d" % (key, shown(value, SHOWN__short_length), number))
    return number


def source_system_value(data: dict, notes: list) -> str:
    value = text_value(KEY__source_system, data, DEFAULT__source_system, notes)
    if REGEX__system_name.fullmatch(value) and len(value) <= LIMIT__source_system:
        return value
    normalised = REGEX__not_system_name.sub("-", value.lower())[:LIMIT__source_system] or DEFAULT__source_system
    notes.append("source_system: %s is not a system name ([a-z0-9-], at most %d), stored as %s" % (
        shown(value, SHOWN__short_length), LIMIT__source_system, shown(normalised)))
    return normalised


def ascii_escaped(text: str) -> (str, int):
    """
    Each character outside ASCII as a \\uXXXX escape (one outside the BMP as its surrogate pair, as JavaScript writes it); and how many
    """
    escaped = []
    count = 0
    for character in text:
        code = ord(character)
        if code < 0x80:
            escaped.append(character)
            continue
        count += 1
        if code > 0xFFFF:
            code -= 0x10000
            escaped.append("\\u%04x\\u%04x" % (0xD800 + (code >> 10), 0xDC00 + (code & 0x3FF)))
        else:
            escaped.append("\\u%04x" % code)
    return "".join(escaped), count


def user_agent_value(data: dict, notes: list, over_cap: bool = False):
    """
    The user agent is encrypted at rest, and the encryption takes ASCII only, so other characters become escapes and the stored agent is
    readable after decryption. One the route did not take before is first cut to LIMIT__user_agent, so escaping it costs next to nothing
    and stores a few KB, however long it was sent. Its value is never quoted in a note
    """
    value = data.get(KEY__user_agent, _MISSING)
    if value is _MISSING or value is None:
        return None
    adapted = over_cap
    if not isinstance(value, str):
        notes.append("user_agent: %s, stored as its JSON text" % type_name(value))
        value = json_text(value)
        adapted = True
    value = value.strip()
    if value.isascii() and not adapted:
        return value
    if len(value) > LIMIT__user_agent:
        notes.append("user_agent: %d characters, cut to the first %d" % (len(value), LIMIT__user_agent))
        value = value[:LIMIT__user_agent]
    if value.isascii():
        return value
    value, count = ascii_escaped(value)
    notes.append("user_agent: %d non-ASCII character(s) stored as \\uXXXX escapes" % count)
    return value


def js_text(data: dict, key: str) -> str:
    """
    A line or column as the browser reporters print it in their "No stack available." text
    """
    value = data.get(key, _MISSING)
    if value is _MISSING:
        return "undefined"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return value if isinstance(value, str) else json_text(value)


def text_or(data: dict, key: str, default: str, limit: int = None) -> str:
    value = storable(data[key].strip())[0] if isinstance(data.get(key), str) else default
    return value[:limit] if limit else value


def normalise(data: dict, args: dict = None, content_type=None, notes: list = None, over_cap: bool = False) -> dict:
    """
    The nine values to store for a parsed report body; the query string's values take the place of keys the body lacks, as before.
    over_cap: the body is over the size cap the route had before, so its stacktrace and user agent are cut to a size the route took then
    """
    notes = [] if notes is None else notes
    if not content_type_accepted_before(content_type):
        notes.append("Content-Type %s read as JSON" % shown(content_type, SHOWN__short_length) if content_type is not None else
                     "no Content-Type: the body was read as JSON")
    data = dict(data)
    ignored = []
    for key, value in (args or {}).items():
        if key in REPORT_KEYS and key not in data:
            data[key] = value
        else:
            ignored.append(key)
    for key in ignored[:SHOWN__unknown_keys]:
        notes.append("query string: %s ignored, the body has it" % key if key in REPORT_KEYS else
                     "query string: %s ignored" % shown(key, SHOWN__short_length))
    if len(ignored) > SHOWN__unknown_keys:
        notes.append("query string: %d more keys ignored" % (len(ignored) - SHOWN__unknown_keys))

    unknown = [key for key in data if key not in REPORT_KEYS]
    for key in unknown[:SHOWN__unknown_keys]:
        if key == KEY__ip_address:
            notes.append("ip_address ignored: the address stored is the one the request came from")
        elif REGEX__personal_key.search(key):
            notes.append("unknown key %s ignored, its value not quoted: it may be personal data, which Sentinel stores encrypted" %
                         shown(key, SHOWN__short_length))
        else:
            notes.append("unknown key %s ignored: %s" % (shown(key, SHOWN__short_length), shown(data[key])))
    if len(unknown) > SHOWN__unknown_keys:
        notes.append("%d more unknown keys ignored" % (len(unknown) - SHOWN__unknown_keys))

    location = at_most(KEY__location, text_value(KEY__location, data, "", notes), LIMIT__location, notes)
    source_file = path_at_most(KEY__source_file, text_value(KEY__source_file, data, "", notes), LIMIT__source_file, notes)
    error_condensed = text_value(KEY__error_condensed, data, DEFAULT__error_condensed, notes)
    line = position(KEY__file_line_number, data, *RANGE__line, notes)
    column = position(KEY__file_col_number, data, *RANGE__column, notes)
    version = at_most(KEY__version, text_value(KEY__version, data, "", notes), LIMIT__version, notes)
    source_system = source_system_value(data, notes)
    user_agent = user_agent_value(data, notes, over_cap)

    # The text the browser reporters build for an error without a stack, so a report from a reporter that sent null (BATON before
    # 2026-07-13) reads as a newer one's would
    no_stack = "No stack available. " + (error_condensed or DEFAULT__error_condensed) + "\n\tat " + (source_file or "unknown file") + \
               ":" + js_text(data, KEY__file_line_number) + ":" + js_text(data, KEY__file_col_number)
    stacktrace = text_value(KEY__stacktrace, data, no_stack, notes, "the browser reporters' text for an error without a stack",
                            (lambda text: start_and_end(KEY__stacktrace, text, LIMIT__stacktrace, LIMIT__stacktrace_end, notes))
                            if over_cap else None)

    if notes:
        stacktrace = (stacktrace + "\n\n" if stacktrace else "") + NOTES__heading + "\n" + "\n".join("\t- " + note for note in notes)

    return {KEY__location: location, KEY__source_file: source_file, KEY__error_condensed: error_condensed, KEY__file_line_number: line,
            KEY__file_col_number: column, KEY__version: version, KEY__source_system: source_system, KEY__stacktrace: stacktrace,
            KEY__user_agent: user_agent}


def fallback(data: dict, ex: Exception) -> dict:
    """
    For a body normalise could not read (a fault of this module, never expected): its string fields within their domains, nothing else
    """
    source_system = text_or(data, KEY__source_system, DEFAULT__source_system)
    stacktrace = text_or(data, KEY__stacktrace, "No stack available.", LIMIT__stacktrace)
    note = NOTES__heading + "\n\t- the report could not be read in full (%s), so only its string fields were stored" % type(ex).__name__
    return {KEY__location: text_or(data, KEY__location, "", LIMIT__location),
            KEY__source_file: text_or(data, KEY__source_file, "", LIMIT__source_file),
            KEY__error_condensed: text_or(data, KEY__error_condensed, DEFAULT__error_condensed),
            KEY__file_line_number: None, KEY__file_col_number: None,
            KEY__version: text_or(data, KEY__version, "", LIMIT__version),
            KEY__source_system: source_system if REGEX__system_name.fullmatch(source_system) and len(source_system) <= LIMIT__source_system
            else DEFAULT__source_system,
            KEY__stacktrace: (stacktrace + "\n\n" if stacktrace else "") + note, KEY__user_agent: None}


def read_report(raw: bytes, content_type=None, args: dict = None, former_cap: int = None) -> dict:
    """
    The nine values to store for a request's raw body, its Content-Type and its query string. former_cap is the body size the route took
    before (Flask's MAX_CONTENT_LENGTH); a larger body is stored with its stacktrace and user agent cut. Raises HttpStatusException 400 only
    when the body holds no JSON object, or an object with none of the nine keys and a query string with none either
    """
    notes = []
    data = parse_body(raw or b"", notes)
    if not isinstance(data, dict):
        raise HttpStatusException(ERR__not_an_object, HTTPStatus.BAD_REQUEST)
    if not any(key in data or key in (args or {}) for key in REPORT_KEYS):
        raise HttpStatusException(ERR__not_a_report, HTTPStatus.BAD_REQUEST)
    over_cap = former_cap is not None and len(raw) > former_cap
    if over_cap:
        notes.append("the body is %d bytes, over the %d the route took before" % (len(raw), former_cap))
    try:
        return normalise(data, args, content_type, notes, over_cap)
    except Exception as ex:
        return fallback(data, ex)
