import os
import tempfile
import pytest

from lwe.core.config import Config
import lwe.core.util as util

TEST_DIR = os.path.join(tempfile.gettempdir(), 'lwe_test')
TEST_CONFIG_DIR = os.path.join(TEST_DIR, 'config')
TEST_DATA_DIR = os.path.join(TEST_DIR, 'data')
TEST_PROFILE = 'test'


@pytest.fixture
def test_config():
    util.remove_and_create_dir(TEST_CONFIG_DIR)
    util.remove_and_create_dir(TEST_DATA_DIR)
    config = Config(TEST_CONFIG_DIR, TEST_DATA_DIR, profile=TEST_PROFILE)
    return config
