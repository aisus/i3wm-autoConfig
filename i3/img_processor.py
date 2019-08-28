import io
import math
import random
from PIL import Image, ImageDraw, ImageFilter

IMAGE_SMOOTH_RATE = 5


class MetaData(object):
    def __init__(self, artist=None, album=None, artUrl=None, image_bytes=None):
        self.artist = artist
        self.album = album
        self.artUrl = artUrl
        if image_bytes is not None:
            self.image_bytes = io.BytesIO(image_bytes)


def circle_and_blur(meta: MetaData, width, height):
    '''
    Default background provided by s3rius.
    Album cover cropped in circle in center of the screen, 
    with blurred and scaled up version of the same image in background
    '''

    cover = Image.open(meta.image_bytes)
    pixels = cover.getcolors(cover.height * cover.width)
    most_frequent_pixel = pixels[0]
    min_frequent_pixel = pixels[0]

    for count, colour in pixels:
        if count > most_frequent_pixel[0]:
            most_frequent_pixel = (count, colour)
        if count <= min_frequent_pixel[0]:
            min_frequent_pixel = (count, colour)

    big_cover_size = (cover.height * IMAGE_SMOOTH_RATE,
                      cover.width * IMAGE_SMOOTH_RATE)

    cover_mask = Image.new('L', big_cover_size, 0)
    mask_drawer = ImageDraw.Draw(cover_mask)
    mask_drawer.ellipse((0, 0) + big_cover_size, fill=255)
    cover_mask = cover_mask.resize(cover.size, Image.ANTIALIAS)
    cover.putalpha(cover_mask)

    gradient = scaled_blur(meta, width, height)
    gradient.paste(cover, ((width - cover.width) // 2,
                           (height - cover.height) // 2),
                   mask=cover_mask)
    return gradient


def scaled_blur(metadata: MetaData, width, heigth):
    back = Image.open(metadata.image_bytes)
    resize_rate = math.ceil(width / back.width)
    print(f"resize rate: {width}/{back.width}={resize_rate}")
    resized = back.resize(
        (back.width * resize_rate, back.height * resize_rate),
        Image.ANTIALIAS).filter(ImageFilter.GaussianBlur(8))
    resized = resized.crop(
        ((resized.width - width) / 2, (resized.height - heigth) / 2,
         (resized.width + width) / 2, (resized.height + heigth) / 2))
    return resized


def interpolate(f_co, t_co, interval):
    det_co = [(t - f) / interval for f, t in zip(f_co, t_co)]
    for i in range(interval):
        yield [round(f + det * i) for f, det in zip(f_co, det_co)]


def draw_linear_gradient(image, from_color, to_color, inversion, width):
    print("Generating linear gradient")
    if inversion:
        tmp = from_color
        from_color = to_color
        to_color = tmp
    drawer = ImageDraw.Draw(image)
    for i, color in enumerate(interpolate(from_color, to_color, width * 2)):
        drawer.line([(i, 0), (0, i)], tuple(color), width=1)


def draw_radial_gradient(image: Image, innerColor, outerColor, inversion, distances):
    print("Generating radial gradient.")
    if inversion:
        tmp = innerColor
        innerColor = outerColor
        outerColor = tmp
    imgsize = (image.width, image.height)
    for y in range(imgsize[1]):
        for x in range(imgsize[0]):
            distanceToCenter = distances[y][x]
            # Calculate r, g, and b values
            r = outerColor[0] * distanceToCenter + innerColor[0] * (
                1 - distanceToCenter)
            g = outerColor[1] * distanceToCenter + innerColor[1] * (
                1 - distanceToCenter)
            b = outerColor[2] * distanceToCenter + innerColor[2] * (
                1 - distanceToCenter)

            image.putpixel((x, y), (int(r), int(g), int(b)))


def genearate_gradinent(width, height, from_color, to_color, distances):
    gradient = Image.new('RGB', (width, height))
    inversion = random.randint(0, 1) == 0
    draw_radial_gradient(gradient, from_color, to_color, inversion, distances)
    #  draw_linear_gradient(gradient, from_color, to_color, inversion)
    return gradient
