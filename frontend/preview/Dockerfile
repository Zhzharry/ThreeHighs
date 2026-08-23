ARG BASE_REGISTRY=docker.io/library
FROM ${BASE_REGISTRY}/node:22-alpine

WORKDIR /app
COPY . .

EXPOSE 80

CMD ["node", "server.mjs"]
