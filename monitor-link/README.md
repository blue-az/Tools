# monitor-link

Display-link toolkit for Fedora/Sway hosts (Z13 or Desktop).

It is used in three closely related ways:

1. Linux-on-Chromebook client over WiFi VNC
2. USB-tethered Android tablet viewer via ADB reverse
3. WiFi second-screen or mirror viewer for Android

The first use case depends on Linux on the Chromebook. If that detail is
omitted, the tool is easy to misread as "just a Chromebook display trick"
rather than a broader host-to-client display setup.

## Display Modes

| Mode | Description |
|------|-------------|
| **extend** | client is a separate 2nd screen with its own workspaces |
| **mirror** | client clones host screen (view-only, scaled to fit) |

## Quick Start

Cheatsheet: `monitor-link-cheatsheet.txt` (optional USB copy path: `/run/media/<user>/<LABEL>/monitor-link-cheatsheet.txt`).

### Extend Mode (2nd screen)
```bash
# On Fedora host (Z13 or Desktop):
cbe              # Start extend mode

# On Linux Chromebook:
cbv              # Launch viewer (windowed only; use cbcf for fullscreen)
```

### Mirror Mode (clone screen)
```bash
# On Fedora host (Z13 or Desktop):
cbm              # Start mirror mode

# On Linux Chromebook:
cbcm             # Connect with auto-scaling
```

### Stop
```bash
# On Linux Chromebook:
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
alias cbt="~/Tools/monitor-link/cb-tablet.sh"
alias cbts="~/Tools/monitor-link/cb-tablet.sh stop"
```

Version-controlled alias template:
```bash
cp ~/Tools/monitor-link/examples/bash_aliases.host ~/.bash_aliases
source ~/.bash_aliases
```

Optional version-controlled Sway keybinds (includes `mod+p` mirror):
```bash
echo 'include ~/Tools/monitor-link/examples/sway-bindings.host.conf' >> ~/.config/sway/config
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

## Linux Chromebook (Client)

### Aliases (in ~/.bash_aliases)
```bash
cbv              # Quick viewer launch (windowed only; avoid Mod+F)
cbc              # Connect to host (same as cbv)
cbcf             # Safe fullscreen (ssvnc; avoids TigerVNC resize issue)
cbcm             # Mirror mode connect (auto-scaled via ssvnc)
cbcd             # Disconnect
cbcs             # Status
```

Version-controlled Debian CB alias template:
```bash
cp ~/Tools/monitor-link/examples/bash_aliases.cb-debian ~/.bash_aliases
source ~/.bash_aliases
```

### Script Commands
```bash
./cb-connect.sh              # Connect windowed
./cb-connect.sh f            # Safe fullscreen (ssvnc scaled)
./cb-connect.sh tf           # TigerVNC fullscreen (legacy)
./cb-connect.sh m            # Mirror mode (ssvnc auto-scaled)
./cb-connect.sh mf           # Mirror fullscreen
./cb-connect.sh d            # Disconnect
./cb-connect.sh s            # Status
```
By default, the client auto-discovers a reachable host from:
`fedora.local desktop.local 127.0.0.1`

Override candidates:
```bash
CB_LINK_HOSTS="desktop.local fedora.local 192.168.x.x" cbv
```

### Manual Connection
```bash
vncviewer host.local:5900           # Extend mode
ssvncviewer -scale auto host.local:5900  # Mirror mode (scaled)
```

TigerVNC fullscreen (`./cb-connect.sh tf` or in-app fullscreen) can trigger
remote resize behavior that causes gray screens in mirror mode; prefer `cbcf`
or `cbcm`.

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

## Android Tablet Over USB

This path is separate from the Linux-on-Chromebook client. It uses `adb
reverse` to make the host VNC server reachable from a tethered Android tablet.

### Start
```bash
./cb-tablet.sh
```

### Stop
```bash
./cb-tablet.sh stop
```

### Troubleshoot
- If the tablet shows extend mode after a mirror session, stop everything (`cbs`) then rerun mirror + tablet (`cbmr` alias if present, or `./cb-display.sh mirror && ./cb-tablet.sh`).

## Android Over WiFi

Android is not limited to the USB-tethered tablet path. Any Android device with
a suitable VNC viewer can also act as a second screen or mirror viewer over
WiFi by connecting to the Fedora host's VNC endpoint.

Typical use:

- start `extend` or `mirror` on the Fedora host
- connect from Android to `hostname.local:5900` or the host IP fallback
- use the same display mode semantics as the Linux Chromebook client

## Requirements

**Fedora host (Z13 or Desktop):**
- wayvnc: `sudo dnf install wayvnc`
- wl-mirror: `sudo dnf install wl-mirror` (for mirror mode)
- avahi: `sudo dnf install avahi` (usually pre-installed)

**Linux Chromebook (Debian):**
- TigerVNC viewer: `sudo apt install tigervnc-viewer`
- SSVNC (for mirror scaling): `sudo apt install ssvnc`
- avahi: `sudo apt install avahi-daemon` (for hostname.local)

**Tablet (optional, USB ADB reverse):**
- Samsung Galaxy Note 8.0 (GT-N5110), LineageOS 7.1.2, Wi-Fi only
- USB debugging enabled; ADB root available (ADB-only)

## Network

Uses mDNS/Avahi hostnames - works across any network (home WiFi, phone hotspot, etc.):

| Device | Hostname | Resolution |
|--------|----------|------------|
| Example host A | `host.local` | 2560x1600 (eDP-1) |
| Example host B | `host2.local` | 2560x1440 (DP-2) |
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
- `examples/bash_aliases.host` - Host alias template (tracked in git)
- `examples/bash_aliases.cb-debian` - Debian CB alias template (tracked in git)
- `examples/sway-bindings.host.conf` - Host Sway keybind template (tracked in git)
