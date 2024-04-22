from constructs import Construct
from cdktf import (
    App,
    TerraformStack,
    IResolvable,
)
from cdktf_cdktf_provider_aws.provider import AwsProvider

from cdktf_cdktf_provider_aws import (
    data_aws_subnets,
    security_group,
    iam_role_policy_attachment,
    lambda_function,
    sfn_state_machine,
    iam_role,
    iam_policy,
    cloudwatch_event_rule,
    cloudwatch_event_target,
    cloudwatch_log_group,
)
from .step import Step, step
from .pipeline import Pipeline
from typing import List, Union, Optional, Tuple
import json
import zipfile
import pickle
from pathlib import Path
import inspect
import textwrap
from hashlib import sha256


def remove_decorators(src: str) -> str:
    """Removes any decorators from source code and
            truncates code so that there is no space
            in front of function definition

    Args:
        src (str): Source code for lambda
    """
    lines = []
    for line in src.splitlines():
        if not line.lstrip().startswith("@"):
            lines.append(line)

    return textwrap.dedent("\n".join(lines))


def get_python_code(python_template_path: str, step: Step) -> str:
    """Generates full python code for lambda

    Args:
        python_template_path (str): Location of template python code
        step (Step): Step to place inside template
    """
    code = remove_decorators(inspect.getsource(step.func))
    with open(python_template_path, "r") as f:
        template = f.read()
    template = template.replace('"{{PUT_FUNCTION_HERE}}"', code)
    template = template.replace('"{{PUT_FUNCTION_NAME_HERE}}"', step.func.__name__)
    new_file_name = f"{step.func.__name__}.py"
    with open(new_file_name, "w") as f:
        f.write(template)
    return new_file_name


def package_lambda(
    python_template_path: str, step: Step, lambda_entry: str
) -> Tuple[str, str]:
    """Creates zip of `Step` code for use in Lambda

    Args:
        python_template_path (str): Location of template python code
        step (Step): `Step` to place inside template
        lambda_entry (str): Name of python entry file
    """
    lambda_python_file = get_python_code(python_template_path, step)

    with open("args.pickle", "wb") as f:
        pickle.dump(
            [step.name if isinstance(step, Step) else step for step in step.args], f
        )

    with open("name.pickle", "wb") as f:
        pickle.dump(step.name, f)

    zip_name = f"{step.name}.zip"

    zf = zipfile.ZipFile(zip_name, mode="w")
    zf.write(lambda_python_file, arcname=f"{lambda_entry}.py")
    zf.write("args.pickle")
    zf.write("name.pickle")
    zf.close()
    with open(zip_name, "rb") as f:
        data = f.read()
        hash_sha256 = sha256(data).hexdigest()
    return zip_name, hash_sha256


def generate_lambda_function(
    scope: Construct,
    name_prefix: str,
    step: Step,
    subnet_ids: Optional[List[str]] = None,
    security_group_ids: Optional[List[str]] = None,
):
    """Creates Terraform resource for Lambda

    Args:
        scope
        name_prefix (str): Prefix for lambda name to ensure uniqueness.
        step (Step): Step to create Lambda from
        subnet_ids (list): Optional subnet IDs.  Required if VPC is specified
        security_group_ids (list): Option security group IDs.  Required if VPC is specified.
    """
    role = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "sts:AssumeRole",
                "Principal": {"Service": ["lambda.amazonaws.com"]},
            }
        ],
    }
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                "Resource": ["arn:aws:logs:*:*:*"],
            },
        ],
    }

    lambda_entry = "index"
    lambda_filename, sha256_hash = package_lambda(
        "step_in_line/template_lambda.py", step, lambda_entry
    )
    lambda_handler = f"{lambda_entry}.lambda_handler"

    lambda_role = iam_role.IamRole(
        scope,
        f"{step.name}role",
        assume_role_policy=json.dumps(role),
        name_prefix=step.name,
    )
    stepfunction_policy = iam_policy.IamPolicy(
        scope,
        f"{step.name}policy",
        policy=json.dumps(policy),
    )
    lambda_policy_attachment = iam_role_policy_attachment.IamRolePolicyAttachment(
        scope,
        f"{step.name}policyattachment",
        policy_arn=stepfunction_policy.arn,
        role=lambda_role.name,
    )
    vpc_config = (
        None
        if subnet_ids is None
        else {"subnet_ids": subnet_ids, "security_group_ids": security_group_ids}
    )
    return lambda_function.LambdaFunction(
        scope,
        step.name,
        function_name=f"{name_prefix}_{step.name}",
        role=lambda_role.arn,
        filename=lambda_filename,
        timeout=900,
        runtime="python3.10",
        handler=lambda_handler,
        vpc_config=vpc_config,
        layers=step.layers,
        source_code_hash=sha256_hash,
        environment=step.env_variables,
    )


def generate_event_bridge(scope: Construct, pipeline: Pipeline, step_function_arn: str):
    """Creates Terraform resource for event bridge to schedule step function run

    Args:
        scope
        pipeline (Pipeline): pipeline to convert into step function
        step_function_arn (str): ARN of the step function pipeline
    """
    role = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "events.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["states:StartExecution"],
                "Resource": step_function_arn,
            }
        ],
    }
    eventbridge_policy = iam_policy.IamPolicy(
        scope,
        f"{pipeline.name}eventbridgepolicy",
        policy=json.dumps(policy),
    )
    eventbridge_role = iam_role.IamRole(
        scope,
        f"{pipeline.name}eventbridgerole",
        assume_role_policy=json.dumps(role),
        name_prefix=pipeline.name,
    )
    eventbridge_policy_attachment = iam_role_policy_attachment.IamRolePolicyAttachment(
        scope,
        f"{pipeline.name}eventbridgepolicyattachment",
        policy_arn=eventbridge_policy.arn,
        role=eventbridge_role.name,
    )
    event_rule = cloudwatch_event_rule.CloudwatchEventRule(
        scope,
        f"{pipeline.name}eventrule",
        schedule_expression=pipeline.schedule,
    )
    cloudwatch_event_target.CloudwatchEventTarget(
        scope,
        f"{pipeline.name}eventtarget",
        rule=event_rule.name,
        arn=step_function_arn,
        role_arn=eventbridge_role.arn,
    )


def generate_step_function(
    scope: Construct, pipeline: Pipeline, aws_region: str, lambda_arns: List[str]
):
    """Creates Terraform resource for step functions

    Args:
        scope
        pipeline (Pipeline): pipeline to convert into step function
        aws_region (str): AWS Region
        lambda_arns (list): ARNs of Lambdas, required to give step functions access to invoke Lambdas
    """
    role = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "sts:AssumeRole",
                "Principal": {
                    "Service": [
                        f"states.{aws_region}.amazonaws.com",
                        "events.amazonaws.com",
                    ]
                },
            }
        ],
    }
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["lambda:InvokeFunction"],
                "Resource": lambda_arns,
            },
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogDelivery",
                    "logs:CreateLogStream",
                    "logs:GetLogDelivery",
                    "logs:UpdateLogDelivery",
                    "logs:DeleteLogDelivery",
                    "logs:ListLogDeliveries",
                    "logs:PutLogEvents",
                    "logs:PutResourcePolicy",
                    "logs:DescribeResourcePolicies",
                    "logs:DescribeLogGroups",
                ],
                "Resource": ["*"],
            },
            {
                "Effect": "Allow",
                "Action": [
                    "xray:PutTraceSegments",
                    "xray:PutTelemetryRecords",
                    "xray:GetSamplingRules",
                    "xray:GetSamplingTargets",
                ],
                "Resource": ["*"],
            },
        ],
    }
    log_group = cloudwatch_log_group.CloudwatchLogGroup(
        scope, f"{pipeline.name}log", name_prefix="/aws/vendedlogs/states/stepfunction"
    )
    stepfunction_policy = iam_policy.IamPolicy(
        scope,
        f"{pipeline.name}policy",
        policy=json.dumps(policy),
    )
    stepfunction_role = iam_role.IamRole(
        scope,
        f"{pipeline.name}role",
        assume_role_policy=json.dumps(role),
        name_prefix=pipeline.name,
    )
    stepfunction_policy_attachment = iam_role_policy_attachment.IamRolePolicyAttachment(
        scope,
        f"{pipeline.name}policyattachment",
        policy_arn=stepfunction_policy.arn,
        role=stepfunction_role.name,
    )
    return sfn_state_machine.SfnStateMachine(
        scope,
        pipeline.name,
        role_arn=stepfunction_role.arn,
        name=pipeline.name,
        type="STANDARD",
        definition=pipeline.generate_step_functions().to_json(),
        logging_configuration={
            "include_execution_data": True,
            "level": "ALL",
            "log_destination": f"{log_group.arn}:*",
        },
        tracing_configuration={"enabled": True},
    )


class StepInLine(TerraformStack):
    def __init__(
        self,
        scope: Construct,
        ns: str,
        pipeline: Pipeline,
        region: str,
        vpc_id: Optional[str] = None,
        subnet_filter: Optional[
            Union[IResolvable, List[data_aws_subnets.DataAwsSubnetsFilter]]
        ] = None,
        outbound_cidr: Optional[List[str]] = [
            "0.0.0.0/0",
        ],
    ):
        super().__init__(scope, ns)

        AwsProvider(self, "AWS", region=region)

        subnet_ids = None
        security_group_ids = None
        if vpc_id is not None:
            subnets = data_aws_subnets.DataAwsSubnets(
                self, "private_subnets", filter=subnet_filter
            )
            security_group_for_lambda = security_group.SecurityGroup(
                self,
                "security_group_lambda",
                egress=[
                    {
                        "fromPort": 0,
                        "toPort": 0,
                        "protocol": "-1",
                        "cidrBlocks": outbound_cidr,
                    }
                ],
                vpc_id=vpc_id,
            )

            subnet_ids = subnets.ids
            security_group_ids = [security_group_for_lambda.id]

        step_to_lambda_tf = {}
        for step in pipeline.get_steps():
            step_lambda = generate_lambda_function(
                self, pipeline.name, step, subnet_ids, security_group_ids
            )
            step_to_lambda_tf[step.name] = step_lambda.arn

        pipeline.set_generate_step_name(lambda s: step_to_lambda_tf[s.name])
        step_function = generate_step_function(
            self, pipeline, region, list(step_to_lambda_tf.values())
        )
        if pipeline.schedule is not None:
            generate_event_bridge(self, pipeline, step_function.arn)


def rename_tf_output(path: Path):
    """Terraform creates .tf, but expects .tf.json.  This function
            adds the .json extension and moves it into the root
            directory

    Args:
        path (Path): directory where Terraform outputs the .tf file
    """
    for file in path.glob("*.tf"):
        new_name = file.with_suffix(".tf.json")
        file.replace(new_name.name)  # put in root directory


## example, for testing
def main():
    app = App(hcl_output=True)

    @step
    def preprocess(arg1: str) -> str:
        return "hello"

    @step
    def preprocess_2(arg1: str) -> str:
        return "hello"

    @step
    def preprocess_3(arg1: str) -> str:
        return "hello"

    @step
    def train(arg1: str, arg2: str, arg3: str):
        return "goodbye"

    step_process_result = preprocess("hi")
    step_process_result_2 = preprocess_2(step_process_result)
    step_process_result_3 = preprocess_3(step_process_result)
    step_train_result = train(
        step_process_result, step_process_result_2, step_process_result_3
    )
    instance_name = "aws_instance"
    pipe = Pipeline("mytest", steps=[step_train_result], schedule="rate(2 minutes)")
    stack = StepInLine(app, instance_name, pipe, "us-east-1")
    tf_path = Path(app.outdir, "stacks", instance_name)
    app.synth()
    rename_tf_output(tf_path)
