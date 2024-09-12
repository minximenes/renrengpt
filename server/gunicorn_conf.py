from multiprocessing import cpu_count


bind = "0.0.0.0:5010"
workers = 2 * cpu_count() + 1
backlog = 2048
worker_class = "gevent"
worker_connections = 1000
timeout = 120
accesslog = "/var/log/gunicorn/access.log"
loglevel = "error"
errorlog = "/var/log/gunicorn/error.log"
