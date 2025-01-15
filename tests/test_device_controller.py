# tests/test_device_controller.py

import pytest
from unittest.mock import Mock, patch
from src.controllers.device_controller import DeviceController


@pytest.fixture
def mock_u2():
    with patch('uiautomator2.connect') as mock_connect:
        mock_device = Mock()
        mock_device.window_size = Mock(return_value=(1080, 2400))
        mock_connect.return_value = mock_device
        yield mock_device


@pytest.fixture
def device_controller(mock_u2):
    return DeviceController('test_device_id')


def test_device_controller_initialization(device_controller):
    """Test if DeviceController initializes correctly."""
    assert device_controller.device_id == 'test_device_id'
    assert device_controller.music_apps is not None
    assert device_controller.base_packages is not None


def test_get_app_name_from_package(device_controller):
    """Test app name resolution from package name."""
    # Test known package
    assert "YouTube Music" in device_controller.get_app_name_from_package(
        "com.google.android.apps.youtube.music"
    )

    # Test clone package
    assert "Clone" in device_controller.get_app_name_from_package(
        "com.apple.android.music.clone"
    )

    # Test unknown package
    assert "Unknown App" in device_controller.get_app_name_from_package(
        "com.unknown.app"
    )


@pytest.mark.asyncio
async def test_check_running_music_apps(device_controller, mock_u2):
    """Test checking running music apps."""
    # Mock the running apps check
    with patch('src.utils.adb_commands.execute_adb_command') as mock_execute:
        mock_execute.return_value = """
        Recent #0: com.google.android.apps.youtube.music
        Recent #1: com.apple.android.music.clone
        """

        running_apps = device_controller.check_running_music_apps()
        assert running_apps is not None
        assert len(running_apps) > 0


def test_control_isoclipboard(device_controller, mock_u2):
    """Test IsoClipboard control."""
    with patch.object(device_controller, 'control_isoclipboard') as mock_control:
        device_controller.control_isoclipboard('youtube')
        mock_control.assert_called_once_with('youtube')