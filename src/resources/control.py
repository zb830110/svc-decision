from fastapi import APIRouter
import logging
import time

app = APIRouter()
logger = logging.getLogger("ah.control")


@app.get("/ready", include_in_schema=False)
def ready():
    return {'message': 'ready'}


@app.get("/healthy", include_in_schema=False)
def healthy():
    return {'healthy': 'true'}


@app.get("/sleep/{seconds}", include_in_schema=False)
def sleep(seconds: int):
    logger.info("Sleeping for %d seconds...", seconds)
    time.sleep(seconds)
    return {'slept': 'true'}
