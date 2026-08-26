from . import (
    artsjobs,
    barbican,
    british_museum,
    kcl,
    national_gallery,
    southbank,
    tate,
    vam,
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
]
