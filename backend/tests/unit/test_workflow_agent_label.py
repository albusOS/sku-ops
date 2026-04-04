from assistant.application.workflows.registry import response_agent_label

def test_response_agent_label_marks_unified_workflow_runs_as_dag():
    label = response_agent_label('unified', [{'tool': 'run_inventory_overview'}, {'tool': 'list_low_stock'}])
    assert label == 'dag'

def test_response_agent_label_preserves_non_workflow_agents():
    assert response_agent_label('procurement', [{'tool': 'get_vendor_lead_times'}]) == 'procurement'
