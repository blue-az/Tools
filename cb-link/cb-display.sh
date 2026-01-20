#!/bin/bash
# cb-display.sh - Two display modes for Chromebook
#
# EXTEND: CB is a separate 2nd screen (HEADLESS-1, own workspaces)
# MIRROR: CB clones laptop screen (view-only clone)

PORT=5900
HEADLESS_RES="1600x1066"
STATE_FILE="/tmp/cb-display-state"
HOST_NAME=$(hostname)

is_desktop_host() {
    [ "$HOST_NAME" = "desktop" ]
}

get_source_output() {
    if [ -n "$CB_LINK_OUTPUT" ]; then
        echo "$CB_LINK_OUTPUT"
        return
    fi
    if is_desktop_host; then
        if swaymsg -t get_outputs | jq -e '.[] | select(.name=="DP-3")' >/dev/null 2>&1; then
            echo "DP-3"
            return
        fi
        echo ""
        return
    fi
    local focused
    focused=$(swaymsg -t get_outputs | jq -r '.[] | select(.focused==true) | .name' | head -1)
    if [ -n "$focused" ] && [[ "$focused" != HEADLESS-* ]]; then
        echo "$focused"
        return
    fi
    swaymsg -t get_outputs | jq -r '.[] | select(.name | startswith("HEADLESS-") | not) | .name' | head -1
}

get_output_resolution() {
    local output=$1
    swaymsg -t get_outputs | jq -r --arg output "$output" '.[] | select(.name==$output) | .current_mode | "\(.width)x\(.height)"' | head -1
}

get_non_headless_count() {
    swaymsg -t get_outputs | jq -r '[.[] | select(.name | startswith("HEADLESS-") | not)] | length'
}

# Get connection info (works across networks)
get_host() {
    echo "$(hostname).local"
}

get_ip() {
    ip -4 addr show | grep -oP '(?<=inet\s)(192\.168\.[0-9.]+|10\.[0-9.]+|172\.(1[6-9]|2[0-9]|3[01])\.[0-9.]+)' | head -1
}

show_connect_info() {
    local host=$(get_host)
    local ip=$(get_ip)
    echo "CB connect:"
    echo "  vncviewer $host:$PORT"
    echo "  vncviewer $ip:$PORT  (fallback)"
}

get_mode() {
    if pgrep wl-mirror >/dev/null 2>&1; then
        echo "mirror"
    elif pgrep -a wayvnc 2>/dev/null | grep -q "HEADLESS-1"; then
        echo "extend"
    else
        echo "off"
    fi
}

show_status() {
    local mode=$(get_mode)
    local source_output
    local native_res
    source_output=$(get_source_output)
    native_res=$(get_output_resolution "$source_output")
    case $mode in
        mirror)
            echo "Mode: MIRROR ($source_output @ $native_res -> wl-mirror -> HEADLESS-1 @ $HEADLESS_RES)"
            show_connect_info
            ;;
        extend)
            echo "Mode: EXTEND (CB is 2nd screen @ $HEADLESS_RES)"
            show_connect_info
            ;;
        off)
            echo "Mode: OFF"
            ;;
    esac
}

start_extend() {
    echo "Starting EXTEND mode..."

    # Stop any existing
    pkill wayvnc 2>/dev/null
    pkill wl-mirror 2>/dev/null
    sleep 0.5

    # Create/enable HEADLESS-1
    if ! swaymsg -t get_outputs | grep -q '"name": "HEADLESS-1"'; then
        swaymsg create_output
        sleep 0.5
    fi
    swaymsg output HEADLESS-1 enable
    swaymsg output HEADLESS-1 resolution $HEADLESS_RES
    sleep 0.5

    # Start wayvnc on HEADLESS-1
    wayvnc --output HEADLESS-1 --render-cursor 0.0.0.0 $PORT &
    sleep 0.5

    if pgrep wayvnc >/dev/null; then
        echo ""
        echo "EXTEND mode started"
        echo "  HEADLESS-1 @ $HEADLESS_RES"
        echo "  This is a separate 2nd screen with own workspaces"
        echo "  Move windows with: mod+Shift+[arrow] or mod+Shift+[number]"
        echo ""
        show_connect_info
    else
        echo "ERROR: Failed to start wayvnc"
        return 1
    fi
}

start_mirror() {
    echo "Starting MIRROR mode (view-only)..."

    local source_output
    local native_res
    local output_count
    local mirror_res
    local mirror_backend
    source_output=$(get_source_output)
    native_res=$(get_output_resolution "$source_output")
    output_count=$(get_non_headless_count)
    if [ -z "$source_output" ]; then
        echo "ERROR: No active output found"
        return 1
    fi
    if [ -n "$CB_LINK_MIRROR_RES" ]; then
        mirror_res="$CB_LINK_MIRROR_RES"
    elif is_desktop_host; then
        mirror_res="1680x1050"
    else
        mirror_res="$native_res"
    fi
    if [ -n "$CB_LINK_MIRROR_BACKEND" ]; then
        mirror_backend="$CB_LINK_MIRROR_BACKEND"
    elif is_desktop_host; then
        mirror_backend="screencopy"
    else
        mirror_backend="screencopy-dmabuf"
    fi

    # Stop any existing
    pkill wayvnc 2>/dev/null
    pkill wl-mirror 2>/dev/null
    pkill -f "cb-mirror-guard" 2>/dev/null
    sleep 0.5

    # Create HEADLESS-1 if needed
    if ! swaymsg -t get_outputs | grep -q '"name": "HEADLESS-1"'; then
        swaymsg create_output
        sleep 0.5
    fi

    # Disable first to clear any existing windows
    swaymsg output HEADLESS-1 disable 2>/dev/null
    sleep 0.3

    # Position far away and enable
    swaymsg output HEADLESS-1 pos 10000 0
    swaymsg output HEADLESS-1 resolution "$mirror_res"
    swaymsg output HEADLESS-1 enable
    sleep 0.3

    # Lock workspaces to the source output on single-display systems
    if [ "$output_count" -le 1 ] && [ -n "$source_output" ]; then
        for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
            swaymsg "workspace $i output $source_output"
        done
    fi

    # Start wl-mirror FIRST (it should be only thing on HEADLESS-1)
    # Default backend is host-specific; override with CB_LINK_MIRROR_BACKEND if needed.
    wl-mirror --backend "$mirror_backend" --fullscreen-output HEADLESS-1 --scaling fit "$source_output" &
    sleep 0.5

    # Force focus back to the source output
    swaymsg focus output "$source_output"

    # Start background guard - moves any non-wl-mirror windows off HEADLESS-1
    (
        SOURCE_OUTPUT="$source_output" exec -a cb-mirror-guard bash -c '
        while true; do
            # Find windows on HEADLESS-1 that are not wl-mirror
            swaymsg -t get_tree | jq -r ".. | objects | select(.output==\"HEADLESS-1\" and .app_id and .app_id!=\"at.yrlf.wl_mirror\") | .id" | while read id; do
                [ -n "$id" ] && swaymsg "[con_id=$id] move to output $SOURCE_OUTPUT" 2>/dev/null
            done
            sleep 1
        done
        '
    ) &

    # Stream HEADLESS-1 via VNC (no --render-cursor, wl-mirror captures cursor)
    wayvnc --output HEADLESS-1 0.0.0.0 $PORT &
    sleep 0.5

    if pgrep wayvnc >/dev/null && pgrep wl-mirror >/dev/null; then
        echo ""
        echo "MIRROR mode started (VIEW-ONLY)"
        echo "  $source_output @ $native_res -> wl-mirror -> HEADLESS-1 @ $mirror_res"
        echo "  Control from host only"
        echo ""
        show_connect_info
    else
        echo "ERROR: Failed to start mirror components"
        return 1
    fi
}

stop_all() {
    local source_output
    local native_res
    source_output=$(get_source_output)
    native_res=$(get_output_resolution "$source_output")
    pkill wayvnc 2>/dev/null
    pkill wl-mirror 2>/dev/null
    pkill -f "cb-mirror-guard" 2>/dev/null
    swaymsg output HEADLESS-1 disable 2>/dev/null
    swaymsg output HEADLESS-2 disable 2>/dev/null
    swaymsg output HEADLESS-3 disable 2>/dev/null
    # Restore native resolution on the source output
    if [ -n "$source_output" ] && [ -n "$native_res" ]; then
        swaymsg output "$source_output" resolution "$native_res"
    fi
    rm -f "$STATE_FILE" 2>/dev/null
    echo "Stopped"
}

toggle() {
    local mode=$(get_mode)
    case $mode in
        mirror)
            start_extend
            ;;
        extend)
            start_mirror
            ;;
        off)
            start_extend
            ;;
    esac
}

show_cb_cmd() {
    local mode=$(get_mode)
    local host=$(get_host)
    case $mode in
        mirror)
            echo "vncviewer -FullScreen $host:$PORT"
            ;;
        extend)
            echo "vncviewer $host:$PORT"
            ;;
        off)
            echo "# Not running. Start with: $0 extend  OR  $0 mirror"
            ;;
    esac
}

case "${1:-status}" in
    extend|e)
        start_extend
        ;;
    mirror|m)
        start_mirror
        ;;
    toggle|t)
        toggle
        ;;
    stop|off)
        stop_all
        ;;
    status|s)
        show_status
        ;;
    cb)
        show_cb_cmd
        ;;
    *)
        echo "cb-display.sh - Use Chromebook as display"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  extend (e)  - 2nd screen (separate workspaces on HEADLESS-1)"
        echo "  mirror (m)  - Clone screen (wl-mirror scaled to $HEADLESS_RES)"
        echo "  toggle (t)  - Switch between extend/mirror"
        echo "  stop        - Stop sharing"
        echo "  status (s)  - Show current mode"
        echo "  cb          - Show CB connect command"
        ;;
esac
