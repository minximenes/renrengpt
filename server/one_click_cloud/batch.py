import json
import os
import requests

from flask import current_app
from typing import Dict, List
# inner import
from one_click_cloud.openRedis import OpenRedis, OpenRedisDirect
from one_click_cloud.openClient import OpenClient


READONLY_ID = os.environ.get("READONLY_ID")
READONLY_SECRET = os.environ.get("READONLY_SECRET")


def run(redisdb: str = "127.0.0.1"):
    """
    run batch
    @param: redisdb(default localhost)
    """
    url = "http://127.0.0.1:5010/batch"
    data = {
        "key_id": READONLY_ID,
        "key_secret": READONLY_SECRET,
        "redisdb": redisdb
    }
    headers = {"Content-Type": "application/json"}
    requests.post(url, json=data, headers=headers)


def refreshRedisData(key_id: str, key_secret: str, host: str):
    """
    refresh redis data
    @param: key_id, key_secret, host
    """
    region_ids = [
        key for key in OpenClient.describeRegions(
            key_id, key_secret, tuning=False
        )
    ]
    imagekv = initkvUbuntuImage(key_id, key_secret, region_ids)
    updatedb(host, [imagekv])
    current_app.logger.warning("apsheduler ran once")


def initkvUbuntuImage(key_id: str, key_secret: str, region_ids: List[str]) -> Dict:
    """
    get ubuntu image
    @param: key_id, key_secret, region_ids
    @return: {ubuntuimage: {regionid: image_id}}
    """
    image_ids = OpenClient.describeUbuntuImages(key_id, key_secret, region_ids)
    return {"ubuntuimage": json.dumps(image_ids)}


def updatedb(host: str, kvs: List[Dict]):
    '''
    update redis
    @param: host, kvs
    '''
    directR = OpenRedisDirect(host)
    directR.flushdb()
    for kv in kvs:
        for key in kv:
            directR.set(key, kv[key])


if __name__ == "__main__":
    pass
