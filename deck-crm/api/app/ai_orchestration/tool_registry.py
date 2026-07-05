from __future__ import annotations


class ToolRegistry:
    def __init__(self) -> None:
        self._tools = {
            "load_deck_context": "context_builder",
            "validate_scene_graph": "scene_graph_validator",
            "save_generation_batch": "orchestrator",
            "compile_final_deck": "final_deck_service",
        }

    def list_tools(self) -> dict[str, str]:
        return dict(self._tools)

