# Nginx proxy image with OpenSSL for local TLS certificate rotation.
FROM nginx:stable-alpine

RUN apk add --no-cache openssl

COPY entrypoint.sh /etc/nginx/entrypoint.sh
COPY nginx.conf /etc/nginx/conf.d/default.conf
RUN chmod +x /etc/nginx/entrypoint.sh
