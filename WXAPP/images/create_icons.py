from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(text, bg_color, text_color, size=81):
    img = Image.new('RGBA', (size, size), bg_color)
    draw = ImageDraw.Draw(img)
    # 绘制圆形边框
    draw.ellipse([0, 0, size-1, size-1], outline=text_color, width=3)
    # 添加文字
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size//2)
    except:
        font = ImageFont.load_default()
    # 居中绘制文字
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = (size - w) // 2 - bbox[0]
    y = (size - h) // 2 - bbox[1]
    draw.text((x, y), text, fill=text_color, font=font)
    return img

# 创建图标
create_icon('首页', '#f5f5f5', '#999999', 81).save('home.png')
create_icon('首页', '#07c160', '#ffffff', 81).save('home-active.png')
create_icon('我', '#f5f5f5', '#999999', 81).save('my.png')
create_icon('我', '#07c160', '#ffffff', 81).save('my-active.png')

print("图标创建成功！")
