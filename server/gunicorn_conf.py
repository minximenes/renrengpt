from multiprocessing import cpu_count


bind = "0.0.0.0:5000"
workers = 2 * cpu_count() + 1
backlog = 2048
worker_class = "gevent"
worker_connections = 1000
accesslog = "/var/log/gunicorn/access.log"
loglevel = "warning"
errorlog = "/var/log/gunicorn/error.log"
