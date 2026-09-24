"""Reclassify saved results offline after a backfill; no scraping or notifications."""
import json
from pathlib import Path
from geographic_filter import partition_jobs
from scrape_jobs import OUTPUT_DIR, PROFILE_LABEL, PROFILE_SUBTITLE, _render_jobs_html


def refilter(directory):
    reports = {}
    for path in sorted(Path(directory).glob('*.json')):
        if path.name not in ('jobs.json', 'all_jobs.json') and not path.name.endswith('_jobs.json'):
            continue
        data = json.loads(path.read_text(encoding='utf-8'))
        candidates = data.get('jobs', []) + data.get('remote_jobs', []) + data.get('ambiguous_jobs', [])
        groups = partition_jobs(candidates)
        data['jobs'] = groups['in_radius']
        data['geographic_counts'] = {key: len(value) for key, value in groups.items()}
        reports[path.name] = data['geographic_counts']
        if path.name == 'all_jobs.json':
            # Preserve nonlocal master history separately for manual review.
            data['remote_jobs'] = groups['remote']
            data['ambiguous_jobs'] = groups['ambiguous']
        else:
            data['remote_jobs'] = groups['remote']
            data['ambiguous_jobs'] = groups['ambiguous']
            data['new_jobs'] = partition_jobs(data.get('new_jobs', []))['in_radius']
            data['total'] = len(data['jobs'])
            data['new_count'] = len(data['new_jobs'])
            if path.with_suffix('.html').exists():
                path.with_suffix('.html').write_text(_render_jobs_html(
                    title=PROFILE_LABEL, subtitle=PROFILE_SUBTITLE,
                    timestamp=data.get('scraped_at', ''), jobs=data['new_jobs'],
                    empty_message='No new confirmed jobs within 100 miles of Sunnyvale.', accent='#2563eb'), encoding='utf-8')
            if path.with_suffix('.md').exists():
                lines = [f'# {PROFILE_LABEL}', f"{len(data['jobs'])} confirmed jobs within 100 miles of Sunnyvale.",
                         'Remote and ambiguous locations are retained separately in the JSON and dashboard.']
                lines += [f"- [{j.get('title', 'Job')}]({j.get('url', '')}) — {j.get('company', '')} — {j.get('location', '')}" for j in data['jobs']]
                path.with_suffix('.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return reports


if __name__ == '__main__':
    print(json.dumps(refilter(OUTPUT_DIR), indent=2))
