# APC UPS Dashboard

A lightweight web dashboard for monitoring multiple APC UPS units via `apcupsd`. Built with Flask and vanilla JS.

![Dashboard Screenshot](screenshot.png)

## What It Shows

**Overview tab** — at-a-glance status for all connected UPSes:
- Combined power summary (total capacity, total draw, overall load %, units online)
- Per-UPS cards: battery charge, estimated runtime on battery, load with wattage breakdown, input voltage
- Expandable detail panels: model, serial, firmware, battery voltage/date, self-test result, last transfer reason

**Network tab** — service health and remote querying:
- Service status for `apcupsd`, `apcupsd2`, `snmpd`
- SNMP query tool for remote UPS devices

**History tab** — rolling 10-minute graphs per UPS:
- Battery charge, load, and input voltage over time

Data refreshes every 5 seconds.

## Setup

Requires `apcupsd` running for each UPS. The dashboard queries them via `apcaccess`.

```
pip install flask
python3 app.py
```

Runs on port `8088` by default. Override with `DASHBOARD_PORT` env var.

### Configuration

UPS instances are defined in `app.py`:

```python
UPS_INSTANCES = [
    {'id': 'ups1', 'name': 'UPS 1', 'host': '127.0.0.1', 'port': 3551},
    {'id': 'ups2', 'name': 'UPS 2', 'host': '127.0.0.1', 'port': 3552},
]
```

The `config/` directory contains reference configs for:
- `apcupsd/` and `apcupsd2/` — per-UPS daemon configs and event scripts
- `snmp/` — SNMP pass-through scripts exposing both UPSes via separate OID subtrees
- `systemd/` — service files for the second `apcupsd` instance and the dashboard

### Running as a Service

```bash
cp config/systemd/ups-dashboard.service /etc/systemd/system/
systemctl enable --now ups-dashboard
```

## Current Hardware

- **UPS 1**: APC Back-UPS ES 850G2 (520W) on USB
- **UPS 2**: APC Back-UPS BE1050G2 (600W) on USB
