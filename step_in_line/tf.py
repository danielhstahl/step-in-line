from constructs import Construct
from cdktf import (
    App,
    TerraformStack,
    IResolvable,
)
from cdktf_cdktf_provider_aws.provider import AwsProvider
from cdktf_cdktf_provider_aws import lambda_function
from cdktf_cdktf_provider_aws import sfn_state_machine, iam_role
from cdktf_cdktf_provider_aws import (
    data_aws_subnets,
    security_group,
)
from .step import Step, step
from .pipeline import Pipeline
from typing import List, Union
import json
import zipfile
import dill


def generate_lambda_function(
    scope: Construct, step: Step, subnet_ids: List[str], security_group_ids: List[str]
):
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
    with open("myfunc.pickle", "wb") as f:
        dill.dump(step, f)
    zip_name = f"{step.name}.zip"
    lambda_source_code = "step_in_line/template_lambda.py"

    zf = zipfile.ZipFile(zip_name, mode="w")
    zf.write(lambda_source_code, arcname="index.py")
    zf.write("myfunc.pickle")
    zf.close()

    lambda_role = iam_role.IamRole(
        scope,
        id_=step.name + "role",
        id=step.name + "role",
        assume_role_policy=json.dumps(role),
        name_prefix=step.name,
    )
    return lambda_function.LambdaFunction(
        scope,
        id=step.name,
        id_=step.name,
        function_name=step.name,
        role=lambda_role.arn,
        filename=zip_name,
        timeout=900,
        runtime="python3.10",
        handler="index.lambda_handler",
        vpc_config={"subnet_ids": subnet_ids, "security_group_ids": security_group_ids},
        layers=step.layers,
    )


def generate_step_function(
    scope: Construct, pipeline: Pipeline, lambda_arns: List[str]
):
    role = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["lambda:InvokeFunction"],
                "Resource": lambda_arns,
            },
        ],
    }
    stepfunction_role = iam_role.IamRole(
        scope,
        id_=pipeline.name + "role",
        id=pipeline.name + "role",
        assume_role_policy=json.dumps(role),
        name_prefix=pipeline.name,
    )
    sfn_state_machine.SfnStateMachine(
        scope=scope,
        id_=pipeline.name,
        id=pipeline.name,
        role_arn=stepfunction_role.arn,
        name=pipeline.name,
        type="STANDARD",
        definition=pipeline.generate_step_functions().to_json(),
    )


class StepInLine(TerraformStack):
    def __init__(
        self,
        scope: Construct,
        ns: str,
        pipeline: Pipeline,
        vpc_id: str,
        region: str,
        subnet_filter: Union[IResolvable, List[data_aws_subnets.DataAwsSubnetsFilter]],
        outbound_cidr: List[str] = [
            "0.0.0.0/0",
        ],
    ):
        super().__init__(scope, ns)

        AwsProvider(self, "AWS", region=region)
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

        step_to_lambda_tf = {}
        for step in pipeline.get_steps():
            step_lambda = generate_lambda_function(
                self, step, subnets.ids, [security_group_for_lambda.id]
            )
            step_to_lambda_tf[step.name] = step_lambda.arn

        pipeline.set_generate_step_name(lambda s: step_to_lambda_tf[s.name])
        generate_step_function(self, pipeline, list(step_to_lambda_tf.values()))


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
    def train(arg2: str):
        return "goodbye"

    step_process_result = preprocess("hi")
    step_process_result_2 = preprocess_2(step_process_result)
    step_process_result_3 = preprocess_3(step_process_result)
    step_train_result = train(
        step_process_result, step_process_result_2, step_process_result_3
    )

    pipe = Pipeline("mytest", steps=[step_train_result])
    stack = StepInLine(app, "aws_instance", pipe, "myvpc", "us-east-1", [])

    app.synth()
