#!/usr/bin/env python3
"""生成 findRightGuy 小红书封面图"""

from PIL import Image, ImageDraw, ImageFont
import os

W, H = 1080, 1080
OUT = os.path.join(os.path.dirname(__file__), "cover.png")

# ── 字体 ──────────────────────────────────────────────────────
FONT_PATHS = [
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
]

def load_font(size):
    for p in FONT_PATHS:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()

font_tag   = load_font(28)
font_main1 = load_font(72)
font_main2 = load_font(86)
font_sub   = load_font(32)
font_foot  = load_font(26)

# ── 颜色 ─────────────────────────────────────────────────────
BG_TOP    = (26,  10, 46)
BG_BOT    = (13,  13, 43)
CARD_BG   = (40,  20, 70, 180)   # RGBA
WHITE     = (255, 255, 255)
PINK      = (255, 110, 199)
PURPLE    = (140,  60, 255)
ORANGE    = (255, 180,  60)
DIM       = (200, 180, 220)

# ── 工具函数 ──────────────────────────────────────────────────
def gradient_bg(draw, w, h):
    for y in range(h):
        t = y / h
        r = int(BG_TOP[0] + (BG_BOT[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOT[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOT[2] - BG_TOP[2]) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

def gradient_text(img, text, font, x, y, colors, center_w=None):
    """逐字符渲染渐变色文字"""
    tmp = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    # 总宽度
    total_w = sum(font.getlength(c) for c in text)
    if center_w is not None:
        x = (center_w - total_w) // 2
    cx = x
    for i, ch in enumerate(text):
        t = i / max(len(text) - 1, 1)
        r = int(colors[0][0] + (colors[1][0] - colors[0][0]) * t)
        g = int(colors[0][1] + (colors[1][1] - colors[0][1]) * t)
        b = int(colors[0][2] + (colors[1][2] - colors[0][2]) * t)
        d.text((cx, y), ch, font=font, fill=(r, g, b, 255))
        cx += font.getlength(ch)
    img.alpha_composite(tmp)

def center_text(draw, img_w, y, text, font, fill):
    w = font.getlength(text)
    draw.text(((img_w - w) / 2, y), text, font=font, fill=fill)

def rounded_rect(draw, xy, radius, fill):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill)

# ── 绘制 ──────────────────────────────────────────────────────
img  = Image.new("RGBA", (W, H), (0, 0, 0, 255))
draw = ImageDraw.Draw(img)

# 背景渐变
gradient_bg(draw, W, H)

# 装饰光晕
glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
gd   = ImageDraw.Draw(glow)
gd.ellipse((-120, -120, 440, 440), fill=(180, 60, 220, 28))
gd.ellipse((700, 700, 1200, 1200), fill=(100, 40, 255, 28))
gd.ellipse((580, 200, 980, 600),   fill=(255, 140, 40, 18))
img = Image.alpha_composite(img, glow)
draw = ImageDraw.Draw(img)

# 卡片
CARD = Image.new("RGBA", (W, H), (0, 0, 0, 0))
cd   = ImageDraw.Draw(CARD)
rounded_rect(cd, (90, 90, 990, 990), 40, (50, 20, 85, 190))
img  = Image.alpha_composite(img, CARD)
draw = ImageDraw.Draw(img)

# 四角装饰线
corner_color = (255, 110, 199, 120)
cc = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ccd = ImageDraw.Draw(cc)
for ox, oy, dx, dy in [(110,110,1,1),(970,110,-1,1),(110,970,1,-1),(970,970,-1,-1)]:
    ccd.line([(ox, oy), (ox + dx*50, oy)], fill=corner_color, width=3)
    ccd.line([(ox, oy), (ox, oy + dy*50)], fill=corner_color, width=3)
img = Image.alpha_composite(img, cc)
draw = ImageDraw.Draw(img)

# Tag 标签
tag_text = "Claude Code Skill"
tag_w = int(font_tag.getlength(tag_text)) + 48
tag_x = (W - tag_w) // 2
tag_y = 168
tg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
tgd = ImageDraw.Draw(tg)
tgd.rounded_rectangle([tag_x, tag_y, tag_x + tag_w, tag_y + 46], radius=23,
                       fill=(180, 60, 220, 200))
img = Image.alpha_composite(img, tg)
draw = ImageDraw.Draw(img)
draw.text((tag_x + 24, tag_y + 9), tag_text, font=font_tag, fill=WHITE)

# 主标题第一行
line1 = "蒸馏一个前任？不，"
w1 = font_main1.getlength(line1)
draw.text(((W - w1) / 2, 258), line1, font=font_main1, fill=WHITE)

# 主标题第二行：「我要蒸馏」白色 + 「10个」渐变 + 「！！！」橙色
line2_a = "我要蒸馏"
line2_b = "10个"
line2_c = "！！！"
wa = font_main2.getlength(line2_a)
wb = font_main2.getlength(line2_b)
wc = font_main2.getlength(line2_c)
total2 = wa + wb + wc
x2 = (W - total2) / 2
y2 = 358
draw.text((x2, y2), line2_a, font=font_main2, fill=WHITE)
# 「10个」渐变（逐字）
gradient_text(img, line2_b, font_main2, int(x2 + wa), y2, [PINK, ORANGE])
draw = ImageDraw.Draw(img)
draw.text((x2 + wa + wb, y2), line2_c, font=font_main2, fill=ORANGE)

# 分割线
div_x0 = (W - 100) // 2
draw.rounded_rectangle([div_x0, 510, div_x0 + 100, 514], radius=2,
                        fill=(255, 110, 199, 180))

# 副标题
subs = [
    ("量变引起质变的典型应用", DIM),
    ("把所有前任的聊天记录丢进去", DIM),
    ("提炼出属于你的理想对象画像", WHITE),
]
for i, (txt, col) in enumerate(subs):
    center_text(draw, W, 548 + i * 58, txt, font_sub, col)

# 底部 footer
foot_a = "findRightGuy"
foot_sep = "  ·  "
foot_b = "前任越多，画像越准"
fw_a = font_foot.getlength(foot_a)
fw_s = font_foot.getlength(foot_sep)
fw_b = font_foot.getlength(foot_b)
fx = (W - fw_a - fw_s - fw_b) / 2
fy = 870
gradient_text(img, foot_a, font_foot, int(fx), fy, [PINK, PURPLE])
draw = ImageDraw.Draw(img)
draw.text((fx + fw_a, fy), foot_sep, font=font_foot, fill=(150, 120, 180))
draw.text((fx + fw_a + fw_s, fy), foot_b, font=font_foot, fill=(180, 160, 200))

# 保存
final = img.convert("RGB")
final.save(OUT, "PNG", quality=95)
print(f"已生成：{OUT}")
