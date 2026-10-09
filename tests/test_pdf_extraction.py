from reportlab.pdfgen import canvas
from app.services.pdf_service import extract_pdf


def test_pdf_pages_keep_page_numbers(tmp_path):
    path = tmp_path / "sample.pdf"
    pdf = canvas.Canvas(str(path))
    pdf.drawString(30, 250, "First page policy text.")
    pdf.showPage()
    pdf.drawString(30, 250, "Second page policy text.")
    pdf.save()
    pages = extract_pdf(path, "doc", "sample.pdf")
    assert [page["page"] for page in pages] == [1, 2]
    assert "First page" in pages[0]["text"]
    assert pages[1]["document_id"] == "doc"
