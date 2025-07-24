from typing import Callable

def get_tool_name_from_operation_id(
    operation_id: str, raw_name: str, normalization_function: Callable[[str], str]
) -> str:
    if 0 < len(operation_id) <= 64:
        return operation_id
    return normalization_function(raw_name)
