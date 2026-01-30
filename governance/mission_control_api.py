"""Compatibility wrapper.

The Mission Control API has been migrated to `runtime.api.mission_control`.
This module remains to avoid breaking older imports.
"""

from runtime.api.mission_control import app
