# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
"""The Pipeline entity for workflow."""
from __future__ import absolute_import

import logging
from typing import Sequence, Optional, List, Callable, Dict, Any, Tuple
import networkx as nx
from .step import Step
from stepfunctions.steps import LambdaStep, Chain, Retry, Parallel, Graph
from stepfunctions.workflow import Workflow

logger = logging.getLogger(__name__)


def crawl_back(graph: nx.DiGraph, step: Step):
    for dependency in step.depends_on:
        graph.add_edge(dependency, step)
        crawl_back(graph, dependency)


def convert_step_to_lambda(
    step: Step, generate_step_name: Callable[[Step], str]
) -> LambdaStep:
    lambda_state = LambdaStep(
        state_id=step.name,
        parameters={
            "FunctionName": generate_step_name(step),  # the function arn
            "Payload.$": "$",
        },
    )
    if step.retry_count > 0:
        lambda_state.add_retry(
            Retry(
                error_equals=["States.TaskFailed"],
                interval_seconds=15,
                max_attempts=step.retry_count,
                backoff_rate=4.0,
            )
        )
    return lambda_state


def default_lambda_name(s: Step) -> str:
    return "${aws_lambda_function." + s.name + "lambda.arn}"


class Pipeline:
    def __init__(
        self,
        name: str = "",
        steps: Optional[Sequence[Step]] = None,
        generate_step_name: Callable[[Step], str] = default_lambda_name,
    ):
        """Initialize a Pipeline

        Args:
            name (str): The name of the pipeline.
            steps (Sequence[Union[Step, StepCollection, StepOutput]]): The list of the
                non-conditional steps associated with the pipeline. Any steps that are within the
                `if_steps` or `else_steps` of a `ConditionStep` cannot be listed in the steps of a
                pipeline. Of particular note, the workflow service rejects any pipeline definitions
                that specify a step in the list of steps of a pipeline and that step in the
                `if_steps` or `else_steps` of any `ConditionStep`.
        """
        self.name = name
        self.steps = steps if steps else []
        self.graph = nx.DiGraph()
        self.generate_step_name = generate_step_name
        for step in steps:
            crawl_back(self.graph, step)
        if not nx.is_directed_acyclic_graph(self.graph):
            raise ValueError("Cycle detected in pipeline step graph.")

    def get_steps(self) -> List[Step]:
        return self.graph.nodes

    def generate_layers(self) -> List[List[Step]]:
        return list(nx.topological_generations(self.graph))

    def generate_step_functions(self) -> Graph:
        dag_lambda = []
        for index, layer in enumerate(self.generate_layers()):
            if len(layer) == 1:
                dag_lambda.append(
                    convert_step_to_lambda(layer[0], self.generate_step_name)
                )
            else:
                parallel_state = Parallel(f"parallel at {index}")
                for step in layer:
                    parallel_state.add_branch(
                        convert_step_to_lambda(step, self.generate_step_name)
                    )
                dag_lambda.append(parallel_state)
        chain = Chain(dag_lambda)
        workflow = Workflow(name=self.name, definition=chain, role="doesnotmatter")
        return workflow.definition

    def set_generate_step_name(self, generate_step_name: Callable[[Step], str]):
        self.generate_step_name = generate_step_name

    def local_run(self) -> List[List[Tuple[str, Any]]]:
        outputs = {}
        output_arr = []
        for layer in self.generate_layers():
            layer_output = []
            for step in layer:
                args = []
                for arg in step.args:
                    if isinstance(arg, Step):
                        args.append(outputs[arg.name])
                    else:
                        args.append(arg)
                outputs[step.name] = step.func(*args)
                layer_output.append((step.name, outputs[step.name]))
            output_arr.append(layer_output)
        return output_arr
