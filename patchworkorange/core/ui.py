from contextlib import contextmanager
from itertools import product

import pygame


@contextmanager
def surface_clipping_context(surface, clip):
    original = surface.get_clip()
    surface.set_clip(clip)
    yield
    surface.set_clip(original)


class PyscrollGroup(pygame.sprite.LayeredUpdates):
    """ Layered Group with ability to center sprites and scrolling map
    """

    def __init__(self, *args, **kwargs):
        pygame.sprite.LayeredUpdates.__init__(self, *args, **kwargs)
        self._map_layer = kwargs.get('map_layer')

    def center(self, value):
        """ Center the group/map on a pixel
        The basemap and all sprites will be realigned to draw correctly.
        Centering the map will not change the rect of the sprites.
        :param value: x, y coordinates to center the camera on
        """
        self._map_layer.center(value)

    @property
    def view(self):
        """ Return a Rect representing visible portion of map
        This rect can be modified, but will not change the renderer
        :return: pygame.Rect
        """
        return self._map_layer.view_rect.copy()

    def draw(self, surface, rect):
        """ Draw all sprites and map onto the surface
        :param surface: pygame surface to draw to
        :type surface: pygame.surface.Surface
        """
        ox, oy = self._map_layer.get_center_offset()

        new_surfaces = list()
        spritedict = self.spritedict
        gl = self.get_layer_of_sprite
        new_surfaces_append = new_surfaces.append

        for spr in self.sprites():
            new_rect = spr.rect.move(ox, oy)
            try:
                new_surfaces_append((spr.image, new_rect, gl(spr), spr.blendmode))
            except AttributeError:  # generally should only fail when no blendmode available
                new_surfaces_append((spr.image, new_rect, gl(spr)))
            spritedict[spr] = new_rect

        self.lostsprites = []
        return self._map_layer.draw(surface, rect, new_surfaces)


class GraphicBox:
    def __init__(self, border=None, background=None, color=None, fill_tiles=False):
        super(GraphicBox, self).__init__()
        self._background = background
        self._color = color
        self._fill_tiles = fill_tiles
        self._tiles = list()
        self._tile_size = 0, 0
        self._rect = None
        if border:
            self._set_border(border)

    def _set_border(self, surface):
        iw, ih = surface.get_size()
        tw, th = iw // 3, ih // 3
        self._tile_size = tw, th
        self._tiles = [surface.subsurface((x, y, tw, th))
                       for x, y in product(range(0, iw, tw), range(0, ih, th))]

    def draw(self, surface, rect):
        inner = self.calc_inner_rect(rect)

        # fill center with solid _color
        if self._color:
            surface.fill(self._color, inner)

        # fill center with tiles from the border file
        elif self._fill_tiles:
            tw, th = self._tile_size
            p = product(range(inner.left, inner.right, tw),
                        range(inner.top, inner.bottom, th))
            [surface.blit(self._tiles[4], pos) for pos in p]

        # draw the border
        if self._tiles:
            surface_blit = surface.blit
            tile_nw, tile_w, tile_sw, tile_n, tile_c, tile_s, tile_ne, tile_e, tile_se = self._tiles
            left, top = rect.topleft
            tw, th = self._tile_size

            # draw top and bottom tiles
            for x in range(inner.left, inner.right, tw):
                if x + tw >= inner.right:
                    area = 0, 0, tw - (x + tw - inner.right), th
                else:
                    area = None
                surface_blit(tile_n, (x, top), area)
                surface_blit(tile_s, (x, inner.bottom), area)

            # draw left and right tiles
            for y in range(inner.top, inner.bottom, th):
                if y + th >= inner.bottom:
                    area = 0, 0, tw, th - (y + th - inner.bottom)
                else:
                    area = None
                surface_blit(tile_w, (left, y), area)
                surface_blit(tile_e, (inner.right, y), area)

            # draw corners
            surface_blit(tile_nw, (left, top))
            surface_blit(tile_sw, (left, inner.bottom))
            surface_blit(tile_ne, (inner.right, top))
            surface_blit(tile_se, (inner.right, inner.bottom))

    def calc_inner_rect(self, rect):
        if self._tiles:
            tw, th = self._tile_size
            return rect.inflate(- tw * 2, -th * 2)
        else:
            return rect


def draw_text(surface, text, rect, font=None, fg_color=None, bg_color=None, aa=False):
    """ draw some text into an area of a surface
    automatically wraps words
    returns size and any text that didn't get blit
    passing None as the surface is ok
    """
    if fg_color is None:
        fg_color = (0, 0, 0)

    total_width = 0
    rect = pygame.Rect(rect)
    y = rect.top
    line_spacing = -2

    if font is None:
        full_path = pygame.font.get_default_font()
        font = pygame.font.Font(full_path, 16)

    # get the height of the font
    font_height = font.size("Tg")[1]

    # for very small fonts, turn off antialiasing
    if font_height < 16:
        aa = 0
        bg_color = None

    while text:
        char_index = 1

        # determine if the row of text will be outside our area
        if y + font_height > rect.bottom:
            break

        # determine maximum width of line
        line_width = font.size(text[:char_index])[0]
        while line_width < rect.width and char_index < len(text):
            if text[char_index] == "\n":
                text = text[:char_index] + text[char_index + 1:]
                break

            char_index += 1
            line_width = font.size(text[:char_index])[0]
            total_width = max(total_width, line_width)
        else:
            # if we've wrapped the text, then adjust the wrap to the last word
            if char_index < len(text):
                char_index = text.rfind(" ", 0, char_index) + 1

        if surface:
            # render the line and blit it to the surface
            if bg_color:
                image = font.render(text[:char_index], aa, fg_color, bg_color)
                image.set_colorkey(bg_color)
            else:
                image = font.render(text[:char_index], aa, fg_color)

            surface.blit(image, (rect.left, y))

        y += font_height + line_spacing

        # remove the text we just blitted
        text = text[char_index:]

    return total_width, text
