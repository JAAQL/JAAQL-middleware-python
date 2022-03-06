from enum import IntEnum

__all__ = ['CustomHTTPStatus']


class CustomHTTPStatus(IntEnum):

    def __new__(cls, value, phrase, description=''):
        obj = int.__new__(cls, value)
        obj._value_ = value

        obj.phrase = phrase
        obj.description = description
        return obj

    DATABASE_NO_EXIST = 460, "Database doesn't exist", "The database doesn't exist on the given node"
