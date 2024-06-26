from enum import Enum
from typing import Generic, Literal, TypeVar, Union

from pydantic import BaseModel, Field, RootModel
from typing_extensions import Annotated

NpFlowStateId = TypeVar("NpFlowStateId", bound=Enum)
ApFlowStateId = TypeVar("ApFlowStateId", bound=Enum)
FeedbackFlowStateId = TypeVar("FeedbackFlowStateId", bound=Enum)


class NpFlowStateRef(BaseModel):
    type: Literal["np"] = "np"
    id: NpFlowStateId


class ApFlowStateRef(BaseModel, Generic[ApFlowStateId]):
    type: Literal["ap"] = "ap"
    id: ApFlowStateId


class FeedbackFlowStateRef(BaseModel):
    type: Literal["feedback"] = "feedback"
    id: FeedbackFlowStateId


class FlowStateRef(RootModel):
    root: Annotated[
        Union[NpFlowStateRef, ApFlowStateRef, FeedbackFlowStateRef],
        Field(discriminator="type"),
    ]


class FlowOption(BaseModel):
    prompt: str
    next: FlowStateRef


class NpFlowState(BaseModel):
    type: Literal["np"] = "np"
    id: NpFlowStateId
    options: list[FlowOption]


class ApFlowState(BaseModel):
    type: Literal["ap"] = "ap"
    id: ApFlowStateId
    options: list[FlowOption]


class FeedbackFlowState(BaseModel):
    type: Literal["feedback"] = "feedback"
    id: FeedbackFlowStateId
    prompt_analysis: str
    prompt_misunderstanding: str
    prompt_needs_improvement: str
    prompt_ok: str
    next_needs_improvement: FlowStateRef
    next_ok: FlowStateRef


class FlowState(RootModel):
    root: Annotated[
        Union[NpFlowState, ApFlowState, FeedbackFlowState],
        Field(discriminator="type"),
    ]


class Level(BaseModel):
    flow_states: list[FlowState]
    initial_np_state: FlowStateRef
    initial_ap_state: FlowStateRef

    def get_flow_state(self, ref: FlowStateRef) -> FlowState:
        return next(state for state in self.flow_states if state.root.id == ref.root.id)
