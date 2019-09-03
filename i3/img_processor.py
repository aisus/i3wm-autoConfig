import io
import math
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import time

IMAGE_SMOOTH_RATE = 5
PREDEFINED_BG_IMAGE_NAME = 'mus_bg.png'


class MetaData(object):
    def __init__(self, artist=None, album=None, artUrl=None, image_bytes=None):
        self.artist = artist
        self.album = album
        self.artUrl = artUrl
        if image_bytes is not None:
            self.image_bytes = io.BytesIO(image_bytes)

# ==================================================================
# Complete functions to generate weird graphical stuff
# ==================================================================


def circle_and_blur(meta: MetaData, width, height):
    '''
    Default background provided by s3rius.
    Album cover cropped in circle in center of the screen, 
    with blurred and scaled up version of the same image in background
    '''

    cover = Image.open(meta.image_bytes)
    big_cover_size = (cover.height * IMAGE_SMOOTH_RATE,
                      cover.width * IMAGE_SMOOTH_RATE)

    cover_mask = Image.new('L', big_cover_size, 0)
    mask_drawer = ImageDraw.Draw(cover_mask)
    mask_drawer.ellipse((0, 0) + big_cover_size, fill=255)
    cover_mask = cover_mask.resize(cover.size, Image.ANTIALIAS)
    cover.putalpha(cover_mask)

    gradient = __scaled_blur(Image.open(meta.image_bytes), width, height)

    gradient.paste(cover, ((width - cover.width) // 2,
                           (height - cover.height) // 2),
                   mask=cover_mask)
    return gradient


def predefined_image_with_album_in_circle(meta: MetaData, width, height):
    '''
    Pre-defined image with some amount of blur, 
    album cover in circle at the center of the screen
    '''
    background = Image.open(PREDEFINED_BG_IMAGE_NAME)
    cover = Image.open(meta.image_bytes)

    big_cover_size = (cover.height * IMAGE_SMOOTH_RATE,
                      cover.width * IMAGE_SMOOTH_RATE)

    cover_mask = Image.new('L', big_cover_size, 0)
    mask_drawer = ImageDraw.Draw(cover_mask)
    mask_drawer.ellipse((0, 0) + big_cover_size, fill=255)
    cover_mask = cover_mask.resize(cover.size, Image.ANTIALIAS)
    cover.putalpha(cover_mask)

    gradient = __scaled_blur(background, width, height)

    gradient.paste(cover, ((width - cover.width) // 2,
                           (height - cover.height) // 2),
                   mask=cover_mask)
    return gradient


def linear_gradient_with_circle(meta: MetaData, width, height):
    '''
    Linear gradient from most to least common color in image, 
    album cover in circle at the center of the screen
    '''

    cover = Image.open(meta.image_bytes)
    big_cover_size = (cover.height * IMAGE_SMOOTH_RATE,
                      cover.width * IMAGE_SMOOTH_RATE)

    cover_mask = Image.new('L', big_cover_size, 0)
    mask_drawer = ImageDraw.Draw(cover_mask)
    mask_drawer.ellipse((0, 0) + big_cover_size, fill=255)
    cover_mask = cover_mask.resize(cover.size, Image.ANTIALIAS)
    cover.putalpha(cover_mask)

    (least_color, most_color) = __get_most_and_least_frequent_colors(cover)

    gradient = Image.new('RGB', (width, height))
    __draw_linear_gradient(gradient, most_color, least_color, False, width)

    gradient.paste(cover, ((width - cover.width) // 2,
                           (height - cover.height) // 2),
                   mask=cover_mask)
    return gradient


def radial_gradient_with_circle(meta: MetaData, width, height):
    '''
    Linear gradient from most to least common color in image, 
    album cover in circle at the center of the screen
    '''

    cover = Image.open(meta.image_bytes)
    big_cover_size = (cover.height * IMAGE_SMOOTH_RATE,
                      cover.width * IMAGE_SMOOTH_RATE)

    cover_mask = Image.new('L', big_cover_size, 0)
    mask_drawer = ImageDraw.Draw(cover_mask)
    mask_drawer.ellipse((0, 0) + big_cover_size, fill=255)
    cover_mask = cover_mask.resize(cover.size, Image.ANTIALIAS)
    cover.putalpha(cover_mask)

    (least_color, most_color) = __get_most_and_least_frequent_colors(cover)

    gradient = Image.new('RGB', (width, height))
    __draw_radial_gradient(gradient, most_color, least_color, True)

    gradient.paste(cover, ((width - cover.width) // 2,
                           (height - cover.height) // 2),
                   mask=cover_mask)
    return gradient

# ==================================================================
# From here goes the service functions and math for image processing
# ==================================================================


def __calculate_distances(width, height):
    
    start = time.time()

    xv, yv = np.meshgrid(np.linspace(0, width, width), np.linspace(0, height, height))
    print(f"W: {width}, H:{height}\n")
    norm = np.sqrt(2) * width / 2
    distances = np.sqrt((xv - width / 2) ** 2 + (yv - height / 2) ** 2) / norm
    
    elapsed = time.time() - start
    print(f"Elapsed time for distances: {elapsed}")
    return distances


def __get_most_and_least_frequent_colors(image: Image):
    pixels = image.getcolors(image.height * image.width)
    most_frequent_pixel = pixels[0]
    min_frequent_pixel = pixels[0]

    for count, colour in pixels:
        if count > most_frequent_pixel[0]:
            most_frequent_pixel = (count, colour)
        if count <= min_frequent_pixel[0]:
            min_frequent_pixel = (count, colour)

    _, min_color = min_frequent_pixel
    _, max_color = most_frequent_pixel
    return (min_color, max_color)


def __scaled_blur(image, width, heigth):
    back = image
    resize_rate = math.ceil(width / back.width)
    print(f"resize rate: {width}/{back.width}={resize_rate}")
    resized = back.resize(
        (back.width * resize_rate, back.height * resize_rate),
        Image.ANTIALIAS).filter(ImageFilter.GaussianBlur(8))
    resized = resized.crop(
        ((resized.width - width) / 2, (resized.height - heigth) / 2,
         (resized.width + width) / 2, (resized.height + heigth) / 2))
    return resized


def __interpolate(f_co, t_co, interval):
    det_co = [(t - f) / interval for f, t in zip(f_co, t_co)]
    for i in range(interval):
        yield [round(f + det * i) for f, det in zip(f_co, det_co)]


def __draw_linear_gradient(image, from_color, to_color, inversion, width):
    print("Generating linear gradient")
    if inversion:
        tmp = from_color
        from_color = to_color
        to_color = tmp
    drawer = ImageDraw.Draw(image)
    for i, color in enumerate(__interpolate(from_color, to_color, width * 2)):
        drawer.line([(i, 0), (0, i)], tuple(color), width=1)


def __draw_radial_gradient(image: Image, innerColor, outerColor, inversion):
    print("Generating radial gradient.")
    distances = __calculate_distances(image.width, image.height)
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


def __genearate_gradinent(width, height, from_color, to_color):
    gradient = Image.new('RGB', (width, height))
    distances = __calculate_distances(width, height)
    inversion = random.randint(0, 1) == 0
    __draw_radial_gradient(gradient, from_color,
                           to_color, inversion, distances)
    #  draw_linear_gradient(gradient, from_color, to_color, inversion)
    return gradient
