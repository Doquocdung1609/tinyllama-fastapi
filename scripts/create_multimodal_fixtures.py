"""Create small legal synthetic PDFs with explicit ground truth for tests."""
from __future__ import annotations

from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "pdfs"
OUT.mkdir(parents=True, exist_ok=True)
ARIAL = Path("C:/Windows/Fonts/arial.ttf")
ARIAL_BOLD = Path("C:/Windows/Fonts/arialbd.ttf")
pdfmetrics.registerFont(TTFont("FixtureSans", str(ARIAL)))
pdfmetrics.registerFont(TTFont("FixtureSansBold", str(ARIAL_BOLD)))


def styles():
    result = getSampleStyleSheet()
    for name in ("Normal", "Title", "Heading1", "Heading2"):
        result[name].fontName = "FixtureSansBold" if name != "Normal" else "FixtureSans"
    return result


def doc(path: Path, story):
    SimpleDocTemplate(str(path), pagesize=A4, rightMargin=18*mm, leftMargin=18*mm,
                      topMargin=16*mm, bottomMargin=16*mm).build(story)


def styled_table(data, widths=None):
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "FixtureSansBold"),
        ("FONTNAME", (0, 1), (-1, -1), "FixtureSans"),
        ("GRID", (0, 0), (-1, -1), .75, colors.HexColor("#44546A")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9EAF7")),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def make_text_vi():
    s = styles()
    story = [Paragraph("TÀI LIỆU VĂN BẢN TIẾNG VIỆT", s["Title"]), Spacer(1, 8),
             Paragraph("Năng lực hấp thụ là khả năng doanh nghiệp nhận biết giá trị của tri thức mới, tiếp thu tri thức đó và ứng dụng vào hoạt động kinh doanh.", s["Normal"]),
             Spacer(1, 8), Paragraph("Năng lực hấp thụ tốt giúp doanh nghiệp khai thác đổi mới nhanh hơn và chuyển tri thức thành sản phẩm hoặc quy trình hữu ích.", s["Normal"])]
    doc(OUT / "A_text_only_vi.pdf", story)


def make_mixed_table():
    s = styles()
    data = [["Năm", "Doanh thu (triệu đồng)", "Lợi nhuận (triệu đồng)"],
            ["2023", "100", "12"], ["2024", "125", "16"]]
    story = [Paragraph("BẢNG 1. KẾT QUẢ KINH DOANH TỔNG HỢP", s["Heading1"]),
             Paragraph("Dữ liệu tổng hợp phục vụ kiểm thử; không đại diện cho doanh nghiệp có thật.", s["Normal"]),
             Spacer(1, 8), styled_table(data, [35*mm, 60*mm, 60*mm]), Spacer(1, 8),
             Paragraph("Doanh thu và lợi nhuận đều tăng trong giai đoạn được trình bày.", s["Normal"])]
    doc(OUT / "B_mixed_text_table.pdf", story)


def make_financial_statement():
    s = styles()
    data = [["Chỉ tiêu", "2023", "2024", "Đơn vị"],
            ["Doanh thu", "1.000", "1.250", "triệu đồng"],
            ["Lợi nhuận", "120", "150", "triệu đồng"],
            ["Tài sản ngắn hạn", "600", "750", "triệu đồng"],
            ["Nợ ngắn hạn", "300", "375", "triệu đồng"],
            ["Tổng nợ", "500", "550", "triệu đồng"],
            ["Tổng tài sản", "1.200", "1.400", "triệu đồng"],
            ["Điều chỉnh giảm", "(25)", "(30)", "triệu đồng"]]
    story = [Paragraph("BẢNG CÂN ĐỐI VÀ CHỈ TIÊU TỔNG HỢP", s["Heading1"]),
             Paragraph("Số liệu tổng hợp giả lập dành riêng cho kiểm thử phần mềm.", s["Normal"]),
             Spacer(1, 8), styled_table(data, [55*mm, 28*mm, 28*mm, 38*mm]),
             Spacer(1, 6), Paragraph("Quy ước: số trong ngoặc đơn là số âm.", s["Normal"])]
    doc(OUT / "C_financial_statement.pdf", story)


def chart_base(path: Path, title: str, chart_kind: str, labels: list[tuple[str, str]], draw_chart):
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    c.setFont("FixtureSansBold", 18); c.drawString(45, height - 55, title)
    c.setFont("FixtureSans", 11); c.drawString(45, height - 78, f"Loại biểu đồ: {chart_kind}")
    draw_chart(c, width, height)
    y = 185
    c.setFont("FixtureSans", 11)
    for label, value in labels:
        c.drawString(55, y, f"{label}: {value}"); y -= 18
    c.drawString(55, y - 8, "Các giá trị trên là nhãn số gốc của biểu đồ kiểm thử.")
    c.save()


def make_bar_line_charts():
    path = OUT / "D_bar_line_charts.pdf"
    c = canvas.Canvas(str(path), pagesize=A4); width, height = A4
    c.setFont("FixtureSansBold", 18); c.drawString(45, height-55, "BIỂU ĐỒ CỘT DOANH THU")
    values = [("2022", 80), ("2023", 100), ("2024", 125)]
    for i,(year,value) in enumerate(values):
        x=90+i*110; c.setFillColor(colors.HexColor("#4F81BD")); c.rect(x,260,55,value*2,fill=1)
        c.setFillColor(colors.black); c.setFont("FixtureSans",10); c.drawString(x,245,year)
    c.setFont("FixtureSans",11); y=185
    for year,value in values: c.drawString(55,y,f"{year}: {value} triệu đồng"); y-=18
    c.showPage(); c.setFont("FixtureSansBold",18); c.drawString(45,height-55,"BIỂU ĐỒ ĐƯỜNG HAI CHUỖI")
    c.setFont("FixtureSans",11); c.drawString(45,height-78,"Chú giải: Chuỗi A và Chuỗi B")
    points_a=[(100,320),(220,380),(340,440)]; points_b=[(100,400),(220,390),(340,370)]
    c.setStrokeColor(colors.blue); c.line(*points_a[0],*points_a[1]); c.line(*points_a[1],*points_a[2])
    c.setStrokeColor(colors.red); c.line(*points_b[0],*points_b[1]); c.line(*points_b[1],*points_b[2])
    c.setFillColor(colors.black); labels=[("Chuỗi A 2022","60"),("Chuỗi A 2023","90"),("Chuỗi A 2024","120"),("Chuỗi B 2022","100"),("Chuỗi B 2023","95"),("Chuỗi B 2024","85")]
    y=250
    for label,value in labels: c.drawString(55,y,f"{label}: {value}"); y-=18
    c.save()


def make_pie_chart():
    def draw(c, width, height):
        c.setFillColor(colors.HexColor("#4F81BD")); c.wedge(150,300,390,540,90,180,fill=1)
        c.setFillColor(colors.HexColor("#C0504D")); c.wedge(150,300,390,540,270,90,fill=1)
        c.setFillColor(colors.HexColor("#9BBB59")); c.wedge(150,300,390,540,0,90,fill=1)
    chart_base(OUT / "E_pie_chart.pdf", "BIỂU ĐỒ TRÒN CƠ CẤU KHÁCH HÀNG", "pie chart",
               [("Cá nhân", "50%"), ("Doanh nghiệp", "30%"), ("Khác", "20%")], draw)


def make_process_diagram():
    path=OUT/"F_process_diagram.pdf"; c=canvas.Canvas(str(path),pagesize=A4); width,height=A4
    c.setFont("FixtureSansBold",18); c.drawString(45,height-55,"SƠ ĐỒ QUY TRÌNH PHÊ DUYỆT KHOẢN VAY")
    labels=["Tiếp nhận hồ sơ","Thẩm định","Phê duyệt","Giải ngân"]
    for i,label in enumerate(labels):
        x=45+i*135; y=390; c.setStrokeColor(colors.HexColor("#385D8A")); c.roundRect(x,y,105,55,6,stroke=1,fill=0)
        c.setFont("FixtureSans",10); c.drawCentredString(x+52,y+25,label)
        if i<len(labels)-1: c.line(x+105,y+27,x+132,y+27); c.line(x+125,y+32,x+132,y+27); c.line(x+125,y+22,x+132,y+27)
    c.setFont("FixtureSans",11); c.drawString(45,330,"Quy trình gồm bốn bước theo thứ tự từ trái sang phải."); c.save()


def make_scanned():
    image=Image.new("RGB",(1240,1754),"white"); draw=ImageDraw.Draw(image)
    font=ImageFont.truetype(str(ARIAL),38); bold=ImageFont.truetype(str(ARIAL_BOLD),46)
    draw.text((90,100),"TÀI LIỆU QUÉT - OCR FIXTURE",font=bold,fill="black")
    draw.text((90,220),"Doanh thu năm 2024 là 250 triệu đồng.",font=font,fill="black")
    draw.text((90,290),"Lợi nhuận năm 2024 là 40 triệu đồng.",font=font,fill="black")
    png=OUT/"_scan_source.png"; image.save(png)
    c=canvas.Canvas(str(OUT/"G_scanned_document.pdf"),pagesize=A4)
    c.drawImage(ImageReader(str(png)),0,0,width=A4[0],height=A4[1]); c.save(); png.unlink()


def make_multi_column():
    path=OUT/"H_multi_column.pdf"; c=canvas.Canvas(str(path),pagesize=A4); width,height=A4
    c.setFont("FixtureSansBold",18); c.drawString(45,height-55,"TÀI LIỆU HAI CỘT")
    c.setFont("FixtureSans",10)
    left=["Cột trái: Đổi mới kiến trúc thay đổi cách các thành phần liên kết với nhau.","Nó có thể giữ nguyên kiến thức về từng thành phần.","Thiết kế chủ đạo định hình kỳ vọng của thị trường."]
    right=["Cột phải: Đổi mới thành phần thay đổi một bộ phận cụ thể.","Quan hệ tổng thể của hệ thống có thể được giữ ổn định.","Doanh nghiệp cần nhận biết loại tri thức bị thay đổi."]
    y=height-100
    for line in left: c.drawString(45,y,line); y-=32
    y=height-100
    for line in right: c.drawString(width/2+10,y,line); y-=32
    c.save()


def make_multipage_table():
    s=styles(); header=["Mã", "Quý", "Giá trị (tỷ đồng)"]
    first=[[f"A{i:02d}",f"Q{(i-1)%4+1}",str(i*10)] for i in range(1,16)]
    second=[[f"A{i:02d}",f"Q{(i-1)%4+1}",str(i*10)] for i in range(16,31)]
    story=[Paragraph("BẢNG 2. DỮ LIỆU NHIỀU TRANG",s["Heading1"]),styled_table([header]+first,[35*mm,35*mm,55*mm]),PageBreak(),
           Paragraph("BẢNG 2 (tiếp theo). DỮ LIỆU NHIỀU TRANG",s["Heading1"]),styled_table([header]+second,[35*mm,35*mm,55*mm])]
    doc(OUT/"I_multipage_table.pdf",story)


def make_mixed_language():
    s=styles(); data=[["Metric / Chỉ tiêu","2023","2024","Unit / Đơn vị"],["Revenue / Doanh thu","200","240","USD million"],["Margin / Biên lợi nhuận","10%","12%","percent"]]
    story=[Paragraph("BILINGUAL FINANCIAL NOTE / GHI CHÚ TÀI CHÍNH SONG NGỮ",s["Heading1"]),
           Paragraph("Revenue increased because the test dataset moved from 200 to 240. Doanh thu tăng trong bộ dữ liệu kiểm thử.",s["Normal"]),Spacer(1,8),styled_table(data,[55*mm,25*mm,25*mm,45*mm])]
    doc(OUT/"J_mixed_vi_en.pdf",story)


def make_scanned_financial_table():
    image = Image.new("RGB", (1800, 1200), "white")
    draw = ImageDraw.Draw(image)
    title = ImageFont.truetype(str(ARIAL_BOLD), 54)
    font = ImageFont.truetype(str(ARIAL), 42)
    bold = ImageFont.truetype(str(ARIAL_BOLD), 42)
    draw.text((100, 70), "BÁO CÁO TÀI CHÍNH QUÉT", font=title, fill="black")
    x_positions = [100, 900, 1250, 1580]
    y_positions = [210, 330, 450, 570, 690]
    rows = [
        ["Chỉ tiêu", "2023", "2024", "Đơn vị"],
        ["Doanh thu", "100", "180", "tỷ đồng"],
        ["Lợi nhuận", "12", "16", "tỷ đồng"],
        ["Tổng tài sản", "300", "360", "tỷ đồng"],
    ]
    # Whitespace-aligned scan: still a table, while avoiding artificial grid
    # lines that can merge with digits during OCR.
    for row_index, row in enumerate(rows):
        for column_index, value in enumerate(row):
            row_font = bold if row_index == 0 or column_index in {1, 2} else font
            draw.text((x_positions[column_index], y_positions[row_index] + 28), value, font=row_font, fill="black")
    draw.text((100, 820), "Ghi chú: số liệu tổng hợp dùng cho kiểm thử OCR cục bộ.", font=font, fill="black")
    png = OUT / "_scan_table_source.png"
    image.save(png)
    c = canvas.Canvas(str(OUT / "K_scanned_financial_table.pdf"), pagesize=A4)
    c.drawImage(ImageReader(str(png)), 0, 0, width=A4[0], height=A4[1])
    c.showPage()
    english = Image.new("RGB", (1800, 1200), "white")
    english_draw = ImageDraw.Draw(english)
    english_draw.text((100, 70), "SCANNED FINANCIAL STATEMENT", font=title, fill="black")
    english_rows = [
        ["Metric", "2023", "2024", "Unit"],
        ["Revenue", "100", "180", "USD million"],
        ["Profit", "12", "16", "USD million"],
        ["Total assets", "300", "360", "USD million"],
    ]
    for row_index, row in enumerate(english_rows):
        for column_index, value in enumerate(row):
            row_font = bold if row_index == 0 or column_index in {1, 2} else font
            english_draw.text((x_positions[column_index], y_positions[row_index] + 28), value,
                              font=row_font, fill="black")
    english_draw.text((100, 820), "Note: synthetic figures for local OCR verification.", font=font, fill="black")
    english_png = OUT / "_scan_table_english_source.png"
    english.save(english_png)
    c.drawImage(ImageReader(str(english_png)), 0, 0, width=A4[0], height=A4[1])
    c.save()
    png.unlink()
    english_png.unlink()


def make_mixed_all_modalities():
    path = OUT / "L_mixed_text_table_chart.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    c.setFont("FixtureSansBold", 17)
    c.drawString(42, height - 48, "BÁO CÁO TỔNG HỢP: VĂN BẢN, BẢNG VÀ BIỂU ĐỒ")
    c.setFont("FixtureSans", 10)
    c.drawString(42, height - 70, "Doanh thu tăng cùng với lợi nhuận trong dữ liệu kiểm thử.")
    data = [["Chỉ tiêu", "2023", "2024", "Đơn vị"],
            ["Doanh thu", "100", "125", "tỷ đồng"],
            ["Lợi nhuận", "12", "16", "tỷ đồng"]]
    table = styled_table(data, [55*mm, 25*mm, 25*mm, 35*mm])
    table.wrapOn(c, width, height)
    table.drawOn(c, 42, height - 205)
    cash_data = [["Dòng tiền", "2023", "2024"], ["Kinh doanh", "20", "28"]]
    cash_table = styled_table(cash_data, [55*mm, 30*mm, 30*mm])
    cash_table.wrapOn(c, width, height)
    cash_table.drawOn(c, 42, height - 285)
    c.setFont("FixtureSansBold", 13)
    c.drawString(42, 440, "BIỂU ĐỒ CỘT DOANH THU")
    for index, (year, value) in enumerate((("2023", 100), ("2024", 125))):
        x = 100 + index * 150
        c.setFillColor(colors.HexColor("#4F81BD"))
        c.rect(x, 170, 70, value * 1.5, fill=1)
        c.setFillColor(colors.black)
        c.setFont("FixtureSans", 10)
        c.drawString(x, 152, year)
        c.drawString(390, 390 - index * 22, f"{year}: {value} tỷ đồng")
    c.save()


def make_image_only_chart():
    image = Image.new("RGB", (1600, 1100), "white")
    draw = ImageDraw.Draw(image)
    title = ImageFont.truetype(str(ARIAL_BOLD), 52)
    font = ImageFont.truetype(str(ARIAL), 40)
    draw.text((100, 60), "BIỂU ĐỒ CỘT DOANH THU QUÉT", font=title, fill="black")
    values = [("2022", 80), ("2023", 100), ("2024", 125)]
    for index, (year, value) in enumerate(values):
        x = 180 + index * 310
        draw.rectangle((x, 800 - value * 4, x + 130, 800), fill="#4F81BD", outline="black", width=3)
        draw.text((x, 830), year, font=font, fill="black")
        draw.text((1120, 300 + index * 90), f"{year}: {value} tỷ đồng", font=font, fill="black")
    png = OUT / "_scan_chart_source.png"
    image.save(png)
    c = canvas.Canvas(str(OUT / "M_image_only_chart.pdf"), pagesize=A4)
    c.drawImage(ImageReader(str(png)), 0, 0, width=A4[0], height=A4[1])
    c.save()
    png.unlink()


def main():
    make_text_vi(); make_mixed_table(); make_financial_statement(); make_bar_line_charts()
    make_pie_chart(); make_process_diagram(); make_scanned(); make_multi_column()
    make_multipage_table(); make_mixed_language()
    make_scanned_financial_table(); make_mixed_all_modalities(); make_image_only_chart()
    for path in sorted(OUT.glob("*.pdf")):
        print(path.name, path.stat().st_size)


if __name__ == "__main__":
    main()
