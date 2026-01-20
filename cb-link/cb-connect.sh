#!/bin/bash
# cb-connect.sh - Connect to cb-link server from Chromebook

# Use hostname.local (works across networks)
SERVER_HOST="${CB_LINK_HOST:-fedora.local}"
PORT="${CB_LINK_PORT:-5900}"
COMMAND="connect"

parse_args() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --host|-h)
                SERVER_HOST="$2"
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

TARGET="$SERVER_HOST"

show_status() {
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
    pkill vncviewer 2>/dev/null
    sleep 0.5
    echo "Connecting to $TARGET:$PORT..."
    vncviewer "$TARGET:$PORT" &
    echo "Press F8 in viewer for menu (fullscreen, etc.)"
}

connect_fullscreen() {
    pkill vncviewer 2>/dev/null
    sleep 0.5
    echo "Connecting fullscreen to $TARGET:$PORT..."
    vncviewer -FullScreen "$TARGET:$PORT" &
    echo "Press F8 to exit fullscreen"
}

connect_scaled() {
    pkill vncviewer 2>/dev/null
    pkill ssvncviewer 2>/dev/null
    sleep 0.5
    echo "Connecting with auto-scaling to $TARGET:$PORT..."
    ssvncviewer -scale auto "$TARGET:$PORT" &
    echo "Mirror mode - auto-scaled to fit CB screen"
}

connect_mirror_fullscreen() {
    pkill vncviewer 2>/dev/null
    pkill ssvncviewer 2>/dev/null
    sleep 0.5
    echo "Connecting fullscreen mirror to $TARGET:$PORT..."
    ssvncviewer -scale auto -fullscreen "$TARGET:$PORT" &
    echo "Mirror fullscreen - press F8 to exit"
}

connect_fast() {
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
        ;;
esac
