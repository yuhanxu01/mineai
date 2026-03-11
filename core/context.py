import threading

_local = threading.local()


def set_user(user_id):
    _local.user_id = user_id


def get_user():
    return getattr(_local, 'user_id', None)
