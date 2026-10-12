"""Create a fresh internal holdout after quality-hardening implementation."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests/fixtures/quality_holdout"
OUT.mkdir(parents=True, exist_ok=True)
pdfmetrics.registerFont(TTFont("Holdout", r"C:\Windows\Fonts\arial.ttf"))
pdfmetrics.registerFont(TTFont("HoldoutBold", r"C:\Windows\Fonts\arialbd.ttf"))


def heading(c, text, y):
    c.setFont("HoldoutBold", 16); c.drawString(45, y, text)


def borderless():
    c=canvas.Canvas(str(OUT/"H1_borderless_bilingual.pdf"),pagesize=A4); w,h=A4
    heading(c,"BÁO CÁO CHỈ TIÊU / METRIC REPORT",h-55)
    rows=[("Chỉ tiêu / Metric","2024","2025","Đơn vị / Unit"),("Doanh thu / Revenue","240","300","tỷ đồng"),("Lợi nhuận / Profit","36","48","tỷ đồng")]
    ys=[h-110,h-145,h-180]; xs=[50,300,380,455]
    for ri,row in enumerate(rows):
        c.setFont("HoldoutBold" if ri==0 else "Holdout",11)
        for x,value in zip(xs,row): c.drawString(x,ys[ri],value)
    c.setFont("Holdout",10); c.drawString(50,h-225,"Bảng không có đường viền. Biên lợi nhuận 2025 được tính từ lợi nhuận chia doanh thu.")
    c.save()


def multi_company():
    c=canvas.Canvas(str(OUT/"H2_multi_company.pdf"),pagesize=A4); w,h=A4
    heading(c,"SO SÁNH HAI CÔNG TY",h-55)
    data=[("Công ty","Doanh thu 2024","Lợi nhuận 2024","Đơn vị"),("An Phát","500","50","tỷ đồng"),("Bình Minh","420","63","tỷ đồng")]
    x=[50,205,345,470]; y=h-105
    for r,row in enumerate(data):
        c.setFont("HoldoutBold" if r==0 else "Holdout",11)
        for xx,val in zip(x,row): c.drawString(xx,y-r*32,val)
        c.line(45,y-r*32-5,545,y-r*32-5)
    c.setFont("Holdout",10); c.drawString(50,h-225,"Dữ liệu kiểm thử độc lập; không đại diện doanh nghiệp có thật.")
    c.save()


def mixed():
    c=canvas.Canvas(str(OUT/"H3_mixed_table_chart.pdf"),pagesize=landscape(A4)); w,h=landscape(A4)
    heading(c,"DÒNG TIỀN VÀ CƠ CẤU NGUỒN VỐN",h-45)
    c.setFont("HoldoutBold",11); c.drawString(45,h-85,"Bảng 1. Dòng tiền")
    rows=[("Hoạt động","2023","2024","Đơn vị"),("Kinh doanh","70","95","tỷ đồng"),("Đầu tư","(20)","(35)","tỷ đồng")]
    for r,row in enumerate(rows):
        for col,val in enumerate(row): c.drawString(45+col*120,h-115-r*27,val)
    c.setFont("HoldoutBold",11); c.drawString(475,h-85,"Biểu đồ 1. Cơ cấu nguồn vốn 2024")
    pairs=[("Vốn chủ sở hữu","60%",colors.HexColor("#3076B8")),("Nợ phải trả","40%",colors.HexColor("#E07A35"))]
    x=480
    for label,value,color in pairs:
        c.setFillColor(color); c.rect(x,h-210,80,int(value[:-1])*2,fill=1,stroke=0)
        c.setFillColor(colors.black); c.setFont("Holdout",10); c.drawString(x,h-230,f"{label}: {value}"); x+=145
    c.save()


def rotated_low_contrast():
    img=Image.new("RGB",(1700,1100),"white"); d=ImageDraw.Draw(img)
    font=ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf",38); bold=ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf",46)
    d.text((80,70),"BÁO CÁO QUÉT SONG NGỮ / BILINGUAL SCAN",font=bold,fill=(80,80,80))
    lines=["Chỉ tiêu / Metric     2024     2025     Đơn vị / Unit","Doanh thu / Revenue   310      372      tỷ đồng","Lợi nhuận / Profit     31       45      tỷ đồng","Ghi chú / Note: số liệu dùng cho kiểm thử OCR."]
    for i,line in enumerate(lines): d.text((90,180+i*95),line,font=font,fill=(105,105,105))
    img=ImageEnhance.Contrast(img).enhance(.62).rotate(2.2,expand=True,fillcolor="white")
    path=OUT/"_H4.png"; img.save(path)
    c=canvas.Canvas(str(OUT/"H4_rotated_low_contrast_scan.pdf"),pagesize=A4); w,h=A4
    c.drawImage(ImageReader(str(path)),25,120,width=w-50,height=h-210,preserveAspectRatio=True,anchor="c"); c.save(); path.unlink()


if __name__ == "__main__":
    borderless(); multi_company(); mixed(); rotated_low_contrast()
    print([p.name for p in sorted(OUT.glob("*.pdf"))])
