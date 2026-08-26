from . import (
    artsjobs,
    barbican,
    british_museum,
    cambridge,
    kcl,
    national_gallery,
    national_museums,
    national_trust,
    nhm,
    royal_academy,
    southbank,
    tate,
    vam,
    waltham_forest,
    william_morris_gallery,
)

# Every source the orchestrator runs each pass. Keep the module reference (not
# the function) so main.py can label status/errors by module name uniformly.
SOURCES = [
    british_museum,
    tate,
    kcl,
    vam,
    barbican,
    artsjobs,
    southbank,
    national_gallery,
    nhm,
    royal_academy,
    cambridge,
    waltham_forest,
    national_trust,
    william_morris_gallery,
    national_museums,
]
