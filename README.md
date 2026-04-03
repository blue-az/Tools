# Tools

Collection of utility tools.

## Contents

| Tool | Description |
|------|-------------|
| [monitor-link](monitor-link/) | Linux-on-Chromebook and Android tablet display link for Fedora/Sway hosts via VNC and ADB |
| [device-map](device-map/) | Interactive web map of office devices with specs from dotfiles |
| [gpu-monitor](gpu-monitor/) | Monitor, record, and graph GPU usage (NVIDIA/ROCm) |

## monitor-link

Display-link toolkit for Fedora/Sway hosts. Its main roles are:

- Linux-on-Chromebook client over WiFi VNC
- USB-tethered Android tablet viewer via ADB reverse
- WiFi second-screen / mirror path for Android viewers

The Chromebook piece depends on Linux being available on the CB; otherwise the
point of the tool is easy to misread.

See [monitor-link/README.md](monitor-link/README.md) for full documentation.

## device-map

Interactive web page showing office setup photo with hoverable hotspots revealing device specs. Data sourced from `~/.dotfiles/`.

**Live:** https://proto.efehnconsulting.com/device-map/

Features:
- 16 devices: 8 machines, 4 monitors, 4 mobile devices
- Hover/tap to see specs
- Color-coded by type (machines, monitors, devices)
- Mobile-friendly
