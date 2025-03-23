from typing import Optional, List, Literal

from pydantic import BaseModel
from typing_extensions import override


class NotGiven:
    """
    A sentinel singleton class used to distinguish omitted keyword arguments
    from those passed in with the value None (which may have different behavior).

    For example:

    ```py
    def get(timeout: Union[int, NotGiven, None] = NotGiven()) -> Response: ...


    get(timeout=1)  # 1s timeout
    get(timeout=None)  # No timeout
    get()  # Default timeout behavior, which may not be statically known at the method definition.
    ```
    """

    def __bool__(self) -> Literal[False]:
        return False

    @override
    def __repr__(self) -> str:
        return "NOT_GIVEN"

    def to_json(self):
        return {
            # Convert the relevant attributes to a JSON-serializable format
        }


NOT_GIVEN = NotGiven()


class Function(BaseModel):
    arguments: str
    name: str


class CompletionMessageToolCall(BaseModel):
    id: str
    function: Function
    type: Literal["function"]


class CompletionMessage(BaseModel):
    """
    {
    "content": "hi",
    "refusal": "None",
    "role": "assistant",
    }
    """
    message: dict
    role: str
