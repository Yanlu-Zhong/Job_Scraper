import json
import math
import pytest
from geographic_filter import CENTER, EARTH_RADIUS_MILES, classify_job, classify_location, distance_miles, partition_jobs


def test_distance_boundary_without_rounding():
    for miles in [0, 99.999, 100.001, 150]:
        latitude = CENTER[0] + math.degrees(miles / EARTH_RADIUS_MILES)
        assert distance_miles(latitude, CENTER[1]) == pytest.approx(miles)


def test_radius_boundary_uses_unrounded_distance(monkeypatch):
    import geographic_filter as g
    monkeypatch.setitem(g.PLACES, 'boundary', [[0, 0]])
    monkeypatch.setattr(g, 'distance_miles', lambda *args: 100.0001)
    assert classify_location('Boundary, CA')['status'] == 'outside_radius'
    monkeypatch.setattr(g, 'distance_miles', lambda *args: 100)
    assert classify_location('Boundary, CA')['status'] == 'in_radius'


@pytest.mark.parametrize('location', ['California', 'San Francisco Bay Area', 'Sunnyvale', '', 'Alta Sierra, CA', 'Sunnyvale / San Diego, CA', 'Sunnyvale, CA, Canada'])
def test_ambiguous_locations_fail_closed(location):
    assert classify_location(location)['status'] == 'ambiguous'


def test_remote_is_never_a_distance_claim():
    for job in [{'location': 'Remote'}, {'location': 'Sunnyvale, CA', 'is_remote': True},
                {'location': 'Sunnyvale, CA', 'work_arrangement': 'Remote'}]:
        result = classify_job(job)
        assert result['status'] == 'remote'
        assert result['distance_miles'] is None


def test_hybrid_has_a_known_office_location():
    assert classify_location('Hybrid - Sunnyvale, CA')['status'] == 'in_radius'
    assert classify_location('Sunnyvale, CA (Hybrid)')['status'] == 'in_radius'


def test_partition_does_not_mutate_input():
    original = {'location': 'Sunnyvale, CA'}
    groups = partition_jobs([original, {'location': 'Remote'}, {'location': 'California'}, {'location': 'Los Angeles, CA'}])
    assert all(len(jobs) == 1 for jobs in groups.values())
    assert 'geography' not in original


def test_save_boundary_and_blocked_run_fallback(tmp_output_dir, monkeypatch):
    import scrape_jobs as s
    import notify
    notified = []
    monkeypatch.setattr(notify, 'notify_new_jobs', lambda jobs, source: notified.extend(jobs))
    candidates = [{'url': f'https://example.com/jobs/{i}', 'title': 'Research Scientist',
                   'company': 'Example', 'ats': 'Indeed', 'location': location}
                  for i, location in enumerate(['Sunnyvale, CA', 'Los Angeles, CA', 'California', 'Remote'])]
    s.save_indeed_results(candidates)
    data = json.loads((tmp_output_dir / 'indeed_jobs.json').read_text())
    master = json.loads((tmp_output_dir / 'all_jobs.json').read_text())
    assert len(data['jobs']) == len(data['new_jobs']) == len(master['jobs']) == len(notified) == 1
    assert len(data['remote_jobs']) == len(data['ambiguous_jobs']) == 1
    assert len(master['remote_jobs']) == len(master['ambiguous_jobs']) == 1
    assert data['geographic_counts']['outside_radius'] == 1
    assert data['jobs'][0]['geography']['status'] == 'in_radius'
    assert len(s._load_prev_jobs(str(tmp_output_dir / 'indeed_jobs.json'))) == 3


def test_master_does_not_keep_a_local_job_that_becomes_remote(tmp_output_dir, monkeypatch):
    import scrape_jobs as s
    import notify
    monkeypatch.setattr(notify, 'notify_new_jobs', lambda *args: None)
    job = {'url': 'https://example.com/jobs/1', 'title': 'Research Scientist', 'company': 'Example', 'ats': 'Indeed', 'location': 'Sunnyvale, CA'}
    s.save_indeed_results([job])
    s.save_indeed_results([{**job, 'is_remote': True}])
    data = json.loads((tmp_output_dir / 'all_jobs.json').read_text())
    assert data['jobs'] == []
    assert len(data['remote_jobs']) == 1


def test_refilter_preserves_job_metadata_and_separates_review(tmp_output_dir):
    from refilter_saved_jobs import refilter
    path = tmp_output_dir / 'indeed_jobs.json'
    jobs = [{'url': str(i), 'location': location, 'notes': 'Keep my note'} for i, location in enumerate(['Sunnyvale, CA', 'Remote', 'California', 'Los Angeles, CA'])]
    path.write_text(json.dumps({'jobs': jobs, 'new_jobs': jobs, 'scraped_at': 'original'}))
    report = refilter(tmp_output_dir)
    data = json.loads(path.read_text())
    assert data['total'] == data['new_count'] == 1
    assert data['jobs'][0]['notes'] == 'Keep my note'
    assert data['scraped_at'] == 'original'
    assert len(data['remote_jobs']) == len(data['ambiguous_jobs']) == 1
    assert report['indeed_jobs.json']['outside_radius'] == 1
