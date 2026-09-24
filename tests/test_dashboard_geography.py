"""Execute the actual dashboard filter functions with Node, without a DOM."""
import json
import re
import shutil
import subprocess
from pathlib import Path
import pytest


def test_dashboard_geography_and_defaults():
    if not shutil.which('node'):
        pytest.skip('Node is not installed')
    root = Path(__file__).resolve().parent.parent
    html = (root / 'triage.html').read_text(encoding='utf-8')
    js = "const assert = require('node:assert/strict');\n"
    js += 'const CONFIG = ' + (root / 'config.json').read_text(encoding='utf-8') + ';\n'
    js += 'const state = {blockedCompanies: [], triage: {}, stars: {}};\n'
    js += re.search(r'  const filters = \{.*?\n  \};', html, re.S)[0]
    for name in ['geographicStatus', 'jobDateMs', 'matchesFilters', 'isExcludedTitle']:
        js += re.search(r'  function ' + name + r'\(.*?\n  \}', html, re.S)[0]
    js += """
const local = {date_posted: '13 days ago', geography: {status: 'in_radius', distance_miles: 50}};
assert.equal(filters.days, 14);
assert.equal(filters.geography, 'in_radius');
assert(matchesFilters(local));
assert(!matchesFilters({...local, date_posted: '15 days ago'}));
assert(!matchesFilters({...local, geography: {status:'remote'}}));
assert(!matchesFilters({...local, geography: {status:'ambiguous'}}));
assert(!matchesFilters({...local, geography: undefined}));
assert(!matchesFilters({...local, geography: {status:'in_radius', distance_miles:101}}));
assert(!matchesFilters({...local, geography: {status:'in_radius', distance_miles:null}}));
filters.geography='remote';
assert(matchesFilters({...local, geography: {status:'remote'}}));
assert(!matchesFilters(local));
filters.geography='ambiguous';
assert(matchesFilters({...local, geography: {status:'ambiguous'}}));
filters.geography='in_radius'; filters.days=null;
assert(matchesFilters({...local, date_posted:'100 days ago'}));
assert(!isExcludedTitle('Research Engineer, Speech'));
assert(!isExcludedTitle('Machine Learning Engineering Scientist'));
assert(isExcludedTitle('Research Scientist Intern'));
assert(isExcludedTitle('Director of AI Research'));
const element = {classList:{remove(){}},setAttribute(){}};
const $=()=>element; const renderAll=()=>{}; let sortMode;
"""
    js += re.search(r"  \$\('clear-filters'\)\.onclick = \(\) => \{.*?\n  \};", html, re.S)[0]
    js += "element.onclick(); assert.equal(filters.days,14); assert.equal(filters.geography,'in_radius');"
    assert "[14, '2 Weeks']" in html and "[null, 'Any time']" in html
    subprocess.run(['node'], input=js, encoding='utf-8', check=True)
