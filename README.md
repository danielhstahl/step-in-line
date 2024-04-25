## Step-in-line

[AWS Step Functions](https://aws.amazon.com/step-functions/) is awesome.  It is a fully managed serverless AWS offering, so there is no upkeep or maintenance required.  Unfortunately, programatically created workflows of Lambda functions using Terraform requires creating complex JSON definitions.  `step-in-line` generates these JSON definitions automatically from Python decorators.  In addition, it generates the Terraform files needed for deploying Step Functions, Lambdas, and EventBridge events.    

The API is intentionally similar to the Sagemaker Pipeline API.  

## Usage

### Install

Full install (recommended):

`pip install step-in-line[terraform]`

Don't include Terraform related dependencies:

`pip install step-in-line`.

### Example Pipeline
```python

from step_in_line.step import step
from step_in_line.pipeline import Pipeline
from step_in_line.tf import StepInLine, rename_tf_output
from pathlib import Path

lambda_iam_policy = "" # put an IAM policy here, formatted as JSON

@step(
    # function names must be unique, or you can pass a name to the step to 
    # ensure uniqueness
    name = "preprocess_unique",
    python_runtime = "python3.9", # defaults to 3.10
    memory_size = 128, # defaults to 512
    layers = ["arn:aws:lambda:us-east-2:123456789012:layer:example-layer"],
    # be default, Lambda will only get bare permissions; to 
    # interact with additional AWS Services, need to provide 
    # IAM policies here.  They will automatically get attached 
    # to the Lambda Role.  
    policies = [lambda_iam_policy] 
)
def preprocess(arg1: str) -> str:
    # do stuff here, eg run some sql code against snowflake.  
    # Make sure to "import snowflake" within this function.  
    # Will need a "layer" passed which contains the snowflake
    # dependencies.  Must run in <15 minutes.
    return "hello"

@step
def preprocess_2(arg1: str) -> str:
    # do stuff here, eg run some sql code against snowflake.  
    # Make sure to "import snowflake" within this function.  
    # Will need a "layer" passed which contains the snowflake
    # dependencies.  Must run in <15 minutes.
    return "hello"

@step
def preprocess_3(arg1: str) -> str:
    # do stuff here, eg run some sql code against snowflake.  
    # Make sure to "import snowflake" within this function.  
    # Will need a "layer" passed which contains the snowflake
    # dependencies. Must run in <15 minutes.
    return "hello"

@step
def train(arg1: str, arg2: str, arg3: str) -> str:
    # do stuff here, eg run some sql code against snowflake.  
    # Make sure to "import snowflake" within this function.  
    # Will need a "layer" passed which contains the snowflake
    # dependencies.  Must run in <15 minutes.
    return "goodbye"

step_process_result = preprocess("hi")
# typically, will pass small bits of metadata between jobs.
# the lambdas will also pass data to each other via json inputs.
step_process_result_2 = preprocess_2(step_process_result)
step_process_result_3 = preprocess_3(step_process_result)
step_train_result = train(
    step_process_result, step_process_result_2, step_process_result_3
)
# this creates a pipeline including all the dependent steps
# "schedule" is optional, and can be cron or rate based
pipe = Pipeline("mytest", steps=[step_train_result], schedule="rate(2 minutes)")

# to run locally
print(pipe.local_run()) # will print output of each step

# to extract the step function definition
print(pipe.generate_step_functions())

# to extract the step function definition as a string
import json
print(json.dumps(pipe.generate_step_functions()))

# generate terraform json including step function code and lambdas
# Optionally installed with `pip install step-in-line[terraform]`
from cdktf import App
app = App(hcl_output=True)
instance_name = "aws_instance"
stack = StepInLine(app, instance_name, pipe, "us-east-1")
# write the terraform json for use by `terraform apply`
tf_path = Path(app.outdir, "stacks", instance_name)
app.synth()
# Terraform Python SDK does not add ".json" extension; this function
# renames the generated Terraform file and copies it to the project root.
rename_tf_output(tf_path)

```

```bash
export AWS_ACCESS_KEY_ID=your_aws_access_key
export AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
terraform init
terraform apply
```

### Custom Lambda template

The default Lambda template is the [following](./step_in_line/template_lambda.py):

```python
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
    
    with open("args.pickle", "rb") as f:
        args = pickle.load(f)
    
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

```

You can supply a custom template like so:

```python
stack = StepInLine(app, instance_name, pipe, "us-east-1", template_file="/path/to/your/custom/template.py")
```

The `"{{PUT_FUNCTION_HERE}}"` and `"{{PUT_FUNCTION_NAME_HERE}}"` will automatically be replaced by the code of your function defined inside the `@step` decorator and the name of the function, respectively.  

### Limitations

Only Lambda steps are supported.  For other types of steps, including Sagemaker jobs, [Sagemaker Pipelines](https://docs.aws.amazon.com/sagemaker/latest/dg/pipelines-step-decorator-create-pipeline.html) are likely a better option.

All limitations of Lambdas apply.  Each step can only run for 15 minutes before timing out.



## API Docs

https://danielhstahl.github.io/step-in-line/index.html