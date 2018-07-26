from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def root():
    return Path(__file__).parent.parent
