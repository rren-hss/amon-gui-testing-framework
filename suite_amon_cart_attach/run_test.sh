#!/usr/bin/env bash
set -e

SQUISH_PREFIX="${SQUISH_PREFIX:-/home/rren/squish-for-qt-9.2.2_68x}"
AMON_CART_IP="${AMON_CART_IP:-172.16.0.102}"
SERVER_PORT="${SERVER_PORT:-4322}"
SUITE_DIR="$HOME/suite_amon_cart_attach"

"$SQUISH_PREFIX/bin/squishrunner" \
    --host "$AMON_CART_IP" \
    --port "$SERVER_PORT" \
    --testsuite "$SUITE_DIR" \
    --testcase tst_attach_cart \
    --reportgen stdout
