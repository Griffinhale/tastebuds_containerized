#!/bin/sh
# Generate/rotate dev TLS certs before launching nginx for local proxying.
set -euo pipefail

CERT_DIR="${CERT_DIR:-/etc/nginx/certs}"
CERT_PATH="${CERT_PATH:-$CERT_DIR/dev.crt}"
KEY_PATH="${KEY_PATH:-$CERT_DIR/dev.key}"
CERT_DAYS="${TLS_CERT_DAYS:-30}"
ROTATE_WITHIN_SECONDS="${TLS_ROTATE_WITHIN_SECONDS:-1209600}" # 14 days
CHECK_INTERVAL_SECONDS="${TLS_ROTATE_CHECK_INTERVAL_SECONDS:-43200}" # 12 hours
SUBJECT="${TLS_CERT_SUBJECT:-/C=US/ST=Local/L=Local/O=Tastebuds/OU=Dev/CN=localhost}"

has_openssl() {
  command -v openssl >/dev/null 2>&1
}

generate_dev_cert() {
  echo "Generating development certificate for ${SUBJECT}"
  mkdir -p "$CERT_DIR"
  openssl req -x509 -nodes -newkey rsa:2048 \
    -keyout "$KEY_PATH" \
    -out "$CERT_PATH" \
    -days "$CERT_DAYS" \
    -subj "$SUBJECT" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" >/dev/null 2>&1
}

ensure_cert_ready() {
  if ! has_openssl; then
    if [ ! -f "$CERT_PATH" ] || [ ! -f "$KEY_PATH" ]; then
      echo "OpenSSL not available and no existing cert/key found; cannot start TLS proxy." >&2
      exit 1
    fi
    echo "OpenSSL not available; using existing certs without rotation."
    return
  fi

  if [ ! -f "$CERT_PATH" ] || [ ! -f "$KEY_PATH" ]; then
    generate_dev_cert
    return
  fi

  if ! openssl x509 -checkend "$ROTATE_WITHIN_SECONDS" -noout -in "$CERT_PATH" >/dev/null 2>&1; then
    echo "Certificate expiring soon; rotating now"
    generate_dev_cert
  fi
}

refresh_loop() {
  while true; do
    sleep "$CHECK_INTERVAL_SECONDS" || break
    if ! openssl x509 -checkend "$ROTATE_WITHIN_SECONDS" -noout -in "$CERT_PATH" >/dev/null 2>&1; then
      echo "Refreshing dev certificate (background)"
      generate_dev_cert
      nginx -s reload || true
    fi
  done
}

ensure_cert_ready
if has_openssl; then
  refresh_loop &
fi

nginx -g "daemon off;"
