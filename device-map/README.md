# device-map

Interactive web page showing office setup with hoverable hotspots revealing device specs.

**Live:** https://proto.efehnconsulting.com/device-map/

## Features

- 16 devices mapped: 8 machines, 4 monitors, 4 mobile devices
- Hover to preview specs, click to pin tooltips
- Color-coded by type (green=machines, purple=monitors, orange=devices)
- Mobile-friendly (tap to show)
- Data sourced from `~/.dotfiles/`

## Devices

### Machines (8)
- Desktop (Fedora/Windows dual boot) - i9-9900KF, RTX 3090, 64GB
- ROG Flow Z13 (Fedora/Windows) - Ryzen AI MAX 390, 27GB
- Mac Mini (2018) - i7-8700B, 8GB
- Chromebook Lenovo - i3-10110U, Crostini
- IdeaPad U400 - i5-2450M, Debian
- Chromebook Kevin - ARM rk3399, Debian

### Monitors (4)
- Main LG TV - 55" 4K 3840x2160
- Acer Predator XB271HU - 27" 2560x1440 144Hz G-Sync
- Acer AL2216W - 22" 1680x1050
- 2nd LG TV - 1080p

### Mobile Devices (4)
- iPhone 15 Pro - iOS 18
- Galaxy S10e - LineageOS 21, Magisk root
- Galaxy Note 8.0 - LineageOS 14.1
- Galaxy Avant - CyanogenMod, rooted

## Deployment

```bash
cd /path/to/deploy/root
./deploy.sh device-map
```

## Files

- `index.html` - Main page with hotspots
- `style.css` - Styling and hover effects
- `office.jpg` - Office setup photo
