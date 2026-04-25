import os
import requests
from flask import current_app


class SNCFClient:
    BASE_URL = 'https://api.sncf.com/v1'

    def __init__(self):
        self._token = None

    @property
    def token(self):
        if self._token is None:
            self._token = current_app.config.get('SNCF_API_TOKEN', os.environ.get('SNCF_API_TOKEN', ''))
        return self._token

    @property
    def headers(self):
        return {'Authorization': self._token}

    def search_stations(self, query):
        """Search for stations by name. Returns list of {id, name}."""
        try:
            resp = requests.get(
                f'{self.BASE_URL}/coverage/sncf/places',
                params={'q': query, 'count': 10},
                headers=self.headers,
                timeout=10,
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            places = data.get('places', [])
            stations = []
            seen = set()
            for p in places:
                if p.get('embedded_type') == 'stop_area':
                    sid = p.get('id', '')
                    name = p.get('name', '')
                    if sid not in seen:
                        seen.add(sid)
                        stations.append({'id': sid, 'name': name})
            return stations
        except Exception:
            return []

    def get_disruptions(self, lines=None):
        """Get current disruptions from SNCF API."""
        try:
            resp = requests.get(
                f'{self.BASE_URL}/coverage/sncf/disruptions',
                headers=self.headers,
                timeout=15,
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            return data.get('disruptions', [])
        except Exception:
            return []

    def get_traffic_info(self, departure_id, arrival_id):
        """Get traffic/disruption info between two stations."""
        try:
            # Query disruptions for the line/region
            resp = requests.get(
                f'{self.BASE_URL}/coverage/sncf/physical_modes/physical_mode:Rail/traffic_reports',
                headers=self.headers,
                timeout=15,
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            reports = data.get('traffic_reports', [])
            disruptions = []
            for report in reports:
                for line in report.get('lines', []):
                    disruptions.extend(line.get('disruptions', []))

            # Also try journey-based approach
            now = datetime.now()
            resp2 = requests.get(
                f'{self.BASE_URL}/coverage/sncf/journeys',
                params={
                    'from': departure_id,
                    'to': arrival_id,
                    'datetime': now.strftime('%Y%m%dT%H%M%S'),
                },
                headers=self.headers,
                timeout=15,
            )
            if resp2.status_code == 200:
                data2 = resp2.json()
                for journey in data2.get('journeys', []):
                    for section in journey.get('sections', []):
                        for disp in section.get('display_informations', {}).get('disruptions', []):
                            disruptions.append(disp)

            return disruptions
        except Exception:
            return []


sncf_client = SNCFClient()

# Fix missing import
from datetime import datetime