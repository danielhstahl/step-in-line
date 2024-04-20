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
"""The `Step` definitions for SageMaker Pipelines Workflows."""
from __future__ import absolute_import


from enum import Enum
from typing import Dict, List, Union, Optional

from .entities import RequestType
from .utilities import unique_name_from_base_uuid4
from functools import wraps


class StepTypeEnum(Enum):
    """Enum of `Step` types."""

    LAMBDA = "Lambda"


class Step:
    """`Step` for step function workflows"""

    def __init__(
        self,
        name: str,
        description: Optional[str] = None,
        retry_count: Optional[int] = 0,
        layers: List[str] = [],
        step_type: StepTypeEnum = None,  # should only be lambda for Step Functions
        depends_on: Optional[List[Union[str, "Step"]]] = None,
    ):
        """Initialize a Step

        Args:
            name (str): The name of the `Step`.
            description (str): The description of the `Step`.
            step_type (StepTypeEnum): The type of the `Step`.
            depends_on (List[Union[str, Step, StepCollection]]): The list of `Step`/`StepCollection`
                names or `Step` or `StepCollection`, `StepOutput` instances that the current `Step`
                depends on.
        """
        self.name = name
        self.description = description
        self.step_type = step_type
        self.retry_count = retry_count
        self.layers = layers
        if depends_on is not None:
            self._depends_on = depends_on
        else:
            self._depends_on = None

    @property
    def depends_on(
        self,
    ) -> Optional[List[Union[str, "Step"]]]:
        """The list of steps the current `Step` depends on."""

        return self._depends_on

    @depends_on.setter
    def depends_on(self, depends_on: List[Union[str, "Step"]]):
        """Set the list of  steps the current step explicitly depends on."""

        if depends_on is not None:
            self._depends_on = depends_on
        else:
            self._depends_on = None

    def to_request(self) -> RequestType:
        """Gets the request structure for workflow service calls."""
        request_dict = {
            "Name": self.name,
            "Type": self.step_type.value,
        }
        if self.depends_on:
            request_dict["DependsOn"] = list(self.depends_on)
        if self.description:
            request_dict["Description"] = self.description

        return request_dict

    def add_depends_on(self, step_names: List[Union[str, "Step"]]):
        """Add `Step` names or `Step` instances to the current `Step` depends on list."""

        if not step_names:
            return

        if not self._depends_on:
            self._depends_on = []

        self._depends_on.extend(step_names)

    @property
    def ref(self) -> Dict[str, str]:
        """Gets a reference dictionary for `Step` instances."""
        return {"Name": self.name}


def step(
    _func=None,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    layers: Optional[List[str]] = None,
    retry_count: int = 0
):
    """Decorator for converting a python function to a pipeline step.

    This decorator wraps the annotated code into a `DelayedReturn` object which can then be passed
    to a pipeline as a step. This creates a new pipeline that proceeds from the step of the
    `DelayedReturn` object.

    If the value for a parameter is not set, the decorator first looks up the value from the
    SageMaker configuration file. If no value is specified in the configuration file or no
    configuration file is found, the decorator selects the default as specified in the following
    list. For more information, see `Configuring and using defaults with the SageMaker Python SDK
    <https://sagemaker.readthedocs.io/en/stable/overview.html#configuring-and-using-defaults-with-the-sagemaker-python-sdk>`_.

    Args:
        _func: A Python function to run as a SageMaker pipeline step.

        name (str): Name of the pipeline step. Defaults to a generated name using function name
            and uuid4 identifier to avoid duplicates.


    """

    def _step(func):

        @wraps(func)
        def wrapper(*args, **kwargs):

            depends_on = {}
            for arg in list(args) + list(kwargs.values()):
                if isinstance(arg, Step):
                    depends_on[id(arg)] = arg

            # setup default values for name, display_name and description if not provided

            _name = unique_name_from_base_uuid4(func.__name__) if not name else name

            _description = description
            if not _description:
                _description = (
                    func.__doc__ if func.__doc__ else func.__code__.co_filename
                )
            return Step(
                name=_name,
                step_type=StepTypeEnum.LAMBDA,
                depends_on=list(depends_on.values()),
                retry_count=retry_count,
                layers=layers,
            )

        return wrapper

    if _func is None:
        return _step
    return _step(_func)
