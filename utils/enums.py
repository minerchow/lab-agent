from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    AUTHOR = "author"
    ADMIN = "admin"