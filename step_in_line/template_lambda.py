import pickle

"{{PUT_FUNCTION_HERE}}"


def combine_payload(event):
    """Takes payload from event.  If previous "step" was a Parallel state,
            this will be an array of payloads from however many steps
            were in the Parallel state.  In this case, it combines these
            outputs into one large payload.
    Args:
        event (dict): object passed to the Lambda
    """
    payload = {}
    if isinstance(event, dict):
        if "Payload" in event:
            payload = event["Payload"]
    else:  # then event is a list, and contains "multiple" payloads
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
            # extract the output from a previous Lambda
            arg_values.append(payload[arg])
        else:
            # just use the hardcoded argument
            arg_values.append(arg)

    result = "{{PUT_FUNCTION_NAME_HERE}}"(*arg_values)
    ## all outputs from all lambdas are stored in the payload and
    ## passed on to the next lambda(s) in the step.  This mirrors
    ## the local_run from the `Pipeline` class.  On each subsequent
    ## "step" this payload will grow larger.  At the final step, this
    ## will include the output of all intermediary steps.
    return {name: result, **payload}
