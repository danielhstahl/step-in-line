import logging
from typing import Sequence, Optional, List, Callable, Any, Tuple
import networkx as nx
from .step import Step
from .stepfunctions.steps import LambdaStep, Chain, Retry, Parallel, Graph

logger = logging.getLogger(__name__)


def crawl_back(graph: nx.DiGraph, step: Step):
    """Create the Graph of Steps

    Args:
        graph (DiGraph): The graph to populate with Steps
        step (Step): The `Step` to add to the graph
    """
    for dependency in step.depends_on:
        graph.add_edge(dependency, step)
        crawl_back(graph, dependency)


def convert_step_to_lambda(
    step: Step, generate_step_name: Callable[[Step], str]
) -> LambdaStep:
    """Create Lambda from Step

    Args:
        step (Step): The `Step` to convert to a lambda
        generate_step_name (callable): Generates the ARN of the Lambda from the step
    """
    lambda_state = LambdaStep(
        state_id=step.name,
        parameters={
            "FunctionName": generate_step_name(step),  # the function arn
            "Payload.$": "$",  # pass in all the possible values, including outputs from previous steps
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
    logger.debug(f"Converted {step.name} to Lambda")
    return lambda_state


def _default_lambda_name(s: Step) -> str:
    return "${aws_lambda_function." + s.name + "lambda.arn}"


class Pipeline:
    def __init__(
        self,
        name: str = "",
        steps: Optional[Sequence[Step]] = None,
        schedule: Optional[str] = None,  # cron
        generate_step_name: Callable[[Step], str] = _default_lambda_name,
    ):
        """Initialize a Pipeline

        Args:
            name (str): The name of the pipeline.
            steps (Sequence[Step]): The list of the non-conditional Steps associated with the pipeline.
        """
        self.name = name
        self.steps = steps if steps else []
        self.graph = nx.DiGraph()
        self.generate_step_name = generate_step_name
        self.schedule = schedule
        for step in steps:
            crawl_back(self.graph, step)
        if not nx.is_directed_acyclic_graph(self.graph):
            raise ValueError("Cycle detected in pipeline step graph.")
        if not self._check_uniqueness_of_names():
            raise ValueError(
                "Non-unique Step names!  Step names must be unique or a unique name must be passed to the @step decorator."
            )

    def _check_uniqueness_of_names(self) -> bool:
        num_steps = len(self.get_steps())
        return len(set(step.name for step in self.get_steps())) == num_steps

    def get_steps(self) -> List[Step]:
        """Gets all steps, guaranteed to be unique."""
        return self.graph.nodes

    def generate_layers(self) -> List[List[Step]]:
        """
        Create indexed sets of steps.
        This allows steps to be run in parallel,
        if they don't depend on each other
        """
        return list(nx.topological_generations(self.graph))

    def generate_step_functions(self) -> dict:
        """Create Step Function workflow definition"""
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
        workflow = Graph(
            chain
        )  # Workflow(name=self.name, definition=chain, role="doesnotmatter")
        logger.debug(f"Converted {self.name} to step function Workflow")
        return workflow.to_dict()

    def set_generate_step_name(self, generate_step_name: Callable[[Step], str]):
        self.generate_step_name = generate_step_name

    def local_run(self) -> List[List[Tuple[str, Any]]]:
        """
        Runs pipeline locally, with no AWS dependency.
        Returns all intermediary outputs.
        """
        outputs = {}  # contains all intermediary output
        output_arr = (
            []
        )  # contains all intermediary output, in the shape of the steps given by the topological generations
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
                logger.debug(f"Output from step {step.name}: {outputs[step.name]}")
                layer_output.append((step.name, outputs[step.name]))
            output_arr.append(layer_output)
        return output_arr
