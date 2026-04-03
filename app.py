#!/usr/bin/env python3
"""
UPS Network Dashboard - Monitor multiple UPS units via apcaccess and SNMP
Run as a service on a high port for easy access
"""

from flask import Flask, render_template, jsonify, request
import subprocess
import re
import os
import socket
import time
from datetime import datetime
from collections import deque
import threading

app = Flask(__name__)

# Configuration
PORT = int(os.environ.get('DASHBOARD_PORT', 8088))
SNMP_COMMUNITY = os.environ.get('SNMP_COMMUNITY', 'public')
HISTORY_SIZE = 120  # Keep 10 minutes of data at 5-second intervals

# UPS instances: list of (name, host, port) tuples
UPS_INSTANCES = [
    {'id': 'ups1', 'name': 'UPS 1', 'host': '127.0.0.1', 'port': 3551},
    {'id': 'ups2', 'name': 'UPS 2', 'host': '127.0.0.1', 'port': 3552},
]

# History storage for graphs (per UPS)
history = {}
history_lock = threading.Lock()

for ups in UPS_INSTANCES:
    history[ups['id']] = {
        'timestamps': deque(maxlen=HISTORY_SIZE),
        'battery_charge': deque(maxlen=HISTORY_SIZE),
        'load_percent': deque(maxlen=HISTORY_SIZE),
        'input_voltage': deque(maxlen=HISTORY_SIZE),
    }

# APC SNMP OIDs
APC_OIDS = {
    'model': '.1.3.6.1.4.1.318.1.1.1.1.1.1.0',
    'battery_charge': '.1.3.6.1.4.1.318.1.1.1.2.2.1.0',
    'battery_temp': '.1.3.6.1.4.1.318.1.1.1.2.2.2.0',
    'time_remaining': '.1.3.6.1.4.1.318.1.1.1.2.2.3.0',
    'battery_date': '.1.3.6.1.4.1.318.1.1.1.2.2.4.0',
    'input_voltage': '.1.3.6.1.4.1.318.1.1.1.3.2.1.0',
    'input_frequency': '.1.3.6.1.4.1.318.1.1.1.3.2.4.0',
    'last_transfer': '.1.3.6.1.4.1.318.1.1.1.3.2.5.0',
    'output_voltage': '.1.3.6.1.4.1.318.1.1.1.4.2.1.0',
    'load_percent': '.1.3.6.1.4.1.318.1.1.1.4.2.3.0',
}


def get_apcaccess(host='127.0.0.1', port=3551):
    """Get UPS status from apcaccess command"""
    try:
        result = subprocess.run(
            ['apcaccess', '-h', f'{host}:{port}'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return parse_apcaccess(result.stdout)
        return None
    except FileNotFoundError:
        return {'error': 'apcaccess not installed'}
    except Exception as e:
        return {'error': str(e)}


def parse_apcaccess(output):
    """Parse apcaccess output into dictionary"""
    data = {}
    for line in output.split('\n'):
        match = re.match(r'^\s*([^:]+)\s*:\s*(.+?)\s*$', line)
        if match:
            key = match.group(1).strip()
            value = match.group(2).strip()
            data[key] = value
    return data


def extract_ups_data(status):
    """Extract standardized UPS data from apcaccess output"""
    return {
        'model': status.get('MODEL', 'Unknown'),
        'status': status.get('STATUS', 'Unknown'),
        'battery_charge': status.get('BCHARGE', '0').replace('%', '').replace(' Percent', ''),
        'battery_voltage': status.get('BATTV', 'Unknown'),
        'battery_temperature': status.get('ITEMP', 'Unknown'),
        'time_left': status.get('TIMELEFT', 'Unknown'),
        'input_voltage': status.get('LINEV', 'Unknown'),
        'input_frequency': status.get('LINEFREQ', 'Unknown'),
        'output_voltage': status.get('OUTPUTV', 'Unknown'),
        'load_percent': status.get('LOADPCT', '0').replace('%', '').replace(' Percent', ''),
        'last_transfer': status.get('LASTXFER', 'Unknown'),
        'battery_date': status.get('BATTDATE', 'Unknown'),
        'serial_number': status.get('SERIALNO', 'Unknown'),
        'firmware': status.get('FIRMWARE', 'Unknown'),
        'selftest': status.get('SELFTEST', 'Unknown'),
        'nom_power': status.get('NOMPOWER', 'Unknown'),
        'upsname': status.get('UPSNAME', 'Unknown'),
    }


def snmp_get(host, oid, community=None):
    """Get a single SNMP OID value"""
    if community is None:
        community = SNMP_COMMUNITY
    try:
        result = subprocess.run(
            ['snmpget', '-v', '2c', '-c', community, '-t', '2', '-r', '1', host, oid],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            if '=' in output:
                value_part = output.split('=', 1)[1].strip()
                if ':' in value_part:
                    value = value_part.split(':', 1)[1].strip()
                    value = value.strip('"')
                    return value
        return None
    except Exception:
        return None


def snmp_query_ups(host, community=None):
    """Query all UPS data via SNMP"""
    if community is None:
        community = SNMP_COMMUNITY

    data = {}
    for key, oid in APC_OIDS.items():
        value = snmp_get(host, oid, community)
        data[key] = value

    return data


def check_port_open(host, port, timeout=2):
    """Check if a TCP port is open"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False


def check_snmp_host(host, community=None):
    """Check if SNMP is responding on a host"""
    if community is None:
        community = SNMP_COMMUNITY
    try:
        result = subprocess.run(
            ['snmpget', '-v', '2c', '-c', community, '-t', '2', '-r', '1',
             host, '.1.3.6.1.2.1.1.1.0'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False


def get_service_status(service_name):
    """Check if a systemd service is running"""
    try:
        result = subprocess.run(
            ['systemctl', 'is-active', service_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout.strip() == 'active'
    except:
        return False


def get_process_running(process_name):
    """Check if a process is running"""
    try:
        result = subprocess.run(
            ['pgrep', '-x', process_name],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False


@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html', ups_instances=UPS_INSTANCES)


@app.route('/api/status')
def api_status():
    """Get status for all UPS units"""
    results = []

    for ups_cfg in UPS_INSTANCES:
        status = get_apcaccess(ups_cfg['host'], ups_cfg['port'])

        if status and 'error' not in status:
            ups_data = extract_ups_data(status)

            # Update history for this UPS
            ups_id = ups_cfg['id']
            with history_lock:
                h = history[ups_id]
                h['timestamps'].append(datetime.now().isoformat())
                try:
                    h['battery_charge'].append(float(ups_data['battery_charge']))
                except:
                    h['battery_charge'].append(None)
                try:
                    h['load_percent'].append(float(ups_data['load_percent']))
                except:
                    h['load_percent'].append(None)
                try:
                    v = ups_data['input_voltage'].replace(' Volts', '').replace('V', '')
                    h['input_voltage'].append(float(v))
                except:
                    h['input_voltage'].append(None)

            results.append({
                'id': ups_cfg['id'],
                'name': ups_cfg['name'],
                'success': True,
                'ups': ups_data,
            })
        else:
            results.append({
                'id': ups_cfg['id'],
                'name': ups_cfg['name'],
                'success': False,
                'error': status.get('error', 'Unable to communicate with UPS') if status else 'UPS not responding',
            })

    return jsonify({
        'success': True,
        'timestamp': datetime.now().isoformat(),
        'source': 'apcaccess',
        'units': results,
    })


@app.route('/api/snmp-status')
def api_snmp_status():
    """Query UPS via SNMP"""
    host = request.args.get('host', '127.0.0.1')
    community = request.args.get('community', SNMP_COMMUNITY)

    if not check_snmp_host(host, community):
        return jsonify({
            'success': False,
            'error': f'SNMP not responding on {host}'
        }), 503

    data = snmp_query_ups(host, community)

    if data.get('model'):
        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'source': 'snmp',
            'host': host,
            'ups': {
                'model': data.get('model', 'Unknown'),
                'battery_charge': data.get('battery_charge', '0'),
                'battery_temperature': data.get('battery_temp', 'Unknown'),
                'time_left': data.get('time_remaining', 'Unknown'),
                'input_voltage': data.get('input_voltage', 'Unknown'),
                'input_frequency': data.get('input_frequency', 'Unknown'),
                'output_voltage': data.get('output_voltage', 'Unknown'),
                'load_percent': data.get('load_percent', '0'),
                'last_transfer': data.get('last_transfer', 'Unknown'),
                'battery_date': data.get('battery_date', 'Unknown'),
            }
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Could not retrieve UPS data via SNMP'
        }), 503


@app.route('/api/network-check')
def api_network_check():
    """Check network and service status"""
    host = request.args.get('host', '127.0.0.1')
    community = request.args.get('community', SNMP_COMMUNITY)

    checks = {
        'snmp_port': check_port_open(host, 161) if host != '127.0.0.1' else True,
        'snmp_responding': check_snmp_host(host, community),
        'apcupsd_running': get_process_running('apcupsd'),
        'snmpd_running': get_process_running('snmpd'),
        'apcupsd_service': get_service_status('apcupsd'),
        'apcupsd2_service': get_service_status('apcupsd2'),
        'snmpd_service': get_service_status('snmpd'),
    }

    return jsonify({
        'success': True,
        'timestamp': datetime.now().isoformat(),
        'host': host,
        'checks': checks
    })


@app.route('/api/history')
def api_history():
    """Get historical data for charts"""
    ups_id = request.args.get('ups', 'ups1')
    with history_lock:
        if ups_id in history:
            h = history[ups_id]
            return jsonify({
                'success': True,
                'ups_id': ups_id,
                'timestamps': list(h['timestamps']),
                'battery_charge': list(h['battery_charge']),
                'load_percent': list(h['load_percent']),
                'input_voltage': list(h['input_voltage']),
            })
        else:
            return jsonify({'success': False, 'error': f'Unknown UPS: {ups_id}'}), 404


@app.route('/api/scan')
def api_scan():
    """Scan a subnet for UPS devices"""
    subnet = request.args.get('subnet', '192.168.1')
    community = request.args.get('community', SNMP_COMMUNITY)

    found = []
    for i in range(1, 21):
        host = f'{subnet}.{i}'
        if check_snmp_host(host, community):
            data = snmp_query_ups(host, community)
            if data.get('model'):
                found.append({
                    'host': host,
                    'model': data.get('model'),
                    'battery_charge': data.get('battery_charge'),
                    'load_percent': data.get('load_percent'),
                })

    return jsonify({
        'success': True,
        'found': found
    })


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})


if __name__ == '__main__':
    print(f"Starting UPS Network Dashboard on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)
