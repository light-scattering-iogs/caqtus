from swabian_pulse_streamer.runtime.swabian_pulse_streamer import SwabianPulseStreamer


def test_connection():
    pulse_streamer = SwabianPulseStreamer(
        name="pulse streamer", ip_address="192.168.137.187", time_step=1
    )

    with pulse_streamer:
        pass
