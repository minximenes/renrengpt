import json
import os

from flask import current_app
from typing import Dict, List
# inner import
from one_click_cloud.openRedis import OpenRedis, OpenRedisDirect
from one_click_cloud.openClient import OpenClient


READONLY_ID = os.environ.get("READONLY_ID")
READONLY_SECRET = os.environ.get("READONLY_SECRET")


def run(host: str = "127.0.0.1"):
    """
    run batch
    @param: host(default localhost)
    """
    region_ids = [
        key for key in OpenClient.describeRegions(
            READONLY_ID, READONLY_SECRET, tuning=False
        )
    ]
    imagekv = initkvUbuntuImage(region_ids)
    updatedb(host, [imagekv])
    current_app.logger.info("apsheduler ran once")


def initkvUbuntuImage(region_ids: List[str]) -> Dict:
    """
    get ubuntu image
    @param: region_ids
    @return: {ubuntuimage: {regionid: image_id}}
    """
    image_ids = OpenClient.describeUbuntuImages(READONLY_ID, READONLY_SECRET, region_ids)
    return {"ubuntuimage": json.dumps(image_ids)}


def updatedb(host: str, kvs: List[Dict]):
    '''
    update redis
    @param: host, kvs
    '''
    using_db = OpenRedis(host).connection_pool.connection_kwargs["db"]
    # update idle
    idle_db = 1 if using_db == 0 else 0
    directR = OpenRedisDirect(host, idle_db)
    directR.flushdb()
    for kv in kvs:
        for key in kv:
            directR.set(key, kv[key])
    # shift db
    OpenRedis(host, idle_db)


if __name__ == "__main__":
    pass
