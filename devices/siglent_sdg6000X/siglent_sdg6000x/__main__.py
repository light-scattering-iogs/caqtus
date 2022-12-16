import logging

from modulation import AmplitudeModulation, FrequencyModulation
from siglent_sdg6000X import (
    SiglentSDG6000XWaveformGenerator,
    SiglentSDG6000XChannel,
)
from waveforms import SineWave

logging.basicConfig()

if __name__ == "__main__":
    with SiglentSDG6000XWaveformGenerator(
        name="Siglent SDG6022X A",
        visa_resource_name="TCPIP0::192.168.137.180::inst0::INSTR",
        channel_configurations=(
            SiglentSDG6000XChannel(
                output_enabled=True,
                waveform=SineWave(frequency=1e3, amplitude=1),
                modulation=AmplitudeModulation(source="CH2", depth=10),
            ),
            SiglentSDG6000XChannel(
                output_enabled=True,
                waveform=SineWave(frequency=100, amplitude=4, offset=2),
            ),
        ),
    ) as device:
        print(device.get_identity())
