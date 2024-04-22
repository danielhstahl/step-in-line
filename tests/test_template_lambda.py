from step_in_line.template_lambda import combine_payload


def test_returns_payload_if_empty_dict():
    event = {}
    assert combine_payload(event) == {}


def test_returns_payload_if_contains_payload_dict():
    event = {"Payload": {"hi": 4}}
    assert combine_payload(event) == {"hi": 4}


def test_returns_payload_if_contains_payload_arr():
    event = [{"Payload": {"hi": 4}}]
    assert combine_payload(event) == {"hi": 4}


def test_returns_payload_if_contains_payload_arr_multiple():
    event = [{"Payload": {"hi": 4}}, {"Payload": {"bye": 4}}]
    assert combine_payload(event) == {"hi": 4, "bye": 4}
