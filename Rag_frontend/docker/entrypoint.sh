#!/bin/sh
set -e

# Vite bakes import.meta.env.VITE_* in at BUILD time -- but compose's
# `environment: VITE_API_URL=...` only sets it at container RUNTIME. Those
# are two different moments, so the value in compose.yaml would silently
# never reach the built JS bundle if we relied on import.meta.env alone.
#
# Fix: index.html loads /env-config.js before the app bundle, and this
# script regenerates that file from the *actual* runtime env var every time
# the container starts, via envsubst on the template baked into the image.
: "${VITE_API_URL:=http://localhost:8000}"

envsubst '${VITE_API_URL}' \
  < /usr/share/nginx/html/env-config.js.template \
  > /usr/share/nginx/html/env-config.js

exec nginx -g "daemon off;"
