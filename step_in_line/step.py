## based on Sagemaker Pipeline syntax
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
from __future__ import absolute_import

from typing import List, Optional, Callable, Any

from .utilities import unique_name_from_base_uuid4
from functools import wraps


## TODO, add environment variables
class Step:
    """`Step` for step function workflows"""

    def __init__(
        self,
        name: str,
        func: Callable,
        args: List[Any],
        description: Optional[str] = None,
        retry_count: int = 0,
        layers: List[str] = [],
        depends_on: Optional[List["Step"]] = None,
    ):
        """Initialize a Step

        Args:
            name (str): The name of the `Step`.
            func (callable): The function that should be executed as part of this step
            args (list): The arguments to the function.  If not a step, these are considered "static" and are used even in the Step Function execution
            description (str): The description of the `Step`.
            retry_count (int): Number of times to retry a failure
            layers (list): the ARNs of layers to add to the lambda functions
            depends_on (List[Step]): The list of Steps that the current `Step` depends on.
        """
        self.name = name
        self.description = description
        self.retry_count = retry_count
        self.layers = layers
        self.func = func
        self.args = args
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
    retry_count: int = 0
):
    """Decorator for converting a python function to a pipeline step.

    This decorator wraps the annotated code into a `Step` object which can then be passed
    to a pipeline as a step.

    Args:
        _func: A Python function to run as a SageMaker pipeline step.
        name (str): Name of the pipeline step. Defaults to a generated name using function name and uuid4 identifier to avoid duplicates.
        description (str): Description of the step
        layers (list): Lambda layers
        retry_count (int): number of retries to attempt.  Defaults to 0 (no retries).


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

            _name = unique_name_from_base_uuid4(func.__name__) if not name else name

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
                func=func,
                args=arg_list,
            )

        return wrapper

    if _func is None:
        return _step
    return _step(_func)
