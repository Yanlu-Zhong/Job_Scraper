"""Offline, fail-closed Sunnyvale radius classification using Census place points."""
import json
import math
import re
from pathlib import Path

_DATA = json.loads((Path(__file__).parent / 'data/california_places.json').read_text(encoding='utf-8'))
PLACES = _DATA['places']
CENTER = tuple(PLACES['sunnyvale'][0])
RADIUS_MILES = 100.0
EARTH_RADIUS_MILES = 3958.7613


def distance_miles(latitude, longitude):
    """Great-circle distance from Sunnyvale's Census representative point."""
    lat1, lon1, lat2, lon2 = map(math.radians, (*CENTER, latitude, longitude))
    a = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(min(1, max(0, a))))


def classify_location(location, *, is_remote=None, work_arrangement=''):
    """Only an unambiguous California city + state can qualify as in_radius.

    Remote is not a distance claim. Regions, counties, missing state/city,
    multiple locations, and unknown/duplicate place names require review.
    No substring matching, guessed coordinates, network calls, or paid APIs.
    """
    location = str(location or '').strip()
    result = {'status': 'ambiguous', 'distance_miles': None,
              'reason': 'An unambiguous city and state are required.'}
    remote_text = location + ' ' + str(work_arrangement or '')
    if is_remote is True or re.search(r'\b(remote|work from home|wfh)\b', remote_text, re.I):
        return {**result, 'status': 'remote', 'reason': 'Remote eligibility requires review; not counted within the radius.'}
    clean = re.sub(r'\s*\((?:hybrid|on[- ]?site)\)\s*', ' ', location, flags=re.I).strip()
    clean = re.sub(r'^(?:hybrid|on[- ]?site)\s*[-:]\s*', '', clean, flags=re.I)
    clean = re.sub(r',?\s+(?:United States(?: of America)?|USA|US)$', '', clean, flags=re.I).strip()
    other_states = {'AL','AK','AZ','AR','CO','CT','DE','DC','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY'}
    state_match = re.fullmatch(r'([^,;/|]+),\s*([A-Z]{2})(?:\s+\d{5}(?:-\d{4})?)?', clean, re.I)
    if state_match and state_match[2].upper() in other_states:
        return {**result, 'status': 'outside_radius', 'reason': 'The stated US state is outside the Sunnyvale radius.'}
    # Require the whole string to match, so multi-office and regional listings
    # cannot sneak through merely by mentioning a nearby city.
    match = re.fullmatch(r'([^,;/|]+),\s*(CA|California)(?:\s+\d{5}(?:-\d{4})?)?', clean, re.I)
    if not match:
        return result
    city = re.sub(r'\s+', ' ', match[1]).strip().lower()
    points = PLACES.get(city, [])
    if len(points) != 1:
        return {**result, 'reason': 'City is unknown or has multiple Census locations.'}
    distance = distance_miles(*points[0])
    return {'status': 'in_radius' if distance <= RADIUS_MILES else 'outside_radius',
            'distance_miles': round(distance, 3), 'city': city,
            'latitude': points[0][0], 'longitude': points[0][1],
            'reason': 'Straight-line distance between Census place points (not driving distance).'}


def classify_job(job):
    return classify_location(job.get('location'), is_remote=job.get('is_remote'),
                             work_arrangement=job.get('work_arrangement', ''))


def partition_jobs(jobs):
    groups = {key: [] for key in ('in_radius', 'remote', 'ambiguous', 'outside_radius')}
    for job in jobs:
        job = dict(job)
        job['geography'] = classify_job(job)
        groups[job['geography']['status']].append(job)
    return groups
