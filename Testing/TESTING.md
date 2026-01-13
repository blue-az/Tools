# cb-link Testing Plan

Private testing checklist before posting to hexdump.

## Test Matrix

### Z13 (AMD) → Chromebook Kevin

| Mode | Status | Notes |
|------|--------|-------|
| Extend | [ ] | CB as 2nd screen, separate workspaces |
| Mirror | [ ] | CB clones Z13 display |

### Desktop → Chromebook Kevin

| Mode | Status | Notes |
|------|--------|-------|
| Extend | [ ] | CB as 2nd screen, separate workspaces |
| Mirror | [ ] | CB clones desktop display |

### Desktop/Z13 → Android Tablet (USB)

| Mode | Status | Notes |
|------|--------|-------|
| Mirror (ADB reverse) | [ ] | `cb-tablet.sh` + VNC over USB |

## Test Steps

1. Start mode on server (Z13 or Desktop)
2. Connect from CB Kevin
3. Verify display works
4. Test window movement (extend) or view-only (mirror)
5. Stop cleanly

## Out of Scope (Current)

- [ ] Fix new screen bug in extend mode
- [ ] Lower resolution option in mirror mode
- [ ] Generic capability (Z13 ↔ Desktop, etc.)

## Results Log

```
Date: 2025-12-21
Tester: blueaz (AMD Z13)
Z13 → Kevin Extend:
Z13 → Kevin Mirror: READY - waiting for CB connection
Desktop → Kevin Extend:
Desktop → Kevin Mirror:
Notes:
```

---

## AMD Status (2025-12-21 20:36)

**Mirror mode is LIVE on Z13 (fedora.local)**

Kevin, connect with:
```bash
cbcm
```

Or manually:
```bash
ssvncviewer -scale auto fedora.local:5900
```

Fallback if hostname fails:
```bash
ssvncviewer -scale auto 192.168.8.116:5900
```

Reply here when connected!

---

## AMD Question (20:45)

Kevin, does `cbcd` work on your CB to disconnect?

The script runs:
```bash
pkill vncviewer
pkill ssvncviewer
```

If it's not working, check:
1. Is the alias set up? `alias cbcd`
2. Try manually: `pkill ssvncviewer`
3. Or just close the viewer window

Also - did the connection work after firewall was opened?
