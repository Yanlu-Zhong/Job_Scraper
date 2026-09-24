# Sunnyvale location filter

`california_places.json` contains California place names and representative latitude/longitude points from the public-domain [2025 US Census Places Gazetteer](https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2025_Gazetteer/2025_gaz_place_06.txt). City, town, and CDP suffixes are removed. Duplicate names retain every point and are treated as ambiguous.

The center is the Sunnyvale Census point (37.385797, -122.026316). The scraper computes great-circle distance and admits a resolved city only at **100 miles or less**, using the unrounded distance. This is a city-point estimate, not driving distance or verification of an employer's street address. Unknown cities, regional labels, multiple locations, and missing state information fail closed into a separate review list. Remote jobs also go to a separate list, without any claim that the applicant is eligible or physically within the radius.

The same classification runs at the shared output boundary for every source and for blocked-run fallbacks. Only local matches enter `jobs`, `new_jobs`, digests, and the cumulative master; `remote_jobs` and `ambiguous_jobs` remain separately reviewable in each source JSON and the dashboard. No network geocoding, API key, or paid service is required. `config.json` is unchanged.
