from siglent_sdg6000x.runtime import SiglentSDG6000XWaveformGenerator


def test_list_resources():
    print(SiglentSDG6000XWaveformGenerator.list_all_visa_resources())
