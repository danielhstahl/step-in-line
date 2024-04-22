import pickle

"{{PUT_FUNCTION_HERE}}"


def combine_payload(event):
    payload = {}
    if isinstance(event, dict):
        if "Payload" in event:
            payload = event["Payload"]
    else:  # then event is a list
        for ev in event:
            if "Payload" in ev:
                payload = {**payload, **ev["Payload"]}
    return payload


# Retrieve transform job name from event and return transform job status.
def lambda_handler(event, context):
    print(event)

    with open("args.pickle", "rb") as f:
        args = pickle.load(f)

    print(args)

    with open("name.pickle", "rb") as f:
        name = pickle.load(f)

    arg_values = []
    payload = combine_payload(event)
    for arg in args:
        if arg in payload:
            arg_values.append(payload[arg])
        else:
            arg_values.append(arg)

    result = "{{PUT_FUNCTION_NAME_HERE}}"(*arg_values)
    return {name: result, **payload}
