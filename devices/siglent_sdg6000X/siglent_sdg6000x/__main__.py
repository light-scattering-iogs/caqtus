import logging

from modulation import AmplitudeModulation
from siglent_sdg6000X import (
    SiglentSDG6000XWaveformGenerator,
    SiglentSDG6000XChannel,
)
from waveforms import SineWave, DCVoltage

logging.basicConfig()

if __name__ == "__main__":
    with SiglentSDG6000XWaveformGenerator(
        name="Siglent SDG6022X A",
        visa_resource_name="TCPIP0::192.168.137.180::inst0::INSTR",
        channel_configurations=(
            SiglentSDG6000XChannel(
                output_enabled=True,
                output_load="HZ",
                waveform=SineWave(frequency=30, amplitude=4),
                modulation=AmplitudeModulation(source="EXT"),
            ),
            SiglentSDG6000XChannel(
                output_enabled=True,
                output_load="HZ",
                waveform=DCVoltage(value=+6),
            ),
        ),
    ) as device:
        device.channel_configurations[0].waveform = SineWave(frequency=2, amplitude=4)
        device.update_parameters()
