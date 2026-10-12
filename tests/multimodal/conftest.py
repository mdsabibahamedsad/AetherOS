"""Multimodal test fixtures configuration."""

# Import all fixtures from the fixtures module
from tests.multimodal.fixtures.conftest import *

# This ensures pytest discovers all fixtures
pytest_plugins = ["tests.multimodal.fixtures.conftest"]