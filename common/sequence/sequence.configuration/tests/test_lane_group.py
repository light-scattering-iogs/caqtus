from sequence.configuration import LaneGroup, LaneReference


def test_lane_group():
    assert LaneReference("lane_0")
    group = LaneGroup(
        "group_0",
        children=[
            LaneReference("lane_0"),
            LaneGroup("group_1", children=[LaneReference("lane_1")]),
        ],
    )
    assert group == LaneGroup.from_yaml(group.to_yaml())
    print(group.descendants)
