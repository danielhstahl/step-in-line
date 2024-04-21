from constructs import Construct
from cdktf import (
    App,
    TerraformStack,
    IResolvable,
)
from cdktf_cdktf_provider_aws.provider import AwsProvider
from cdktf_cdktf_provider_aws import lambda_function
from cdktf_cdktf_provider_aws import sfn_state_machine
from cdktf_cdktf_provider_aws import (
    data_aws_subnets,
    security_group,
)
from .step import Step, step
from .pipeline import Pipeline
from typing import List, Union


def generate_lambda_function(
    scope: Construct, step: Step, subnet_ids: List[str], security_group_ids: List[str]
):
    return lambda_function.LambdaFunction(
        scope,
        id=step.name,
        id_=step.name,
        function_name=step.name,
        role="somerole",
        handler="somehandler",
        vpc_config={"subnet_ids": subnet_ids, "security_group_ids": security_group_ids},
        layers=step.layers,
    )


def generate_step_function(scope: Construct, pipeline: Pipeline):
    sfn_state_machine.SfnStateMachine(
        scope=scope,
        id_=pipeline.name,
        id=pipeline.name,
        role_arn="tbd",
        name=pipeline.name,
        type="STANDARD",
        definition=pipeline.generate_step_functions().to_json(),
    )


class MyStack(TerraformStack):
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
        generate_step_function(self, pipeline)


## temporary, for testing
def main():
    app = App(hcl_output=True)  # not sure what hcl_output does...

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
    stack = MyStack(app, "aws_instance", pipe, "myvpc", "us-east-1", [])

    # RemoteBackend(
    #    stack,
    #    hostname="app.terraform.io",
    #    organization="<YOUR_ORG>",
    #    workspaces=NamedRemoteWorkspace("learn-cdktf"),
    # )

    app.synth()
