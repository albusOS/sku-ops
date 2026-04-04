from assistant.agents.tools.registry import ToolEntry


def test_tool_entry_captures_description_and_arg_names():

    async def sample_tool(vendor_id: str, days: int=30) -> str:
        """Vendor lead-time lookup for diagnostics."""
        return "{}"
    from assistant.agents.tools import registry as reg
    name = "_test_tool_metadata_capture"
    reg.register(name, "purchasing", sample_tool, use_cases=["vendor reliability"])
    entry = reg.get(name)
    assert isinstance(entry, ToolEntry)
    assert entry is not None
    assert entry.description == "Vendor lead-time lookup for diagnostics."
    assert entry.arg_names == ["vendor_id", "days"]
    assert entry.use_cases == ["vendor reliability"]
