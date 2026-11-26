import pytest


@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations):
    """Let the test Home Assistant load custom_components/poltergeist."""
