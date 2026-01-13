#!/bin/bash
# cb-share.sh - Share Chromebook screen to Fedora host
# Run this ON THE CHROMEBOOK
#
# Host connects with: vncviewer <CB_hostname>.local:5900

PORT=5900
CB_RES="1600x1067"  # CB effective resolution (2400x1600 @ 1.5 scale)

get_host() {
    echo "$(hostname).local"
}

get_ip() {
    ip -4 addr show | grep -oP '(?<=inet\s)(192\.168\.[0-9.]+|10\.[0-9.]+|172\.(1[6-9]|2[0-9]|3[01])\.[0-9.]+)' | head -1
}

get_status() {
    if pgrep wayvnc >/dev/null 2>&1; then
        echo "running"
    else
        echo "off"
    fi
}

show_status() {
    local status=$(get_status)
    if [ "$status" = "running" ]; then
        local host=$(get_host)
        local ip=$(get_ip)
        echo "CB sharing: ON"
        echo "  Resolution: $CB_RES"
        echo "Host connect:"
        echo "  vncviewer $host:$PORT"
        echo "  vncviewer $ip:$PORT  (fallback)"
    else
        echo "CB sharing: OFF"
    fi
}

start_share() {
    echo "Starting CB screen share..."

    # Stop any existing
    pkill wayvnc 2>/dev/null
    sleep 0.3

    # Start wayvnc on CB's display
    wayvnc --output eDP-1 --render-cursor 0.0.0.0 $PORT &
    sleep 0.5

    if pgrep wayvnc >/dev/null; then
        local host=$(get_host)
        local ip=$(get_ip)
        echo ""
        echo "CB screen share started"
        echo "  Sharing eDP-1 @ $CB_RES"
        echo ""
        echo "Host connect:"
        echo "  vncviewer $host:$PORT"
        echo "  vncviewer $ip:$PORT  (fallback)"
    else
        echo "ERROR: Failed to start wayvnc"
        return 1
    fi
}

stop_share() {
    pkill wayvnc 2>/dev/null
    echo "Stopped"
}

case "${1:-status}" in
    start|s)
        start_share
        ;;
    stop|off)
        stop_share
        ;;
    status|st)
        show_status
        ;;
    *)
        echo "cb-share.sh - Share CB screen to Fedora host"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  start (s)   - Start sharing CB screen"
        echo "  stop        - Stop sharing"
        echo "  status (st) - Show current status"
        echo ""
        echo "Run ON CHROMEBOOK. Host connects with vncviewer."
        ;;
esac
