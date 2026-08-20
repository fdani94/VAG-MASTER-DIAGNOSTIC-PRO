from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZE = 512
OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "kid_vag_v2.ico"


def font(size: int):
    candidates = (
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    )
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def main() -> None:
    image = Image.new("RGBA", (SIZE, SIZE), (5, 13, 22, 255))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((18, 18, 494, 494), radius=105, fill=(8, 24, 39, 255), outline=(40, 183, 245, 255), width=12)
    draw.rounded_rectangle((38, 38, 474, 474), radius=90, outline=(30, 74, 106, 255), width=5)
    draw.polygon(((92, 105), (210, 318), (256, 242), (302, 318), (420, 105), (322, 190), (256, 294), (190, 190)), fill=(54, 183, 240, 255))
    draw.line(((92, 105), (210, 318), (256, 242), (302, 318), (420, 105)), fill=(224, 246, 255, 255), width=10, joint="curve")
    title_font = font(70)
    sub_font = font(34)
    title = "KID"
    box = draw.textbbox((0, 0), title, font=title_font)
    draw.text(((SIZE - (box[2] - box[0])) / 2, 330), title, font=title_font, fill=(242, 249, 255, 255), stroke_width=2, stroke_fill=(12, 103, 158, 255))
    subtitle = "VAG V2"
    box = draw.textbbox((0, 0), subtitle, font=sub_font)
    draw.text(((SIZE - (box[2] - box[0])) / 2, 410), subtitle, font=sub_font, fill=(73, 197, 250, 255))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(OUTPUT)


if __name__ == "__main__":
    main()
