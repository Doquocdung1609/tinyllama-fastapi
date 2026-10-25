"""Exercise the real Streamlit financial workflow against the running local API."""
import json
from pathlib import Path
import sys

from streamlit.testing.v1 import AppTest


def verify():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "streamlit_app.py"))
    app.run(timeout=90)
    app.sidebar.radio[0].set_value("Tìm kiếm tài chính").run(timeout=90)
    next(widget for widget in app.selectbox if widget.label == "Tập tài liệu").set_value("sec-pilot-c").run(timeout=90)
    next(widget for widget in app.selectbox if widget.label == "Cách tìm").set_value("Từ khóa")
    next(widget for widget in app.text_input if widget.label == "Nội dung cần tìm").set_value("AAPL total net sales")
    next(widget for widget in app.text_input if widget.label == "Mã cổ phiếu (tùy chọn)").set_value("AAPL")
    next(widget for widget in app.button if widget.label == "Tìm bằng chứng").click().run(timeout=180)
    checks = {"no_streamlit_exception": len(app.exception) == 0,
              "no_api_error": len(app.error) == 0,
              "partial_source_warning_visible": any("trích xuất một phần" in item.value for item in app.warning),
              "source_table_visible": len(app.dataframe) > 0,
              "evidence_results_visible": len(app.subheader) == 5,
              "source_links_visible": len(app.get("link_button")) == 5,
              "provenance_visible": any("Nguồn đã đối chiếu" in item.value for item in app.caption)}
    print(json.dumps({"checks": checks, "scope": "Streamlit AppTest with live API, keyword mode; not a browser pixel-layout test"}, ensure_ascii=True))
    return all(checks.values())


if __name__ == "__main__":
    sys.exit(0 if verify() else 1)
