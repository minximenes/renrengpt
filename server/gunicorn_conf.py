import os

from multiprocessing import cpu_count


bind = "0.0.0.0:5010"
workers = 2 * cpu_count() + 1
backlog = 2048
worker_class = "gevent"
worker_connections = 1000
timeout = 120
accesslog = "/var/log/gunicorn/access.log"
loglevel = "info"
errorlog = "/var/log/gunicorn/error.log"
# env
def readProfile(name : str):
    return open("/etc/profile").read().split(f"{name}=")[1].split("\n")[0]

os.environ["SECRET_ENCRYPT_KEY"] = readProfile("SECRET_ENCRYPT_KEY")
os.environ["JWT_SECRET"] = readProfile("JWT_SECRET")
os.environ["READONLY_ID"] = readProfile("READONLY_ID")
os.environ["READONLY_SECRET"] = readProfile("READONLY_SECRET")
os.environ["REDIS_SECRET"] = readProfile("REDIS_SECRET")
