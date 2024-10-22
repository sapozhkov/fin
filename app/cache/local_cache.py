global_cache = {}


class LocalCache:
    @staticmethod
    def get(key, default=None):
        global global_cache
        return global_cache.get(key, default)

    @staticmethod
    def set(key, value):
        global global_cache
        global_cache[key] = value

    @classmethod
    def inc_counter(cls, key):
        cls.set(key, cls.get_counter(key) + 1)

    @classmethod
    def get_counter(cls, key):
        return cls.get(key, 0)

    @staticmethod
    def clear():
        global global_cache
        global_cache = {}
