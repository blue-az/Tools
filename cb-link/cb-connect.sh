#!/bin/bash
# cb-connect.sh - Connect to cb-link server from Chromebook

# Prefer explicit host. Otherwise auto-discover from candidate list.
SERVER_HOST="${CB_LINK_HOST:-}"
PORT="${CB_LINK_PORT:-5900}"
COMMAND="connect"
HOST_EXPLICIT=0
AUTO_HOST_CANDIDATES="${CB_LINK_HOSTS:-fedora.local desktop.local 127.0.0.1}"

parse_args() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --host|-h)
                SERVER_HOST="$2"
                HOST_EXPLICIT=1
                shift 2
                ;;
            --port|-p)
                PORT="$2"
                shift 2
                ;;
            connect|c|fullscreen|full|f|mirror|m|mf|mirror-full|fast|low|disconnect|stop|d|status|s)
                COMMAND="$1"
                shift 1
                ;;
            *)
                if [[ "$1" == *.* || "$1" == *:* ]]; then
                    SERVER_HOST="$1"
                    HOST_EXPLICIT=1
                    shift 1
                else
                    echo "Unknown arg: $1"
                    exit 1
                fi
                ;;
        esac
    done
}

parse_args "$@"

resolve_target() {
    if [ "$HOST_EXPLICIT" -eq 1 ] && [ -n "$SERVER_HOST" ]; then
        TARGET="$SERVER_HOST"
        return
    fi

    # Try hosts in order and pick first one with an open VNC port.
    for h in $AUTO_HOST_CANDIDATES; do
        if command -v nc >/dev/null 2>&1; then
            if nc -z -w 1 "$h" "$PORT" >/dev/null 2>&1; then
                TARGET="$h"
                return
            fi
        fi
    done

    # Fall back to first candidate even if port check unavailable/fails.
    TARGET=$(echo "$AUTO_HOST_CANDIDATES" | awk '{print $1}')
}

resolve_target

show_status() {
    resolve_target
    if pgrep -a vncviewer 2>/dev/null | grep -v grep; then
        echo "Status: CONNECTED"
    elif pgrep -a ssvncviewer 2>/dev/null | grep -v grep; then
        echo "Status: CONNECTED (ssvnc)"
    else
        echo "Status: DISCONNECTED"
        echo "Target: $TARGET:$PORT"
    fi
}

connect() {
    resolve_target
    pkill vncviewer 2>/dev/null
    sleep 0.5
    echo "Connecting to $TARGET:$PORT..."
    vncviewer "$TARGET:$PORT" &
    echo "Press F8 in viewer for menu (fullscreen, etc.)"
}

connect_fullscreen() {
    resolve_target
    pkill vncviewer 2>/dev/null
    sleep 0.5
    echo "Connecting fullscreen to $TARGET:$PORT..."
    vncviewer -FullScreen "$TARGET:$PORT" &
    echo "Press F8 to exit fullscreen"
}

connect_scaled() {
    resolve_target
    pkill vncviewer 2>/dev/null
    pkill ssvncviewer 2>/dev/null
    sleep 0.5
    echo "Connecting with auto-scaling to $TARGET:$PORT..."
    ssvncviewer -scale auto "$TARGET:$PORT" &
    echo "Mirror mode - auto-scaled to fit CB screen"
}

connect_mirror_fullscreen() {
    resolve_target
    pkill vncviewer 2>/dev/null
    pkill ssvncviewer 2>/dev/null
    sleep 0.5
    echo "Connecting fullscreen mirror to $TARGET:$PORT..."
    ssvncviewer -scale auto -fullscreen "$TARGET:$PORT" &
    echo "Mirror fullscreen - press F8 to exit"
}

connect_fast() {
    resolve_target
    pkill vncviewer 2>/dev/null
    sleep 0.5
    echo "Connecting (low color) to $TARGET:$PORT..."
    vncviewer -LowColorLevel=1 "$TARGET:$PORT" &
    echo "Press F8 in viewer for menu"
}

disconnect() {
    pkill vncviewer 2>/dev/null
    pkill ssvncviewer 2>/dev/null
    echo "Disconnected"
}

case "$COMMAND" in
    connect|c)
        connect
        ;;
    fullscreen|full|f)
        connect_fullscreen
        ;;
    mirror|m)
        connect_scaled
        ;;
    mf|mirror-full)
        connect_mirror_fullscreen
        ;;
    fast|low)
        connect_fast
        ;;
    disconnect|stop|d)
        disconnect
        ;;
    status|s)
        show_status
        ;;
    *)
        echo "Usage: cb-connect.sh [command]"
        echo ""
        echo "Extend mode (HEADLESS-1, 2nd screen):"
        echo "  connect (c)     - Connect windowed"
        echo "  fullscreen (f)  - Connect fullscreen"
        echo "  fast            - Low color (faster)"
        echo ""
        echo "Mirror mode (source output clone, ssvnc scaled):"
        echo "  mirror (m)      - Connect with auto-scaling"
        echo "  mirror-full (mf)- Fullscreen mirror"
        echo ""
        echo "  disconnect (d)  - Disconnect"
        echo "  status (s)      - Show connection status"
        echo ""
        echo "Target: $TARGET:$PORT"
        echo ""
        echo "Options:"
        echo "  --host <hostname.local>   Override server (or set CB_LINK_HOST)"
        echo "  --port <port>             Override port (or set CB_LINK_PORT)"
        echo "  CB_LINK_HOSTS             Space-separated auto-discovery hosts"
        ;;
esac
