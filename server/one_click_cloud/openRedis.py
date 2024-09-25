import os
import redis


REDIS_SECRET = os.environ.get("REDIS_SECRET")

class OpenRedis:
    '''
    get redis instance with singleton pool
    @param: host(default localhost), db(default 1)
    @return: redis instance
    '''
    _pool = None

    def __new__(cls, host: str = "127.0.0.1", db: int = 1):
        if not cls._pool:
            cls._pool = redis.ConnectionPool(
                host=host,
                port=6379,
                password=REDIS_SECRET,
                db=db,
                decode_responses=True,
            )
        return redis.Redis(connection_pool=cls._pool)


class OpenRedisDirect:
    '''
    get redis instance directly
    @param: host, db(default 1)
    @return: redis instance
    '''
    def __new__(cls, host: str, db: int = 1):
        return redis.Redis(
            host=host,
            port=6379,
            password=REDIS_SECRET,
            db=db,
            decode_responses=True,
            )


if __name__ == "__main__":
    pass
