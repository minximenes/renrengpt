import logging

from flask import Flask, jsonify, request
from flask_cors import CORS
# inner import
from one_click_cloud.wrapper import varifyRequestTokenWrapper
from one_click_cloud.openClient import OpenClient
from one_click_cloud.auth import deEnSecret, generateToken, splitSecret


ORIGIN_RESOURCE = "http://127.0.0.1:5500 http://8.137.83.192 http://beautigpt"

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ORIGIN_RESOURCE}})


@app.errorhandler(Exception)
def handleError(e):
    app.logger.error(e)
    unexpected = "An unexpected error has occurred. It will be appreciated if you email me with details."
    return jsonify(error=str(e) if str(e) else unexpected), 500


@app.route("/")
def index():
    return "connect success"


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
    try:
        specs = OpenClient.querySpecs(key_id, key_secret, region_ids, cpus, mems, bandwidth)
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
    if cpu > 2 or mem > 2 or bandwidth > 3:
        raise ValueError("Only supports creating instance with limit of 2vCPU 2memGiB 3Mbps.")

    image_id = jsondata.get("image_id")
    disk_category = jsondata.get("disk_category")
    alive_minutes = jsondata.get("alive_minutes")
    if alive_minutes > 60 * 4:
        alive_minutes = 60 * 4
    user_data_base64 = jsondata.get("user_data")
    try:
        OpenClient.createInstance(
            key_id, key_secret, region_id, zone_id,
            instance_type, bandwidth, image_id, disk_category,
            alive_minutes, user_data_base64
        )
    except Exception as e:
        raise ValueError(e.data.get("Message") if e.data else e.message)

    return jsonify(new_token=varified.get("new_token"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
else:
    # product log
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

