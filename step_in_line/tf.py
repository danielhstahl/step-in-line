from constructs import Construct
from cdktf import (
    App,
    NamedRemoteWorkspace,
    TerraformStack,
    TerraformOutput,
    RemoteBackend,
    IResolvable,
)
from cdktf_cdktf_provider_aws.provider import AwsProvider
from cdktf_cdktf_provider_aws.instance import Instance
from cdktf_cdktf_provider_aws import lambda_function
from cdktf_cdktf_provider_aws import sfn_state_machine
from cdktf_cdktf_provider_aws import (
    data_aws_subnets,
    security_group,
)
from .step import Step
from .pipeline import Pipeline
from typing import List, Union


def generate_lambda_function(
    scope: Construct, step: Step, subnet_ids: List[str], security_group_ids: List[str]
):
    return lambda_function.LambdaFunction(
        scope,
        id=step.name,
        function_name=step.name,
        role="somerole",
        handler="somehandler",
        vpc_config={"subnet_ids": subnet_ids, "security_group_ids": security_group_ids},
        layers=step.layers,
    )


def generate_step_function(scope: Construct, pipeline: Pipeline):
    sfn_state_machine.SfnStateMachine(
        scope=scope,
        id=pipeline.name,
        role_arn="tbd",
        name=pipeline.name,
        type="STANDARD",
        definition=pipeline.generate_step_functions(),
    )


class MyStack(TerraformStack):
    def __init__(
        self,
        scope: Construct,
        ns: str,
        pipeline: Pipeline,
        vpc_id: str,
        region: str,
        steps: List[Step],
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
            egress={
                "from_port": 0,
                "to_port": 0,
                "protocol": "-1",
                "cidr_blocks": outbound_cidr,
            },
            vpc_id="hello",
        )

        step_to_lambda_tf = {
            [step.name]: generate_lambda_function(
                scope, step, subnets.ids, security_group_for_lambda.id
            ).arn
            for step in steps
        }

        pipeline.set_generate_step_name(lambda s: step_to_lambda_tf[s.name])
        generate_step_function(pipeline)


app = App()
stack = MyStack(app, "aws_instance")

RemoteBackend(
    stack,
    hostname="app.terraform.io",
    organization="<YOUR_ORG>",
    workspaces=NamedRemoteWorkspace("learn-cdktf"),
)

app.synth()
