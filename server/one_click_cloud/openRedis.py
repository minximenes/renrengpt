import redis
from typing import Optional


class OpenRedis:
    '''
    get redis instance with singleton pool
    @param: host(default localhost), db(default current)
    @return: redis instance
    '''
    _pool = None

    def __new__(cls, host: str = "127.0.0.1", db: Optional[int] = None):
        if not cls._pool or db is not None:
            cls._pool = redis.ConnectionPool(
                host=host,
                port=6379,
                password="H6r2HDdi-",
                db=0 if db is None else db,
                decode_responses=True,
            )
        return redis.Redis(connection_pool=cls._pool)


class OpenRedisDirect:
    '''
    get redis instance directly
    @param: host, db
    @return: redis instance
    '''
    def __new__(cls, host: str, db: int):
        return redis.Redis(
            host=host,
            port=6379,
            password="H6r2HDdi-",
            db=db,
            decode_responses=True,
            )


if __name__ == "__main__":
    pass
