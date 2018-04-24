import pygame
from animation import animation
from pygame.transform import scale, rotozoom

from patchworkorange.core.ui import surface_clipping_context


class SuperSprite(pygame.sprite.DirtySprite):
    dirty = False

    def __init__(self, *args, **kwargs):
        self.rect = None  # type: pygame.Rect
        super(SuperSprite, self).__init__(*args)
        self.visible = True
        self._rotation = 0
        self._image = None  # type: pygame.Surface
        self._original_image = None
        self._width = 0
        self._height = 0
        self._needs_rescale = False
        self._needs_update = False

    def draw(self, surface, rect=None):
        """ Draw the sprite to the surface
        This operation does not scale the sprite, so it may exceed
        the size of the area passed.
        :param surface: Surface to be drawn on
        :param rect: Area to contain the sprite
        :return: Area of the surface that was modified
        :rtype: pygame.rect.Rect
        """
        # should draw to surface without generating a cached copy
        if rect is None:
            rect = surface.get_rect()
        return self._draw(surface, rect)

    def _draw(self, surface, rect):
        return surface.blit(self._image, rect)

    @property
    def image(self):
        # should always be a cached copy
        if self._needs_update:
            self.update_image()
            self._needs_update = False
            self._needs_rescale = False

        return self._image

    @image.setter
    def image(self, image):
        if image is None:
            self._original_image = None
            return

        if hasattr(self, 'rect'):
            self.rect.size = image.get_size()
        else:
            self.rect = image.get_rect()

        self._original_image = image
        self._needs_update = True

    def update_image(self):
        if self._needs_rescale:
            w = self.rect.width if self._width is None else self._width
            h = self.rect.height if self._height is None else self._height
            image = scale(self._original_image, (w, h))
            center = self.rect.center
            self.rect.size = w, h
            self.rect.center = center
        else:
            image = self._original_image

        if self._rotation:
            image = rotozoom(image, self._rotation, 1)
            rect = image.get_rect(center=self.rect.center)
            self.rect.size = rect.size
            self.rect.center = rect.center

        self._width, self._height = self.rect.size
        self._image = image

    @property
    def rotation(self):
        return self._rotation

    @rotation.setter
    def rotation(self, value):
        value = int(round(value, 0)) % 360
        if not value == self._rotation:
            self._rotation = value
            self._needs_update = True


class SpriteGroup(pygame.sprite.LayeredUpdates):
    """ Sane variation of a pygame sprite group
    Features:
    * Supports Layers
    * Supports Index / Slice
    * Supports skipping sprites without an image
    * Supports sprites with visible flag
    * Get bounding rect of all children
    * Animations
    Variations from standard group:
    * SpriteGroup.add no longer accepts a sequence, use SpriteGroup.extend
    """
    _init_rect = pygame.Rect(0, 0, 0, 0)

    def __init__(self, *args, **kwargs):
        self._spritelayers = dict()
        self._spritelist = list()
        pygame.sprite.AbstractGroup.__init__(self)
        self._default_layer = kwargs.get('default_layer', 0)
        self._animations = pygame.sprite.Group()

    def __nonzero__(self):
        return bool(self._spritelist)

    def __getitem__(self, item):
        # patch in indexing / slicing support
        return self._spritelist.__getitem__(item)

    def animate(self, *args, **kwargs):
        ani = animation.Animation(*args, **kwargs)
        self._animations.add(ani)
        return ani

    def update(self, *args):
        for s in self.sprites():
            s.update(*args)
        self._animations.update(args[0])

    def draw(self, surface):
        spritedict = self.spritedict
        surface_blit = surface.blit
        dirty = self.lostsprites
        self.lostsprites = []
        dirty_append = dirty.append

        for s in self.sprites():
            if getattr(s, "image", None) is None:
                continue

            if not getattr(s, 'visible', True):
                continue

            r = spritedict[s]
            newrect = surface_blit(s.image, s.rect)
            if r:
                if newrect.colliderect(r):
                    dirty_append(newrect.union(r))
                else:
                    dirty_append(newrect)
                    dirty_append(r)
            else:
                dirty_append(newrect)
            spritedict[s] = newrect
        return dirty

    def extend(self, sprites, **kwargs):
        """ Add a sequence of sprites to the SpriteGroup
        :param sprites: Sequence (list, set, etc)
        :param kwargs:
        :returns: None
        """
        if '_index' in kwargs.keys():
            raise KeyError
        for index, sprite in enumerate(sprites):
            kwargs['_index'] = index
            self.add(sprite, **kwargs)

    def add(self, sprite, **kwargs):
        """ Add a sprite to group.  do not pass a sequence or iterator
        LayeredUpdates.add(*sprites, **kwargs): return None
        If the sprite you add has an attribute _layer, then that layer will be
        used. If **kwarg contains 'layer', then the passed sprites will be
        added to that layer (overriding the sprite._layer attribute). If
        neither the sprite nor **kwarg has a 'layer', then the default layer is
        used to add the sprites.
        """
        layer = kwargs.get('layer')
        if isinstance(sprite, pygame.sprite.Sprite):
            if not self.has_internal(sprite):
                self.add_internal(sprite, layer)
                sprite.add_internal(self)
        else:
            raise TypeError

    def calc_bounding_rect(self):
        """A rect object that contains all sprites of this group
        """
        sprites = self.sprites()
        if not sprites:
            return self.rect
        elif len(sprites) == 1:
            return pygame.Rect(sprites[0].rect)
        else:
            return sprites[0].rect.unionall([s.rect for s in sprites[1:]])


class RelativeGroup(SpriteGroup):
    """
    Drawing operations are relative to the group's rect
    """
    rect = pygame.Rect(0, 0, 0, 0)

    def __init__(self, rect, **kwargs):
        super(RelativeGroup, self).__init__(**kwargs)
        self.rect = pygame.Rect(rect)
        self.parent = kwargs.get('parent')

    def draw(self, surface):
        # self.update_rect_from_parent()
        topleft = self.rect.topleft

        spritedict = self.spritedict
        surface_blit = surface.blit
        dirty = self.lostsprites
        self.lostsprites = []
        dirty_append = dirty.append

        with surface_clipping_context(surface, self.rect):
            for s in self.sprites():
                if s.image is None:
                    continue

                if not getattr(s, 'visible', True):
                    continue

                r = spritedict[s]
                newrect = surface_blit(s.image, s.rect.move(topleft))
                if r:
                    if newrect.colliderect(r):
                        dirty_append(newrect.union(r))
                    else:
                        dirty_append(newrect)
                        dirty_append(r)
                else:
                    dirty_append(newrect)
                spritedict[s] = newrect
            return dirty
