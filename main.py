#!/usr/bin/env python3

# Imports
import os
import sys
import time
import traceback
from prometheus_client import start_http_server, Gauge, REGISTRY, PROCESS_COLLECTOR, PLATFORM_COLLECTOR, GC_COLLECTOR
import requests

# Number of seconds between 2 metrics collection
COLLECT_INTERVAL = os.getenv('EXPORTER_COLLECT_INTERVAL', 30)
# Prefix for all metrics
METRIC_NAMESPACE = os.getenv('METRIC_NAMESPACE', 'jellyfin')

# Get Jellyfin information from env
JELLYFIN_URL = os.getenv('JELLYFIN_URL', 'http://localhost:8096')
JELLYFIN_TOKEN = os.getenv('JELLYFIN_TOKEN')
if JELLYFIN_TOKEN is None:
    print("JELLYFIN_TOKEN must be defined")
    sys.exit(1)

# Remove unwanted Prometheus metrics
REGISTRY.unregister(GC_COLLECTOR)
REGISTRY.unregister(PLATFORM_COLLECTOR)
REGISTRY.unregister(PROCESS_COLLECTOR)

# Start Prometheus exporter server
start_http_server(8000)


#########################################
##### Initialize Prometheus metrics #####
#########################################

# User gauges
users_gauge = Gauge(f'{METRIC_NAMESPACE}_users_count', 'Count of user account')
items_gauge= Gauge(f'{METRIC_NAMESPACE}_items_count', 'Count of media items by type', ['type'])
active_streams_gauge= Gauge(f'{METRIC_NAMESPACE}_active_streams_count', 'The total number of streams', ['user'])
active_direct_streams_gauge = Gauge(f'{METRIC_NAMESPACE}_active_streams_direct_count', 'The number of streams which are currently being direct streams')
active_transcode_streams_gauge = Gauge(f'{METRIC_NAMESPACE}_active_streams_transcode_count', 'The number of streams which are currently being transcoded')
streams_bandwidth_gauge = Gauge(f'{METRIC_NAMESPACE}_streams_bandwidth_bits', 'The total bandwidth currently being streamed')


def get_users():
    """
    Get all Jellyfin users from API
    """
    url = JELLYFIN_URL + "/Users"
    headers = {"X-Emby-Token": JELLYFIN_TOKEN}
    try:
        r = requests.get(url, headers=headers)
        users = r.json()
    except Exception:
        print(traceback.format_exc())
        return []
    return users

def get_items():
    """
    Get all Jellyfin items from API
    """
    url = JELLYFIN_URL + "/Items/Counts"
    headers = {"X-Emby-Token": JELLYFIN_TOKEN}
    try:
        r = requests.get(url, headers=headers)
        items = r.json()
    except Exception:
        print(traceback.format_exc())
        return []
    return items

def get_session():
    """
    Get current sessions from Jellyfin API
    """
    url = JELLYFIN_URL + "/Sessions?ActiveWithinSeconds=" + str(COLLECT_INTERVAL)
    headers = {"X-Emby-Token": JELLYFIN_TOKEN}
    try:
        r = requests.get(url, headers=headers)
        sessions = r.json()
    except Exception:
        print(traceback.format_exc())
        return []
    return sessions

def get_sessions_active_count(sessions):
    """
    Count active sessions per user from a list of sessions returned from Jellyfin API
    """
    sessions_per_user = {}
    for session in sessions:
        try:
            if session["PlayState"]["IsPaused"] == False and "NowPlayingItem" in session.keys():
                if session["UserName"] not in sessions_per_user.keys():
                    sessions_per_user[session["UserName"]] = 1
                else:
                    sessions_per_user[session["UserName"]] += 1
        except Exception:
            print(traceback.format_exc())
    return sessions_per_user

def get_total_bandwidth(sessions):
    """
    Count total bandwidth being streamed from sessions list from Jellyfin API
    """
    bandwidth_total = 0.0
    for session in sessions:
        try:
            if session["PlayState"]["IsPaused"] == False and "NowPlayingItem" in session.keys():
                for stream in session["NowPlayingItem"]["MediaStreams"]:
                    if "BitRate" in stream.keys() and isinstance(stream["BitRate"], int):
                        bandwidth_total += stream["BitRate"]
        except Exception:
            print(traceback.format_exc())
    return bandwidth_total

def get_stream_types(sessions):
    """
    Count direct and transcoded streams count from sessions list
    """
    transcoded = 0
    direct = 0
    for session in sessions:
        try:
            if session["PlayState"]["IsPaused"] == False and "NowPlayingItem" in session.keys():
                if "TranscodingInfo" in session.keys() and (session["TranscodingInfo"]["IsVideoDirect"] or session["TranscodingInfo"]["TranscodeReasons"] is None):
                    direct += 1
                else:
                    transcoded += 1
        except Exception:
            print(traceback.format_exc())
    return direct, transcoded


def refresh_metrics():
    """
    Refresh all Prometheus metrics from Jellyfin API
    """

    # Get data from Jellyfin API
    users = get_users()
    items = get_items()
    sessions = get_session()

    # Process data
    active_sessions = get_sessions_active_count(sessions)
    bandwidth_total = get_total_bandwidth(sessions)
    direct_streams, transcoded_streams = get_stream_types(sessions)

    # Refresh gauges
    users_gauge.set(len(users))
    for item in items:
        items_gauge.labels(type=item).set(items[item])
    active_streams_gauge._metrics.clear()
    for active_user in active_sessions:
        active_streams_gauge.labels(user=active_user).set(active_sessions[active_user])
    streams_bandwidth_gauge.set(bandwidth_total)
    active_direct_streams_gauge.set(direct_streams)
    active_transcode_streams_gauge.set(transcoded_streams)

# Loop forever
while True:
    refresh_metrics()
    # Wait before next metrics collection
    time.sleep(COLLECT_INTERVAL)
