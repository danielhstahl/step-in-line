from typing import List, Optional, Callable, Any, Dict
from functools import wraps


class Step:
    """`Step` for step function workflows"""

    def __init__(
        self,
        name: str,
        func: Callable,
        args: List[Any],
        python_runtime: str,
        memory_size: int = 512,
        description: Optional[str] = None,
        retry_count: int = 0,
        policies: List[str] = [],
        layers: List[str] = [],
        env_variables: Dict[str, str] = {},  # to pass in to lambda
        depends_on: Optional[List["Step"]] = None,
    ):
        """Initialize a Step

        Args:
            name (str): The name of the `Step`.
            func (callable): The function that should be executed as part of this step
            args (list): The arguments to the function.  If not a step, these are considered "static" and are used even in the Step Function execution
            python_runtime (str): Lambda runtime.
            memory_size (int): Megabytes of memory for the lambda.  Defaults to 512.
            description (str): The description of the `Step`.
            retry_count (int): Number of times to retry a failure
            policies (List[str]): IAM policies, in JSON, to provide to the Lambda
            layers (list): the ARNs of layers to add to the lambda function
            env_variables (dict): environment variables to pass to lambda function
            depends_on (List[Step]): The list of Steps that the current `Step` depends on.
        """
        self.name = name
        self.description = description
        self.retry_count = retry_count
        self.layers = layers
        self.func = func
        self.args = args
        self.memory_size = memory_size
        self.python_runtime = python_runtime
        self.env_variables = env_variables
        self.additional_policies = (
            policies  # by default, Lambda gets minimal permission
        )
        if depends_on is not None:
            self._depends_on = depends_on
        else:
            self._depends_on = None

    @property
    def depends_on(
        self,
    ) -> Optional[List["Step"]]:
        """The list of steps the current `Step` depends on."""

        return self._depends_on

    @depends_on.setter
    def depends_on(self, depends_on: List["Step"]):
        """Set the list of  steps the current step explicitly depends on."""

        if depends_on is not None:
            self._depends_on = depends_on
        else:
            self._depends_on = None

    def add_depends_on(self, step_names: List["Step"]):
        """Add `Step` names or `Step` instances to the current `Step` depends on list."""

        if not step_names:
            return

        if not self._depends_on:
            self._depends_on = []

        self._depends_on.extend(step_names)


def step(
    _func=None,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    layers: Optional[List[str]] = None,
    python_runtime: str = "python3.10",
    memory_size: int = 512,
    policies: List[str] = [],
    retry_count: int = 0,
    env_variables: Dict[str, str] = {}
):
    """Decorator for converting a python function to a pipeline step.

    This decorator wraps the annotated code into a `Step` object which can then be passed
    to a pipeline as a step.

    Args:
        _func: A Python function to run as a SageMaker pipeline step.
        name (str): Name of the pipeline step. Defaults to a generated name using function name and uuid4 identifier to avoid duplicates.
        description (str): Description of the step
        layers (list): Lambda layers
        python_runtime (str): Lambda runtime.
        memory_size (int): Megabytes of memory for the lambda.  Defaults to 512.
        policies (List[str]): IAM policies, in JSON, to provide to the Lambda
        retry_count (int): number of retries to attempt.  Defaults to 0 (no retries).
        env_variables (dict): environment variables to pass to lambda function

    """

    def _step(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            depends_on = {}
            arg_list = []
            for arg in list(args) + list(kwargs.values()):
                if isinstance(arg, Step):
                    depends_on[id(arg)] = arg
                arg_list.append(arg)

            # setup default values for name, display_name and description if not provided

            _name = func.__name__ if not name else name

            _description = description
            if not _description:
                _description = (
                    func.__doc__ if func.__doc__ else func.__code__.co_filename
                )
            return Step(
                name=_name,
                depends_on=list(depends_on.values()),
                retry_count=retry_count,
                layers=layers,
                python_runtime=python_runtime,
                memory_size=memory_size,
                policies=policies,
                func=func,
                args=arg_list,
                env_variables=env_variables,
            )

        return wrapper

    if _func is None:
        return _step
    return _step(_func)
