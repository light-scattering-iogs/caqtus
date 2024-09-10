def test_not_in(session_maker):
    with session_maker() as session:
        assert "test_device" not in session.default_device_configurations
