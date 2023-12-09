from toptica_dlc_pro.runtime import TopticaDLCPro


def test_connection():
    with TopticaDLCPro(
        name="421 laser", host="421 laser", output_power_bounds=(800, None)
    ) as laser:
        print(laser.run_test())
