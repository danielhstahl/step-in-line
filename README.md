## Step-in-line

Step functions are awesome.  It is a fully managed serverless AWS offering, so there is no upkeep or maintenance required.  Unfortunately, programatically created workflows of Lambda functions requires creating complex JSON definitions.  This library generates these JSON definitions automatically from Python decorators.  In addition, it generates the Lambda functions for each Python function.  

The API is intentionally similar to the Sagemaker Pipeline API.  

## Usage

```python
from cdktf import App
from step_in_line.step import step
from step_in_line.pipeline import Pipeline
from step_in_line.tf import StepInLine, rename_tf_output

app = App(hcl_output=True)

@step(layers=["arn:aws:lambda:us-east-2:123456789012:layer:example-layer"])
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
def train(arg2: str):
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

# generate terraform json including step function code and lambdas
instance_name = "aws_instance"
stack = StepInLine(app, instance_name, pipe, "us-east-1")

# write the terraform json for use by `terraform apply`
tf_path = Path(app.outdir, "stacks", instance_name)
app.synth()
rename_tf_output(tf_path)

```

```bash
export AWS_ACCESS_KEY_ID=your_aws_access_key
export AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
terraform init
terraform apply
```


## API Docs

https://danielhstahl.github.io/step-in-line/index.html