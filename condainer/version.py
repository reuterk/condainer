"""Condainer - version.py

Single location for the version information.
"""

ver = (0, 1, 9)

def get_version_string():
    """Return the full version number."""
    return '.'.join(map(str, ver))

def get_short_version_string():
    """Return the version number without the patchlevel."""
    return '.'.join(map(str, ver[:-1]))

def get_descriptive_version_string():
    return "Condainer " + get_version_string()
