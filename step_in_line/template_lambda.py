import dill


# Retrieve transform job name from event and return transform job status.
def lambda_handler(event, context):
    with open("myfunc.pickle", "r") as f:
        step = dill.load(f)

    args = []
    for arg in step.depends_on:
        args.append(event[arg])

    result = step.func(*args)
    return {"statusCode": 200, step.name: result}
