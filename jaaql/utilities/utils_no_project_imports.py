from datetime import datetime


def time_delta_ms(start_time: datetime, end_time: datetime) -> int:
    return int(round((end_time - start_time).total_seconds() * 1000))


def check_allowable_file_path(uri):
    return not isinstance(uri, str) or any([not letter.isalnum() and letter not in ['-', '_', '/'] for letter in uri])
