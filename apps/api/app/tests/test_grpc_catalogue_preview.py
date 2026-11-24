from concurrent import futures

import grpc
import pytest
from google.protobuf import message_factory

from app.core.config import settings
from app.models.service import Service
from app.services.data_reference_service import preview_data_reference
from app.services.grpc_preview import _load_descriptors

COMMON = """syntax = "proto3";
package common;
message Line { string text = 1; }
"""

REPORT = """syntax = "proto3";
package report;
import "common.proto";
message GenerateReportRequest {}
message GenerateReportResponse {
  bool success = 1;
  string summary = 2;
  repeated common.Line lines = 3;
  int32 anomalies_detected = 4;
}
service ReportService { rpc GenerateReport(GenerateReportRequest) returns (GenerateReportResponse); }
"""


@pytest.fixture
def grpc_report_service(tmp_path, monkeypatch, session_factory):
    root = tmp_path / "contracts"
    proto_dir = root / "packages" / "pkg1" / "microservice"
    proto_dir.mkdir(parents=True)
    (proto_dir / "common.proto").write_text(COMMON)
    (proto_dir / "report.proto").write_text(REPORT)
    monkeypatch.setattr(settings, "service_contract_path", str(root))

    _, main_file = _load_descriptors(proto_dir / "report.proto")
    method = main_file.services_by_name["ReportService"].methods_by_name["GenerateReport"]
    request_cls = message_factory.GetMessageClass(method.input_type)
    response_cls = message_factory.GetMessageClass(method.output_type)

    def generate(request, context):
        response = response_cls(success=True, summary="15 anomalies in 40 records", anomalies_detected=15)
        response.lines.add(text="Anomaly rate 37.5%")
        return response

    handler = grpc.method_handlers_generic_handler(
        "report.ReportService",
        {"GenerateReport": grpc.unary_unary_rpc_method_handler(
            generate,
            request_deserializer=request_cls.FromString,
            response_serializer=lambda m: m.SerializeToString(),
        )},
    )
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    server.add_generic_rpc_handlers((handler,))
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()

    with session_factory() as db:
        db.merge(Service(
            id="grpc-report", name="Report Generator", provider="Test", category="Test",
            description="d", input_type="a", output_type="b", status="approved",
            container_name="report_generator1", internal_host="127.0.0.1", internal_port="8080",
            operation_name="GenerateReport", proto_uri=str(proto_dir / "report.proto"),
        ))
        db.commit()
    yield port
    server.stop(0)
    with session_factory() as db:
        db.query(Service).filter(Service.id == "grpc-report").delete()
        db.commit()


def test_catalogue_grpc_output_is_decoded_with_stored_proto(grpc_report_service, session_factory):
    with session_factory() as db:
        preview = preview_data_reference(
            "grpc", f"127.0.0.1:{grpc_report_service}", "task_abc", format_hint="GenerateReport", db=db
        )
    assert preview["available"] is True, preview
    assert preview["kind"] == "json"
    assert preview["content"]["summary"] == "15 anomalies in 40 records"
    assert preview["content"]["anomalies_detected"] == 15
    assert preview["content"]["lines"] == [{"text": "Anomaly rate 37.5%"}]


def test_unknown_rpc_name_reports_clear_message(grpc_report_service, session_factory):
    with session_factory() as db:
        preview = preview_data_reference(
            "grpc", f"127.0.0.1:{grpc_report_service}", None, format_hint="Nope", db=db
        )
    assert preview["available"] is False
    assert "Nope" in preview["message"]


def test_host_outside_catalogue_is_never_contacted(session_factory):
    with session_factory() as db:
        preview = preview_data_reference("grpc", "evil.example:50051", "task_x", format_hint="X", db=db)
    assert preview["available"] is False
    assert "approved" in preview["message"]


def test_service_without_stored_proto_explains(session_factory):
    with session_factory() as db:
        db.merge(Service(
            id="grpc-noproto", name="Manual Service", provider="Test", category="Test",
            description="d", input_type="a", output_type="b", status="approved",
            container_name="manual1", internal_host="manual-host", operation_name="Run",
            proto_uri="manual.proto",
        ))
        db.commit()
        preview = preview_data_reference("grpc", "manual-host:50051", None, format_hint="Run", db=db)
    assert preview["available"] is False
    assert "no stored .proto" in preview["message"]
