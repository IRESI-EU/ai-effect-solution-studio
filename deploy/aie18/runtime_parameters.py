"""Narrow wrapper registry export; the maintained orchestrator owns no node map.

validate_tasks is retained solely to reproduce the historical v1 image overlay.
The maintained WP3 build does not copy or import this module.
"""
import json
from pathlib import Path
from parameter_values import effective_parameters, match_wrapper_configuration

CONTRACTS = json.loads(Path(__file__).with_name("contracts.json").read_text())


def validate(method, configuration):
    match_wrapper_configuration(method, configuration, capabilities(method))
    return effective_parameters(CONTRACTS[method]["execution_parameters"], configuration["parameters"])


def capabilities(method):
    contract = CONTRACTS[method]
    return {"capability_schema_version": "1.0", "transports": ["http-parameters-v1"], "operations": [{
        "operation_name": method, "operation_identity": contract["operation_identity"],
        "contract_version": contract["contract_version"], "execution_parameters": contract["execution_parameters"],
        "consumption_evidence": "aie18-manifest-v1"}]}


def validate_tasks(graph, configurations):
    if set(configurations) - set(graph.all_nodes):
        raise ValueError("Configuration targets an unknown graph instance")
    ids = []
    for key, value in configurations.items():
        validate(graph.all_nodes[key].operation.operation_signature.operation_name, value)
        ids.append(value["instance_id"])
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate logical instance identifier")
