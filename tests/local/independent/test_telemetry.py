import pytest

from typing import Dict, List

from sodasql.telemetry.soda_telemetry import SodaTelemetry
from sodasql.telemetry.soda_tracer import soda_trace
from sodasql.telemetry.memory_span_exporter import MemorySpanExporter

from sodasql.__version__ import SODA_SQL_VERSION

from tests.common.telemetry_helper import telemetry_ensure_no_secrets

soda_telemetry = SodaTelemetry.get_instance()
telemetry_exporter = MemorySpanExporter.get_instance()


def dict_has_keys(dict: Dict, keys: List[str]):
    for key in keys:
        assert key in dict


def test_basic_telemetry_structure():
    """Test for basic keys and values for any created span."""
    telemetry_exporter.reset()

    @soda_trace
    def mock_fn():
        pass

    mock_fn()

    assert len(telemetry_exporter.span_dicts) == 1

    span = telemetry_exporter.span_dicts[0]

    dict_has_keys(span, ["attributes", "context", "start_time", "end_time", "name", "resource", "status"])
    dict_has_keys(span["attributes"], ["user_cookie_id"])
    dict_has_keys(span["context"], ["span_id", "trace_id", "trace_state"])
    dict_has_keys(span["resource"], ["os.architecture", "os.type", "os.version", "platform", "python.implementation", "python.version", "service.name", "service.namespace", "service.version"])

    resource = span["resource"]
    assert resource["service.name"] == "soda"
    assert resource["service.namespace"] == "soda-sql"
    assert resource["service.version"] == SODA_SQL_VERSION


def test_multi_spans():
    """Test multi spans, the relationship and hierarchy."""
    telemetry_exporter.reset()

    @soda_trace
    def mock_fn_1():
        pass

    @soda_trace
    def mock_fn_2():
        pass

    mock_fn_1()
    mock_fn_2()

    assert len(telemetry_exporter.span_dicts) == 2
    span_1 = telemetry_exporter.span_dicts[0]
    span_2 = telemetry_exporter.span_dicts[1]

    assert span_1["attributes"]["user_cookie_id"] == span_2["attributes"]["user_cookie_id"]
    assert span_1["context"]["trace_id"] == span_2["context"]["trace_id"]
    assert span_1["context"]["span_id"] == span_2["parent_id"]
    assert span_1["context"]["span_id"] != span_2["context"]["span_id"]


def test_add_argument():
    """Test that adding a telemetry argument adds it to a span."""
    telemetry_exporter.reset()

    @soda_trace
    def mock_fn():
        soda_telemetry.set_attribute("test", "something")
        pass

    mock_fn()

    assert len(telemetry_exporter.span_dicts) == 1

    span = telemetry_exporter.span_dicts[0]

    assert "test" in span["attributes"]
    assert span["attributes"]["test"] == "something"


@pytest.mark.parametrize(
    "key, value",
    [
        ("password", "something"),
        ("something", "secret")
    ]
)
def test_fail_secret(key: str, value: str):
    """Test that 'no_secrets' test works."""
    telemetry_exporter.reset()

    with pytest.raises(AssertionError) as e:
        @telemetry_ensure_no_secrets()
        def test_fn():
            @soda_trace
            def mock_fn():
                soda_telemetry.set_attribute(key, value)
                pass

            mock_fn()
        test_fn()

    error_msg = str(e.value)

    assert "Forbidden telemetry" in error_msg
    assert key in error_msg or value in error_msg
