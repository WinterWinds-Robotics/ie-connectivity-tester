#!/bin/sh
# Read in the file of environment settings
. /app/.env
# Then run the CMD
exec "$@"
