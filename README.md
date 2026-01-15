# cb-link

Use Chromebook (Debian) as a display for Fedora/Sway hosts (Z13 or Desktop) over WiFi VNC.

## Two Modes

| Mode | Description |
|------|-------------|
| **extend** | CB is a separate 2nd screen with its own workspaces |
| **mirror** | CB clones laptop screen (view-only, scaled to fit) |

## Quick Start

### Extend Mode (2nd screen)
```bash
# On Fedora host (Z13 or Desktop):
cbe              # Start extend mode

# On CB:
cbv              # Launch viewer (or cbcf for fullscreen)
```

### Mirror Mode (clone screen)
```bash
# On Fedora host (Z13 or Desktop):
cbm              # Start mirror mode

# On CB:
cbcm             # Connect with auto-scaling
```

### Stop
```bash
# On CB:
cbcd             # Disconnect viewer

# On Fedora host (Z13 or Desktop):
cbs              # Stop sharing
```

## Fedora Host (Server)

### Aliases (in ~/.bash_aliases)
```bash
cbe              # Start extend mode
cbm              # Start mirror mode
cbtog            # Toggle between extend/mirror
cbmz             # Z13 mirror defaults (eDP-1 @ 2560x1600)
cbs              # Stop sharing
cbst             # Show current mode
cbt              # ADB reverse + open tablet viewer (USB)
cbts             # Remove ADB reverse
```

Suggested alias commands:
```bash
alias cbt="~/Tools/cb-link/cb-tablet.sh"
alias cbts="~/Tools/cb-link/cb-tablet.sh stop"
```

### Script Commands
```bash
./cb-display.sh extend   # 2nd screen mode
./cb-display.sh mirror   # Clone mode
./cb-display.sh toggle   # Switch between modes
./cb-display.sh stop     # Stop sharing
./cb-display.sh status   # Show current mode
./cb-display.sh cb       # Get CB connect command
```

### First Time Setup (open firewall)
```bash
sudo firewall-cmd --add-port=5900/tcp
```

## Chromebook (Client)

### Aliases (in ~/.bash_aliases)
```bash
cbv              # Quick viewer launch (windowed)
cbc              # Connect to host (same as cbv)
cbcf             # Fullscreen connect (F8 to exit)
cbcm             # Mirror mode connect (auto-scaled via ssvnc)
cbcd             # Disconnect
cbcs             # Status
```

### Script Commands
```bash
./cb-connect.sh              # Connect windowed
./cb-connect.sh f            # Connect fullscreen
./cb-connect.sh m            # Mirror mode (ssvnc auto-scaled)
./cb-connect.sh mf           # Mirror fullscreen
./cb-connect.sh d            # Disconnect
./cb-connect.sh s            # Status
```

### Manual Connection
```bash
vncviewer fedora.local:5900           # Extend mode
ssvncviewer -scale auto fedora.local:5900  # Mirror mode (scaled)
```

### Desktop Target (override host)
```bash
CB_LINK_HOST=desktop.local cbv
CB_LINK_HOST=desktop.local cbcm
```
Or:
```bash
./cb-connect.sh --host desktop.local
./cb-connect.sh m --host desktop.local
```

### Tablet (Android over USB, no WiFi)
```bash
./cb-tablet.sh
```
Disconnect:
```bash
./cb-tablet.sh stop
```
Troubleshoot:
- If the tablet shows extend mode after a mirror session, stop everything (`cbs`) then rerun mirror + tablet (`cbmr` alias if present, or `./cb-display.sh mirror && ./cb-tablet.sh`).

## Requirements

**Fedora host (Z13 or Desktop):**
- wayvnc: `sudo dnf install wayvnc`
- wl-mirror: `sudo dnf install wl-mirror` (for mirror mode)
- avahi: `sudo dnf install avahi` (usually pre-installed)

**Chromebook (Debian):**
- TigerVNC viewer: `sudo apt install tigervnc-viewer`
- SSVNC (for mirror scaling): `sudo apt install ssvnc`
- avahi: `sudo apt install avahi-daemon` (for hostname.local)

## Network

Uses mDNS/Avahi hostnames - works across any network (home WiFi, phone hotspot, etc.):

| Device | Hostname | Resolution |
|--------|----------|------------|
| Z13 AMD | `fedora.local` | 2560x1600 (eDP-1) |
| Desktop | `desktop.local` | 2560x1440 (DP-2) |
| Chromebook | `<cb-hostname>.local` | 1600x1066 effective |
| HEADLESS-1 | - | 1600x1066 (VNC output) |

Scripts show both hostname and IP fallback when starting.

## How It Works

**Extend Mode:**
- Host creates a virtual HEADLESS-1 output at 1600x1066
- wayvnc streams HEADLESS-1 to CB
- CB is a true 2nd screen with separate workspaces
- Move windows with mod+Shift+arrow

**Mirror Mode:**
- Host runs wl-mirror to copy the source output to HEADLESS-1
- Desktop defaults: DP-3 source, 1680x1050 target, screencopy backend
- Z13 defaults: focused output (eDP-1), native resolution, screencopy-dmabuf backend
- wayvnc streams the mirrored output
- CB uses ssvnc to further scale if needed
- View-only (control from host only)

Overrides:
```bash
CB_LINK_MIRROR_BACKEND=screencopy
CB_LINK_MIRROR_RES=1680x1050
CB_LINK_OUTPUT=DP-3
```

## Notes

- Not suitable for video (VNC latency)
- Works well for static content, coding, documentation
- F8 in VNC viewer opens menu (fullscreen toggle, etc.)

## Files

- `cb-display.sh` - Host: Start/toggle display modes
- `cb-connect.sh` - CB: Connect to host
- `cb-share.sh` - CB: Share CB screen to host (reverse mode)
- `cb-tablet.sh` - Host: ADB reverse to tablet VNC viewer
- `cb-status.md` - Development/communication log
