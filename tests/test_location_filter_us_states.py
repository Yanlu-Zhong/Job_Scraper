"""The fork uses a strict Sunnyvale radius, not the upstream nationwide filter."""
import pytest
from scrape_jobs import is_target_location

@pytest.mark.parametrize("location", ["Sunnyvale, CA", "San Francisco, California, United States", "San Jose, CA", "Monterey, CA", "Oakland, CA"])
def test_nearby_city(location):
    assert is_target_location(location)

@pytest.mark.parametrize("location", ["Los Angeles, California, United States", "San Diego, CA", "Fresno, CA", "Remote", "Remote, United States", "Hybrid - Austin, TX", "California", "San Francisco Bay Area", "Sunnyvale", "Sunnyvale, TX", "Sunnyvale, CA; New York, NY", "Toronto, Canada", "Unknown, CA", "", None])
def test_not_a_confirmed_nearby_city(location):
    assert not is_target_location(location)
