#!/bin/bash
# cb-tablet.sh - Connect Android tablet to cb-link server via ADB reverse
# Run this on the Fedora host (desktop or Z13) with the tablet plugged in.

PORT="${CB_LINK_PORT:-5900}"
VNC_URI="vnc://127.0.0.1:${PORT}"

require_adb() {
    if ! command -v adb >/dev/null 2>&1; then
        echo "ERROR: adb not found"
        exit 1
    fi
}

require_device() {
    if ! adb devices | awk 'NR>1 && $2=="device" {found=1} END{exit !found}'; then
        echo "ERROR: No authorized ADB device found"
        exit 1
    fi
}

start() {
    require_adb
    require_device
    adb reverse "tcp:${PORT}" "tcp:${PORT}"
    adb shell am start -a android.intent.action.VIEW -d "$VNC_URI" >/dev/null
    echo "Tablet connect: $VNC_URI (ADB reverse tcp:${PORT})"
}

stop() {
    require_adb
    adb reverse --remove "tcp:${PORT}" 2>/dev/null
    echo "ADB reverse removed for tcp:${PORT}"
}

case "${1:-start}" in
    start|s)
        start
        ;;
    stop|off)
        stop
        ;;
    *)
        echo "Usage: $0 [start|stop]"
        echo ""
        echo "Env:"
        echo "  CB_LINK_PORT=5900"
        ;;
esac
