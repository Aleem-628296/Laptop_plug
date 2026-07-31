bind = "0.0.0.0:8080"
workers = 2
threads = 4
timeout = 120
accesslog = "gunicorn_access.log"
errorlog = "gunicorn_error.log"
loglevel = "info"
