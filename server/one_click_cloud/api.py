if __name__ == "__main__":
    import os, sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

import os
import logging
import redis
import socket

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.redis import RedisJobStore
from flask import Flask, jsonify, request, Response
from flask_cors import CORS
# inner import
from one_click_cloud.wrapper import varifyRequestTokenWrapper
from one_click_cloud.openClient import OpenClient
from one_click_cloud.auth import deEnSecret, generateToken, splitSecret, isVisitor
from one_click_cloud.batch import run as runBatch, refreshRedisData

ORIGIN_RESOURCE = [
    "http://127.0.0.1:5500",
    "https://renrengpt.cn",
]
DATA_DIR = "/home/one_click_data/"
# 100kB
DATA_LENLIMIT = 100 * 1024
REDIS_SECRET = os.environ.get("REDIS_SECRET")

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ORIGIN_RESOURCE}})
app.config["MAX_CONTENT_LENGTH"] = DATA_LENLIMIT


@app.errorhandler(Exception)
def handleError(e):
    app.logger.error(e)
    unexpected = "An unexpected error has occurred. It will be appreciated if you contact me with details."
    return jsonify(error=str(e) if str(e) else unexpected), 500


# maintain
@app.route("/")
def index():
    return "connect success"


@app.route("/log/<logType>")
def log(logType):
    '''
    view log
    '''
    logfile = f"/var/log/gunicorn/{logType}.log"
    if not os.path.exists(logfile):
        raise ValueError(f'{logType}.log does not exist.')

    with open(logfile, "r") as file:
        content = file.read()
        return Response(content, mimetype="text/plain")


# instance
@app.route("/auth", methods=["POST"])
def auth():
    '''
    authorize and get regions if passed
    '''
    jsondata = request.get_json()
    key_id = jsondata.get("key_id")
    key_secret = jsondata.get("key_secret")
    if not key_id or not key_secret:
        raise ValueError("Access key is not given.")

    decrypted_secret, encrypted_secret = deEnSecret(key_secret)
    try:
        regions = OpenClient.describeRegions(key_id, decrypted_secret)
    except Exception as e:
        raise ValueError(e.data.get("Message") if e.data else e.message)

    # create token
    token = generateToken(key_id, decrypted_secret)
    return jsonify(key_secret=encrypted_secret, token=token, regions=regions)


@app.route("/instancelist", methods=["POST"])
@varifyRequestTokenWrapper
def instanceList(varified):
    '''
    get instance list
    '''
    key_id, key_secret = splitSecret(varified)

    region_ids = request.get_json().get("region_ids")
    try:
        instances = OpenClient.describeInstances(key_id, key_secret, region_ids)
    except Exception as e:
        raise ValueError(e.data.get("Message") if e.data else e.message)

    return jsonify(new_token=varified.get("new_token"), instances=instances)


@app.route("/instancedetail", methods=["POST"])
@varifyRequestTokenWrapper
def instanceDetail(varified):
    '''
    get instance detail
    '''
    key_id, key_secret = splitSecret(varified)

    jsondata = request.get_json()
    instance_id = jsondata.get("instance_id")
    region_id = jsondata.get("region_id")
    try:
        instance = OpenClient.describeInstanceAttribute(key_id, key_secret, region_id, instance_id)
    except Exception as e:
        raise ValueError(e.data.get("Message") if e.data else e.message)

    return jsonify(new_token=varified.get("new_token"), instance=instance)


@app.route("/releaseinstance", methods=["POST"])
@varifyRequestTokenWrapper
def releaseInstance(varified):
    '''
    release instance
    '''
    key_id, key_secret = splitSecret(varified)

    jsondata = request.get_json()
    instance_id = jsondata.get("instance_id")
    region_id = jsondata.get("region_id")
    try:
        OpenClient.deleteInstance(key_id, key_secret, region_id, instance_id)
    except Exception as e:
        raise ValueError(e.data.get("Message") if e.data else e.message)

    return jsonify(new_token=varified.get("new_token"))


@app.route("/speclist", methods=["POST"])
@varifyRequestTokenWrapper
def specList(varified):
    '''
    get spec list
    '''
    key_id, key_secret = splitSecret(varified)

    jsondata = request.get_json()
    region_ids = jsondata.get("region_ids")
    cpus = jsondata.get("cpus")
    mems = jsondata.get("mems")
    bandwidth = jsondata.get("bandwidth")
    is_spot = jsondata.get("is_spot")
    try:
        specs = OpenClient.querySpecs(key_id, key_secret, region_ids, cpus, mems, bandwidth, is_spot)
    except Exception as e:
        raise ValueError(e.data.get("Message") if e.data else e.message)

    return jsonify(new_token=varified.get("new_token"), specs=specs)


@app.route("/createinstance", methods=["POST"])
@varifyRequestTokenWrapper
def createInstance(varified):
    '''
    create instance
    '''
    key_id, key_secret = splitSecret(varified)

    jsondata = request.get_json()
    region_id = jsondata.get("region_id")
    zone_id = jsondata.get("zone_id")
    instance_type = jsondata.get("instance_type")
    cpu = jsondata.get("cpu")
    mem = jsondata.get("mem")
    bandwidth = jsondata.get("bandwidth")
    if cpu > 8 or mem > 16 or bandwidth > 5:
        raise ValueError("Only supports creating instance with limit of 8vCPU 16memGiB 5Mbps.")

    image_id = jsondata.get("image_id")
    disk_category = jsondata.get("disk_category")
    alive_minutes = jsondata.get("alive_minutes")
    if alive_minutes > 60 * 8:
        alive_minutes = 60 * 8
    user_data_base64 = jsondata.get("user_data")
    try:
        OpenClient.createInstance(
            key_id, key_secret, region_id, zone_id,
            instance_type, bandwidth, image_id, disk_category,
            alive_minutes, user_data_base64
        )
    except Exception as e:
        raise ValueError(e.data.get("Message") if e.data else e.message)

    return jsonify(new_token=varified.get("new_token"), region_id=region_id)


@app.route("/getuserdatas")
@varifyRequestTokenWrapper
def getUserdatas(varified):
    '''
    get userdata
    '''
    key_id, _ = splitSecret(varified)
    user_datas = None
    datafile = os.path.join(DATA_DIR, key_id)
    if os.path.exists(datafile):
        with open(datafile, "r") as f:
            user_datas = f.read()

    return jsonify(new_token=varified.get("new_token"), user_datas=user_datas)


@app.route("/setuserdatas", methods=["POST"])
@varifyRequestTokenWrapper
def setUserdatas(varified):
    '''
    set userdata
    '''
    key_id, _ = splitSecret(varified)
    if isVisitor(key_id):
        raise ValueError("Visitor can not perform modification operations.")
    user_datas = request.get_json().get("user_datas")
    datafile = os.path.join(DATA_DIR, key_id)
    with open(datafile, "w") as f:
        f.write(user_datas)

    return jsonify(new_token=varified.get("new_token"))


@app.route("/removeuserdatas")
@varifyRequestTokenWrapper
def removeUserdatas(varified):
    '''
    remove userdata
    '''
    key_id, _ = splitSecret(varified)
    if isVisitor(key_id):
        raise ValueError("Visitor can not perform modification operations.")
    datafile = os.path.join(DATA_DIR, key_id)
    if os.path.exists(datafile):
        os.remove(datafile)

    return jsonify(new_token=varified.get("new_token"))


@app.route("/batch", methods=["POST"])
def batch():
    '''
    run batch
    '''
    jsondata = request.get_json()
    key_id = jsondata.get("key_id")
    key_secret = jsondata.get("key_secret")
    if not key_id or not key_secret:
        raise ValueError("Access key is not given.")

    redisdb = jsondata.get("redisdb")
    if not redisdb:
        raise ValueError("redis db is not given.")

    refreshRedisData(key_id, key_secret, redisdb)
    return "ok"


if __name__ == "__main__":
    # scheduled task
    scheduler = BackgroundScheduler(
        jobstores={"redis": RedisJobStore(host="8.137.83.192", password=REDIS_SECRET)}
    )
    scheduler.add_job(
        runBatch,
        args=["8.137.83.192"],
        trigger="interval",
        minutes=5,
        id="refreshRedisData",
        jobstore="redis",
        replace_existing=True
    )
    scheduler.start()
    app.run(host="0.0.0.0", port=5010, debug=True)
else:
    # product log
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    # single worker
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 47200))
    except socket.error:
        pass
    else:
        # scheduled task
        scheduler = BackgroundScheduler(
            jobstores={"redis": RedisJobStore(password=REDIS_SECRET)}
        )
        scheduler.add_job(
            runBatch,
            trigger="cron",
            hour=6,
            id="refreshRedisData",
            jobstore="redis",
            replace_existing=True
        )
        scheduler.start()
