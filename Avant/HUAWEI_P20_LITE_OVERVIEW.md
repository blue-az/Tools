# Huawei P20 Lite Root / UART / OTG Overview

## Purpose

This file captures what was learned from a public post and reply thread about
using an old Huawei phone as a robotics development platform. The immediate
goal is to preserve the Huawei findings clearly enough that a later pass can
compare them against a rooted Samsung Galaxy Avant.

This is a handoff note for another agent.

Companion file for the Avant-specific side:

- `/home/blueaz/Tools/Avant/GALAXY_AVANT_PROFILE.md`

## What Triggered This

A post described old Android phones, including a Huawei P20 Lite, as useful
robotics dev platforms because they still provide:

- compute
- camera
- IMU and other sensors
- battery
- BLE / Wi-Fi / LTE
- USB OTG
- wireless debugging over ADB
- a "secret UART"

The post also said the phone only needed about "20 minutes of rooting
surgery." A video showed heat gun + pry tool + back cover removal, but the
video itself did not clearly explain the steps.

## Confirmed Facts From The Author's Reply

The author later clarified the following:

1. The back-cover removal was only needed for the root bypass.
2. The hidden UART is available through the 3.5 mm headphone jack.
3. Root access is required before the UART can be used.
4. The author used `PotatoNV` to flash a modified bootloader.
5. The phone had to be opened in order to bridge internal test points.
6. The author's main practical use today is `USB OTG` for transferring data to
   and from other MCUs.
7. The UART is still experimental; the author has not fully worked out how to
   use it yet.

Author-provided tool:

- `PotatoNV`: <https://github.com/mashed-potatoes/PotatoNV>

## Best Current Interpretation

The important distinction is:

- The phone was opened for the root / bootloader-bypass procedure.
- The phone was not opened primarily to access the UART.
- The UART is apparently routed through the headphone jack, not only through
  hidden motherboard pads.
- Root is a prerequisite for enabling or exposing that UART path.

So the current Huawei setup looks like this:

1. Open phone
2. Bridge test points
3. Use `PotatoNV` to bypass bootloader restrictions / flash modified
   bootloader
4. Gain root access
5. Use USB OTG as the main stable robotics interface
6. Experiment with UART later via the 3.5 mm jack

## What "USB OTG" Means In This Context

`USB OTG` matters because it lets the phone act as a USB host. For robotics or
hardware prototyping, that likely means the Huawei phone can:

- connect to microcontrollers over USB
- exchange serial-like data with MCU boards
- talk to external USB peripherals or adapters
- act as the mobile compute/control node instead of just a consumer handset

The author explicitly said USB OTG is what they mainly use right now for
transferring data from other MCUs.

## What "Secret UART" Means In This Context

`UART` = `Universal Asynchronous Receiver-Transmitter`, a simple low-level
serial interface common in embedded systems.

In this Huawei case, the meaningful points are:

- there is a hidden UART path
- it is exposed through the 3.5 mm headphone jack
- it apparently requires root access to use
- it is still experimental for the author

Possible uses, based on standard UART behavior, include:

- reading low-level logs
- debugging at a lower level than normal Android apps
- interacting with service/debug functions
- exploring boot/runtime behavior

But these are still partly inferential. The author did not yet say exactly what
the UART is currently capable of on this phone, only that they plan to post
again after figuring it out properly.

## Confirmed Vs Inferred

### Confirmed

- Back removal was for root bypass.
- Bridging test points was part of the process.
- `PotatoNV` was used.
- UART is through the 3.5 mm jack.
- Root is needed for UART access.
- USB OTG is the main real-world interface currently in use.
- UART is still experimental.

### Inferred

- The headphone jack may support a debug/serial multiplexed mode rather than
  ordinary audio-only use.
- Root may be needed to switch the phone into UART mode, access hidden device
  nodes, or otherwise enable low-level serial functionality.
- The Huawei phone is currently more useful as a rooted OTG-connected mobile
  hardware node than as a mature UART hacking platform.

## Why This Is Interesting Relative To An Old Rooted Galaxy Avant

The structural similarity to the rooted Samsung Galaxy Avant is already clear:

- old Android phone kept alive beyond normal consumer use
- rooted to extend control and longevity
- still valuable because it interfaces with specialized external hardware
- acts more like a hardware/software bridge node than a normal phone

Main difference so far:

- Huawei example is framed as robotics / MCU prototyping
- Avant example is tied to discontinued sports sensors

So the comparison target is not "are these the same phone?" but:

- what low-level interfaces are available on each
- what rooting enabled on each
- what external hardware each can still uniquely support
- whether the Avant has any analogous hidden serial, OTG, ADB, or sensor-bridge
  potential beyond its current use

## Initial Local Pass: Samsung Galaxy Avant

This section records what was found locally about the rooted Galaxy Avant
before any dedicated device probing or external research.

### Confirmed Local Device Metadata

From `/home/blueaz/.dotfiles/devices/avant/README.md`:

- Device: Samsung Galaxy Avant
- Model: `SM-G386T`
- Codename: `afyonltetmo`
- Carrier: `T-Mobile`
- ROM: `CyanogenMod`
- Android: `5.1.1` (`API 22`)
- Root: `Yes (cm-su)`
- USB debugging: enabled
- Stored ADB serial: `9e2ef102`

From `/home/blueaz/Tools/device-map/README.md`:

- the device is still part of the actively tracked hardware inventory
- it is described concisely as `Galaxy Avant - CyanogenMod, rooted`

### Current ADB Reachability

Local check run on 2026-04-02:

- `adb devices` returned no attached devices

Interpretation:

- ADB tooling is present locally
- the Avant was not connected at the time of this pass
- live device interrogation did not happen in this pass

### Confirmed Operational Role In The Sensor Stack

The strongest local evidence is that the Avant is not just a rooted legacy
phone in the abstract. It is a live part of the tennis-sensor data pipeline.

Evidence:

1. `/home/blueaz/Mac/Tennis/README.md`
   - explicitly says `ztennis.db` is pulled from the rooted Avant at:
     `/data/data/com.zepp.ztennis/databases/`

2. `/home/blueaz/Python/project-phoenix/domains/SensorAgents/TennisAgent/cli/phone_sync_service.py`
   - defines an Android phone sync service that downloads app-private DBs from
     a rooted phone via ADB
   - explicitly targets:
     - Zepp DB:
       `/data/data/com.zepp.ztennis/databases/ztennis.db`
     - Babolat DB:
       `/data/data/com.piq.babolat.playpop/databases/playpop_.db`
   - uses `adb exec-out` plus `su -c 'cat ...'`
   - this only works because the phone is rooted and USB debugging is enabled

3. `/home/blueaz/Mac/MacOSTennisAgent/TennisSensor/CLAUDE.md`
   - documents a manual pull workflow:
     - `adb shell "su -c 'cp /data/data/com.zepp.ztennis/databases/ztennis.db /sdcard/ztennis.db'"`
     - `adb pull /sdcard/ztennis.db /tmp/zepp.db`

4. `/home/blueaz/Downloads/SensorDownload/Current/README.md`
   - confirms a centralized multi-sensor repository
   - identifies active/ongoing sources including:
     - Zepp Universal
     - Babolat Pop
     - Apple Watch
     - Garmin

### What This Means

The rooted Avant is best understood, at minimum, as:

- a compatibility bridge to discontinued sports-sensor ecosystems
- a rooted data-extraction node for Android app-private databases
- a stable old-Android environment that preserves legacy app compatibility

This is more concrete than the earlier generic description of "connected to
discontinued sports sensors." Locally, the evidence shows that the phone is
part of an actual extraction and analysis workflow.

### Sensors Most Clearly Tied To The Avant

Based on local evidence, the clearest current ties are:

- Zepp Tennis / Zepp Universal
  - database: `ztennis.db`
  - private app path on rooted phone:
    `/data/data/com.zepp.ztennis/databases/ztennis.db`

- Babolat Pop
  - database: `playpop_.db`
  - private app path on rooted phone:
    `/data/data/com.piq.babolat.playpop/databases/playpop_.db`

There may be additional sports-sensor relationships, but these two are the
ones directly evidenced by local code and docs.

### Most Important Similarity To The Huawei Case

The important similarity is not just "old rooted Android phone."

It is this:

- both phones remain useful because root plus legacy Android compatibility let
  them serve as bridges to hardware or data paths that newer devices may not
  support as cleanly

Huawei:
- bridge to MCUs and robotics peripherals
- OTG is the main current working interface
- UART is a lower-level experimental extension

Avant:
- bridge to discontinued sports sensors and their private app data
- ADB + root is the main evidenced current working interface
- the meaningful asset is not raw phone performance but preserved ecosystem
  compatibility

### Main Difference From The Huawei Case

Huawei P20 Lite:
- being used as a mobile hardware controller / robotics dev node
- emphasis on OTG, debugging, and possible low-level serial experimentation

Samsung Galaxy Avant:
- being used as a legacy sports-sensor ecosystem anchor
- emphasis on rooted access to app-private databases and reproducible data
  extraction into analysis pipelines

So the Huawei phone is closer to:
- rooted embedded/mobile hardware platform

The Avant is closer to:
- rooted legacy compatibility appliance
- or a sensor-ingest gateway for abandoned app ecosystems

### What We Still Do Not Know Yet

This initial pass did not establish:

- whether the Avant supports USB OTG in practice
- whether the Avant has any known UART/debug-over-headphone-jack path
- whether the sports sensors connect over BLE, classic Bluetooth, or another
  transport
- whether the current phone still actively collects new sensor sessions, or is
  mainly retained for extraction / compatibility / archive access
- whether root was originally obtained to keep the apps functioning, to extract
  the DBs, or both

## Questions For The Next Agent

The next pass should focus on the Samsung Galaxy Avant and compare it to this
Huawei model along the following lines:

1. What rooting state does the Galaxy Avant currently have?
2. Does the Avant support USB OTG in practice?
3. Are there known UART/debug paths on the Avant?
4. Does the Avant expose any useful test points or service/debug interfaces?
5. Which discontinued sports sensors depend on it, and over what transport?
6. Is the Avant best understood as:
   - a compatibility bridge
   - a sensor gateway
   - a hackable embedded Android node
   - or some combination
7. Are there ways to preserve or replicate the Avant's current sensor role on
   newer hardware?
8. Does the phone still pair directly with the sensors for ongoing capture, or
   is it now mainly a rooted extractor for historical and current app data?
9. Are there package/version constraints that explain why the Avant still works
   while newer phones may not?

## Recommended Next Step

Start by documenting the actual current state of the rooted Samsung Galaxy
Avant:

- Android version
- root method / status
- bootloader state if known
- working sensor pairings
- communication method used by those sensors
- whether OTG works
- whether ADB works over USB / Wi-Fi

Then compare that practical profile to the Huawei P20 Lite profile above.

## Provisional Conclusion After Initial Pass

The Huawei and Avant cases are structurally similar but operationally
different.

The Huawei phone is being repurposed as a rooted mobile hardware node for
robotics work, with OTG already useful and UART as an experimental low-level
extension.

The Avant is already evidenced locally as a rooted legacy-sensor bridge. Its
most important current value is that it still provides stable, root-enabled
access to app-private sports-sensor databases that feed downstream analysis
systems.

So if another agent takes over, the right next question is not "can the Avant
also be a robotics board?" The better question is:

"What exact combination of old Android version, root access, sensor pairing,
and app compatibility makes the Avant uniquely valuable, and can any of that be
preserved, replicated, or extended?"
