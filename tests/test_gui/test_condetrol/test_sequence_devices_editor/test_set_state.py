from collections.abc import Mapping
from typing import Self, reveal_type

import attrs
import pytest
from pytestqt.qtbot import QtBot

from caqtus.device import DeviceName, DeviceConfiguration
from caqtus.device.camera import CameraConfiguration
from caqtus.gui.autogen import generate_device_configuration_editor
from caqtus.gui.condetrol._sequence_devices_editor import (
    SequenceDevicesEditor,
    DraftSequence,
)
from caqtus.gui.condetrol.device_configuration_editors import DeviceConfigurationEditor
from caqtus.types.image import Width, Height
from caqtus.types.image.roi import RectangularROI


@attrs.define
class MockDeviceConfiguration(CameraConfiguration):
    camera_id: int

    @classmethod
    def default(cls) -> Self:
        return cls(
            camera_id=0, roi=RectangularROI((Width(100), Height(100)), 0, 50, 10, 60)
        )


@pytest.fixture
def device_configurations() -> Mapping[DeviceName, DeviceConfiguration]:
    return {DeviceName("camera"): MockDeviceConfiguration.default()}


mock_configuration_editor_factory = generate_device_configuration_editor(
    MockDeviceConfiguration
)


def editor_factory(
    device_configuration: DeviceConfiguration,
) -> DeviceConfigurationEditor:
    if isinstance(device_configuration, MockDeviceConfiguration):
        return mock_configuration_editor_factory(device_configuration)
    else:
        raise NotImplementedError


def test_set_fresh_draft_sets_device_configurations(
    qtbot: QtBot, device_configurations
):
    editor = SequenceDevicesEditor(editor_factory)
    qtbot.addWidget(editor)

    editor.set_fresh_state(DraftSequence(device_configurations=device_configurations))

    state = editor.state()

    assert isinstance(state, DraftSequence)
    assert state.device_configurations == device_configurations
