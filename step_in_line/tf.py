from constructs import Construct
from cdktf import (
    App,
    NamedRemoteWorkspace,
    TerraformStack,
    TerraformOutput,
    RemoteBackend,
)
from cdktf_cdktf_provider_aws.provider import AwsProvider
from cdktf_cdktf_provider_aws.instance import Instance
from cdktf_cdktf_provider_aws import lambda_function
from cdktf_cdktf_provider_aws import sfn_state_machine
from cdktf_cdktf_provider_aws import data_aws_subnets
from .step import Step


def generate_lambda_function(step: Step):
    lambda_function.LambdaFunction(
        scope,
        id,
        function_name="helloworld",
        role="somerole",
        handler="somehandler",
        vpc_config="somevpcconfig",
    )


class MyStack(TerraformStack):
    def __init__(self, scope: Construct, ns: str):
        super().__init__(scope, ns)

        AwsProvider(self, "AWS", region="us-west-1")
        subnets = data_aws_subnets.DataAwsSubnets(
            self,
            "private_subnets",
            filter=[],  #: typing.Union[IResolvable, typing.List[DataAwsSubnetsFilter]] = None,
        )
        lambda_function.LambdaFunction(
            scope,
            id,
            function_name="helloworld",
            role="somerole",
            handler="somehandler",
            vpc_config="somevpcconfig",
        )


app = App()
stack = MyStack(app, "aws_instance")

RemoteBackend(
    stack,
    hostname="app.terraform.io",
    organization="<YOUR_ORG>",
    workspaces=NamedRemoteWorkspace("learn-cdktf"),
)

app.synth()
