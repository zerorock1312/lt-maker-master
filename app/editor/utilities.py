from PyQt5 import QtGui

from app.constants import COLORKEY
from app.data.palettes import enemy_colors, other_colors, enemy2_colors

qCOLORKEY = QtGui.qRgb(*COLORKEY)
qAlpha = QtGui.qRgba(0, 0, 0, 0)

def convert_colorkey_slow(image):
    image.convertTo(QtGui.QImage.Format_ARGB32)
    for x in range(image.width()):
        for y in range(image.height()):
            if image.pixel(x, y) == qCOLORKEY:
                image.setPixel(x, y, qAlpha)
    return image

def convert_colorkey(image):
    new_image = image.convertToFormat(QtGui.QImage.Format_Indexed8)
    num_colors = new_image.colorCount()
    if num_colors > 192:
        return convert_colorkey_slow(image)
    for i in range(new_image.colorCount()):
        if new_image.color(i) == qCOLORKEY:
            new_image.setColor(i, qAlpha)
            break
    image = new_image.convertToFormat(QtGui.QImage.Format_ARGB32)
    return image

enemy_colors = {QtGui.qRgb(*k): QtGui.qRgb(*v) for k, v in enemy_colors.items()}
other_colors = {QtGui.qRgb(*k): QtGui.qRgb(*v) for k, v in other_colors.items()}
enemy2_colors = {QtGui.qRgb(*k): QtGui.qRgb(*v) for k, v in enemy2_colors.items()}

def color_convert_slow(image, conversion_dict):
    image.convertTo(QtGui.QImage.Format_ARGB32)
    for x in range(image.width()):
        for y in range(image.height()):
            current_color = image.pixel(x, y)
            if current_color in conversion_dict:
                new_color = conversion_dict[current_color]
                image.setPixel(x, y, new_color)
    return image

def color_convert(image, conversion_dict):
    new_image = image.convertToFormat(QtGui.QImage.Format_Indexed8)
    num_colors = new_image.colorCount()
    if num_colors > 192:
        return color_convert_slow(image, conversion_dict)
    for old_color, new_color in conversion_dict.items():
        for i in range(new_image.colorCount()):
            if new_image.color(i) == old_color:
                new_image.setColor(i, new_color)
    return new_image.convertToFormat(QtGui.QImage.Format_RGB32)

def find_palette(image):
    palette = []
    for x in range(image.width()):
        for y in range(image.height()):
            current_color = image.pixel(x, y)
            if current_color not in palette:
                palette.append(current_color)
    color_palette = [QtGui.QColor(p) for p in palette]
    true_palette = [(c.red(), c.green(), c.blue()) for c in color_palette]
    return true_palette

def get_full_palette(image) -> list:
    """
    Returns list of 3-tuples
    """
    palette = []
    for x in range(image.width()):
        for y in range(image.height()):
            color = image.pixelColor(x, y)
            palette.append((color.red(), color.green(), color.blue()))
    return palette

def convert_gba(image):
    for i in range(image.colorCount()):
        color = QtGui.QColor(image.color(i))
        new_color = (color.red() // 8 * 8), (color.green() // 8 * 8), (color.blue() // 8 * 8)
        image.setColor(i, QtGui.qRgb(*new_color))
    return image

def get_bbox(image):
    min_x, max_x = image.width(), 0
    min_y, max_y = image.height(), 0

    # Assumes topleft color is exclude color
    # unless top right is qCOLORKEY, then uses qCOLORKEY
    exclude_color = image.pixel(0, 0)
    test_color = image.pixel(image.width() - 1, 0)
    if test_color == qCOLORKEY:
        exclude_color = qCOLORKEY

    for x in range(image.width()):
        for y in range(image.height()):
            current_color = image.pixel(x, y)
            if current_color != exclude_color:
                if x < min_x:
                    min_x = x
                if x > max_x:
                    max_x = x
                if y < min_y:
                    min_y = y
                if y > max_y:
                    max_y = y
    # Returns x, y, width, height rect
    return (min_x, min_y, max_x - min_x, max_y - min_y)
