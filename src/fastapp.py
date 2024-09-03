from ddtrace import patch_all
patch_all()

import ah_config
from ah_fastapi_utils.datadog_middleware import DataDogStarletteMiddleware
from ah_fastapi_utils.exceptions import InvalidInput, ServiceUnavailable
from ah_fastapi_utils.exception_handlers import custom_exception_handler, validation_exception_handler
from ah_fastapi_utils.handle_reverse_proxy import handle_rp
from ah_fastapi_utils.logging_factory import record_factory
from datadog import initialize as datadog_initialize
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
import logging
from middleware import PrometheusMiddleware
from starlette_prometheus import metrics
from resources.control import app as control_app
from resources.decision import app as decision_app
import uvicorn

ah_config.initialize()

reverse_proxy_route = "/svc-gateway/decision/"

exception_handler_dict = {
    RequestValidationError: validation_exception_handler,
    ServiceUnavailable: custom_exception_handler,
    InvalidInput: custom_exception_handler
}


logging.setLogRecordFactory(record_factory)
app = FastAPI(title="svc-decision",
              exception_handlers=exception_handler_dict, **handle_rp(reverse_proxy_route))

app.include_router(control_app, prefix="/control")
app.include_router(decision_app, prefix="/v0")

# Adding Prometheus Middleware
app.add_middleware(PrometheusMiddleware)
app.add_route("/metrics", metrics)

# Adding DataDog middleware
app.add_middleware(DataDogStarletteMiddleware)


@app.get("/openapi.json", include_in_schema=False)
def get_reverse_proxy_docs():
    """
    This method is added to handle cases where reverse proxy is being used.
    It might be cleaner to add this to an app factory.
    :return:
    """
    return app.openapi()


if __name__ == '__main__':
    uvicorn.run(app, port=5000, debug=True)
