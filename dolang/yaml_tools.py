"""Compatibility module for YAML handling.

Upstream dolang historically monkey-patched PyYAML Node classes so that `yaml.compose`
output acted like dict/list. We avoid monkey-patching in this repo.

Keep this module so old imports (`from dolang.yaml_tools import yaml`) continue to work.
"""

import yaml  # re-exported for convenience
