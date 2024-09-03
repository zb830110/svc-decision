# Set build variables
ARG pip_conf_file=pip.conf
ARG deploy_env=${SERVICE_ENVIRONMENT:-'default'}

# install packages
COPY requirements.txt /tmp/
COPY $pip_conf_file /etc/pip.conf
RUN pip3 install --upgrade pip \
    && pip3 install --no-cache-dir -r /tmp/requirements.txt \
    && rm --force /etc/pip.conf

# Copy srccode to container
WORKDIR /app
COPY . .

# Setup env for app and run
ENV AH_CONFIGURATION_PATH=/app/config
ENV PYTHONIOENCODING=utf_8
ENV LANG=C.UTF-8
ENV AWS_DEFAULT_REGION=us-west-2
ENV deploy_env=${deploy_env}
ENV WEB_CONCURRENCY=2

# copy build config to src
COPY config/gunicorn_conf.py ./src/
WORKDIR /app/src

CMD [ "gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-c", "gunicorn_conf.py", "--log-config", "/app/config/logging.conf", "fastapp:app" ]
