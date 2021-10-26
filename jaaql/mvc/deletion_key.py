from datetime import datetime, timedelta


class DeletionKey:

    def __init__(self, purpose: str, expiry_seconds: int, input_args: dict):
        self.purpose = purpose
        self.expires_at = datetime.now() + timedelta(seconds=expiry_seconds)
        self.input_args = input_args
