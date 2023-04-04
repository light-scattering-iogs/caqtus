from elliptec_ell14.runtime.elliptec_ell14 import ElliptecELL14RotationStage

with ElliptecELL14RotationStage(
    name="hwp", serial_port="COM9", device_id=0
) as hwp_mount:
    print(f"{hwp_mount.position=}")
    hwp_mount.update_parameters(position=400)
    print(f"{hwp_mount.position=}")
