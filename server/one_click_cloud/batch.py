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
    data = {"redisdb": redisdb}
    headers = {"Content-Type": "application/json"}
    requests.post(url, json=data, headers=headers)


def refreshRedisData(host: str):
    """
    refresh redis data
    @param: host
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
    directR = OpenRedisDirect(host)
    directR.flushdb()
    for kv in kvs:
        for key in kv:
            directR.set(key, kv[key])


if __name__ == "__main__":
    pass
