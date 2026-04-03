# Samsung Galaxy Avant Profile

## Purpose

This file is a focused handoff note for the rooted Samsung Galaxy Avant in the
current environment. It separates the Avant-specific findings from the broader
Huawei comparison note.

Related file:

- `/home/blueaz/Tools/Avant/HUAWEI_P20_LITE_OVERVIEW.md`

## Executive Read

The Samsung Galaxy Avant is not just an old rooted phone kept around out of
habit. The local evidence shows it functions as a legacy Android compatibility
node for discontinued sports-sensor ecosystems, especially Zepp Tennis and
Babolat Pop. Its most important current value is rooted access to app-private
databases plus continued compatibility with old sensor apps and BLE pairing
flows.

Best current shorthand:

- rooted legacy sensor bridge
- rooted Android data-extraction node
- compatibility appliance for abandoned sports-sensor ecosystems

## Confirmed Local Metadata

From `/home/blueaz/.dotfiles/devices/avant/README.md`:

- Device: Samsung Galaxy Avant
- Model: `SM-G386T`
- Codename: `afyonltetmo`
- Carrier: `T-Mobile`
- ROM: `CyanogenMod`
- Android: `5.1.1`
- API level: `22`
- Root: `Yes (cm-su)`
- USB debugging: enabled
- Stored ADB serial: `9e2ef102`

Additional local device description from
`/home/blueaz/Downloads/SensorDownload/Current/log_device_desc_16.04.25_212952.txt`:

- Manufacturer: `samsung`
- Device ROM change list: `LMY48Y`
- Observed app version in that log: `3.3.2.2655`

## Current Live Reachability

Live check run on 2026-04-02:

- `adb devices -l` showed connected device `9e2ef102`
- reported model: `SM-G386T`
- reported device: `afyonltetmo`
- `adb shell getprop ro.build.version.release` returned `5.1.1`
- `adb shell getprop ro.build.version.sdk` returned `22`
- `adb shell su -c id` returned `uid=0(root)`

So:

- ADB is installed and working locally
- the stored serial in local docs still matches the connected Avant
- USB debugging is active
- root access is live and confirmed

## Confirmed Operational Role

The Avant is clearly integrated into the current tennis-sensor workflow.

### 1. Rooted App-Private DB Extraction

`/home/blueaz/Python/project-phoenix/domains/SensorAgents/TennisAgent/cli/phone_sync_service.py`
defines a rooted ADB sync path for:

- Zepp:
  - remote path:
    `/data/data/com.zepp.ztennis/databases/ztennis.db`
- Babolat:
  - remote path:
    `/data/data/com.piq.babolat.playpop/databases/playpop_.db`

The sync code uses:

- `adb exec-out`
- `su -c 'cat ...'`

That means the intended operational pattern is:

- connect rooted Android phone
- use ADB
- use root to read app-private databases
- copy those DBs into the local analysis environment

### 2. Manual Extraction Workflow Is Also Documented

`/home/blueaz/Mac/MacOSTennisAgent/TennisSensor/CLAUDE.md` includes:

```bash
adb shell "su -c 'cp /data/data/com.zepp.ztennis/databases/ztennis.db /sdcard/ztennis.db'"
adb pull /sdcard/ztennis.db /tmp/zepp.db
```

This strongly reinforces that root on the phone is not incidental. It is part
of the practical workflow.

### 2a. Clear Current Download Instructions

The main practical purpose of the Avant is to pull the current Zepp and
Babolat SQLite databases into:

- `/home/blueaz/Downloads/SensorDownload/Current/`

Canonical phone-side source paths:

- Zepp:
  `/data/data/com.zepp.ztennis/databases/ztennis.db`
- Babolat:
  `/data/data/com.piq.babolat.playpop/databases/playpop_.db`

Canonical local destination paths:

- `/home/blueaz/Downloads/SensorDownload/Current/ztennis.db`
- `/home/blueaz/Downloads/SensorDownload/Current/playpop_.db`

Recommended pull commands, using rooted `adb exec-out` so the binary SQLite
content is not mangled by a PTY:

```bash
adb -s 9e2ef102 exec-out "su -c 'cat /data/data/com.zepp.ztennis/databases/ztennis.db'" > /home/blueaz/Downloads/SensorDownload/Current/ztennis.db
adb -s 9e2ef102 exec-out "su -c 'cat /data/data/com.piq.babolat.playpop/databases/playpop_.db'" > /home/blueaz/Downloads/SensorDownload/Current/playpop_.db
```

Recommended verification:

```bash
sqlite3 /home/blueaz/Downloads/SensorDownload/Current/ztennis.db 'PRAGMA integrity_check;'
sqlite3 /home/blueaz/Downloads/SensorDownload/Current/playpop_.db 'PRAGMA integrity_check;'
```

Expected result:

- `ok`

If preserving an existing local copy matters, rename it first with a timestamp
suffix before overwriting.

### 3. Avant Is Named As The Zepp Data Source

`/home/blueaz/Mac/Tennis/README.md` says:

- `ztennis.db` is pulled from the rooted Avant
- source path:
  `/data/data/com.zepp.ztennis/databases/`

This is direct evidence that the rooted Avant is the source device for at least
part of the current Zepp pipeline.

## Sensors / Apps Most Clearly Tied To The Avant

### Zepp Tennis

Confirmed evidence:

- package path:
  `/data/data/com.zepp.ztennis/databases/ztennis.db`
- active downstream use in multiple analysis projects
- local centralized repository keeps `ztennis.db` as an ongoing active source

Role:

- preserves access to Zepp swing data
- enables continued extraction into Phoenix / Mac / sensor-analysis workflows

### Babolat Pop

Confirmed evidence:

- package path:
  `/data/data/com.piq.babolat.playpop/databases/playpop_.db`
- sync code explicitly supports pulling this DB from the rooted phone
- local logs show `com.piq.babolat.playpop` activity on `SM-G386T`

Role:

- preserves access to Babolat Pop activity/session data
- supports import into local analysis datasets

## Evidence Of BLE Sensor Pairing / Active Sensor Interaction

The local logs are especially useful here.

From
`/home/blueaz/Downloads/SensorDownload/Current/log_13.12.25_024532.txt`
and older related logs:

- `SensorPairFragment pairSensor`
- `BabolatRawDataController getBluetoothDevice`
- `BleClient6Plus ... register BluetoothBroadcastReceiver`
- `SensorBinder connectSensorBLE`

This is strong evidence that the Avant is not merely storing stale databases.
It has at least been used in active BLE sensor-pairing flows with the Babolat
stack.

So one important refinement is:

- the phone is not just an extractor
- it also appears to be a live sensor-pairing / session-capture environment

## Why The Avant Still Matters

The strongest likely reasons are:

1. Legacy Android compatibility
- Android `5.1.1` plus CyanogenMod may still run old sensor apps that became
  unstable, unsupported, or unavailable elsewhere

2. Root access
- root makes app-private SQLite DB extraction practical and repeatable

3. Stable BLE + old app ecosystem
- local logs strongly suggest active BLE pairing behavior with sports sensors

4. Existing downstream tooling depends on its outputs
- Phoenix, MacOSTennisAgent, and other local analysis paths already expect data
  originating from this phone's app databases

## What The Avant Seems To Be, Conceptually

Best current classification:

- primary: compatibility bridge
- secondary: sensor gateway
- tertiary: rooted extractor for app-private data

It is less well-characterized, at least from current local evidence, as:

- a general-purpose embedded Android hacking platform
- a low-level hardware experimentation target

That is the main contrast with the Huawei P20 Lite.

## Huawei Comparison In One Page

Huawei P20 Lite:

- rooted for bootloader bypass using test points and `PotatoNV`
- primarily used with `USB OTG` to exchange data with MCUs
- hidden UART through the headphone jack is present but still experimental
- positioned as a robotics / embedded prototyping device

Galaxy Avant:

- rooted via CyanogenMod / `cm-su`
- clearly used for sports-sensor app compatibility and DB extraction
- active evidence of BLE pairing and sensor-app runtime behavior
- positioned as a legacy sensor-ecosystem anchor

Shared structure:

- old Android hardware remains valuable because root + older software support
  preserve useful interface layers that newer devices may not

Different practical center of gravity:

- Huawei: hardware prototyping
- Avant: sensor compatibility and data preservation

## Unknowns

Still unresolved after this pass:

- whether the Avant supports USB OTG in practice
- whether the Avant has any useful UART/debug path comparable to the Huawei
  case
- whether Zepp also shows directly logged BLE pair/connect flows in the local
  logs
- whether the current live workflow still captures new sessions on the Avant,
  or if some data is now historical while the phone is mostly retained for
  compatibility and extraction
- whether newer phones fail because of Play Store/app availability, Android API
  changes, BLE stack differences, rooting differences, or some combination

## Best Next Steps For Another Agent

1. Inspect the relevant local logs more surgically for Zepp BLE pairing,
   package behavior, and session storage patterns.
2. If the phone is available, connect it and run:
   - `adb devices`
   - `adb shell getprop`
   - `adb shell su -c id`
   - package listing / version checks for Zepp and Babolat apps
3. Determine whether OTG works on the Avant.
4. Check whether the installed apps are still obtainable on newer devices or if
   the Avant's value is partly due to app preservation.
5. Document exactly which sensor workflows still require the Avant and which
   have already migrated elsewhere.

## Bottom Line

The current evidence supports a strong, practical claim:

The rooted Samsung Galaxy Avant is a still-relevant infrastructure device in
the local sports-sensor stack, primarily because it preserves legacy Android
app compatibility, BLE sensor workflows, and root-enabled access to app-private
SQLite databases. Its clearest day-to-day role is downloading fresh copies of
`ztennis.db` and `playpop_.db` into
`/home/blueaz/Downloads/SensorDownload/Current/`.
databases that feed later analysis systems.
