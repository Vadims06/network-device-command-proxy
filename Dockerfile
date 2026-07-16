FROM python:3.13-alpine3.22

RUN apk add --no-cache openssh-client

WORKDIR /app
COPY pyproject.toml .
COPY device_command_proxy ./device_command_proxy
RUN pip install --no-cache-dir .

RUN addgroup -g 2000 execution-proxy \
    && adduser -D -H -u 2000 -G execution-proxy execution-proxy \
    && install -d -o execution-proxy -g execution-proxy -m 0700 /run/execution-proxy \
    && chown -R execution-proxy:execution-proxy /app

USER execution-proxy
EXPOSE 8080
ENTRYPOINT ["uvicorn", "device_command_proxy.main:app", "--host", "0.0.0.0", "--port", "8080", "--no-access-log"]
