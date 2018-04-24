import logging
import random
import sys
import time
from collections import deque
from functools import partial

import pygame
from animation import Animation, Task, remove_animations_of
from pygame.locals import *
from pygame.math import Vector2
from pygame.sprite import Group, LayeredUpdates, Sprite
from pygame.transform import smoothscale

from patchworkorange.core.minigamemanager import Minigame
from patchworkorange.core.resources import get_image_asset, get_font_asset, get_sound_asset

logger = logging.getLogger(__name__)

SCREEN_SIZE = 1280, 720

"""
bootup sound:
https://freesound.org/people/BenKoning/sounds/49184/
font:
https://www.dafont.com/apple.font
"""


def none_or_not(d, name, func):
    value = d.get(name)
    if value is not None:
        return func(value)


def ternone(value, default):
    return default if value is None else value


def load_sound(filename):
    return pygame.mixer.Sound(get_sound_asset(filename))


def load_image(filename):
    return pygame.image.load(get_image_asset(filename))


def load_font(name, size):
    return pygame.font.Font(get_font_asset(name), size)


class Jackin(Minigame):
    GAME_NAME = "Jackin"
    _default_layer = 1

    charset = "1234567890QWERTYUIOPASDFGHJKLZXCVBNM,.?>&/="

    def __init__(self):
        super(Jackin, self).__init__()
        self.running = False
        self._sprites = LayeredUpdates()
        self._animations = Group()
        self.platten_speed = 40
        self.pressed = set()
        self.cpl = 40
        self.buffer = None
        self.cache = None
        self.char_height = 0
        self.char_width = 0
        self.platten = None
        self.paper = None
        self.mode = None
        self.fade_buffer = None
        self.screen_size = None

        self.cursor = Vector2(200, -70)

        self.document = list()
        self.document.append(list())
        self.current_line = 0

        font_name = 'Apple ][.ttf'
        font_size = 8
        ratio = 10
        color = pygame.Color('goldenrod')

        self.text = [
            ('display', '> '),
            ('wait', 1500),
            ('type', 'CD/HACK'),
            ('display', '\nHACK> '),
            ('type', '\nRUN HACK.BAS'),
            ('wait', 1000),
            ('type', '\nAT&F&D2&C1S0=0X4'),
            ('wait', 1500),
            ('display', '\nOK'),
            ('wait', 1000),
            ('type', '\nATDT0040745129711\n'),
            ('sound', 'modem'),
            ('wait', 18000),
            ('display', '\nCONNECT 14400')
        ]

        self.sounds = {
            'run': load_sound('run.wav'),
            'boot': load_sound('boot.wav'),
            'beep': load_sound('beep.wav'),
            'modem': load_sound('188828__0ktober__modem-dial.wav'),
            'spacebar': [load_sound(i) for i in [
                'spacebar01.wav',
                'spacebar02.wav']],
            'key': [load_sound(i) for i in [
                'keypress01.wav',
                'keypress02.wav',
                'keypress04.wav',
                'keypress05.wav',
                'keypress06.wav',
            ]]

        }

        self.generate_font(font_name, font_size, ratio, color)
        self.set_tab(0)

    def next_command(self):
        try:
            cmd, text = self.text.pop(0)
        except IndexError:
            self.fade_out()
            return

        if cmd == 'display':
            self.display(text)

        elif cmd == 'type':
            self.buffer = list(text)
            self.next_press()

        elif cmd == 'sound':
            self.sounds[text].play()
            self.next_command()

        elif cmd == 'wait':
            task = Task(self.next_command, text)
            self._animations.add(task)

    def next_press(self):
        try:
            self.press(self.buffer.pop(0))
        except IndexError:
            self.next_command()

        else:
            if random.randint(0, 20):
                task = Task(self.next_press, interval=random.randint(200, 400))
            else:
                task = Task(self.next_press, interval=random.randint(800, 1200))

            self._animations.add(task)

    def fade_out(self):
        if self.fade_buffer is None:
            self.fade_buffer = pygame.Surface(self.screen_size)
            self.fade_buffer.fill(0)

        ani = self.animate(self.fade_buffer, set_alpha=255, initial=0, duration=3000)
        ani.schedule(partial(setattr, self, 'running', False), 'on finish')

    def display(self, text):
        for char in text:
            self.strike(char, True)

        task = Task(self.next_command, interval=random.randint(600, 800))
        self._animations.add(task)

    def generate_font(self, font_name, font_size, ratio, color):
        self.cache = dict()

        padding = 8
        padding2 = padding * 2

        font = pygame.font.Font(get_font_asset(font_name), font_size)
        glyph = font.render('W', 1, (0, 0, 0))

        natural_size = glyph.get_size()
        scratch = natural_size[0] + padding2, natural_size[1] + padding2
        full_size = scratch[0] * ratio, scratch[1] * ratio

        # generate a scanline image to create scanline effect
        scanline = pygame.Surface(full_size, pygame.SRCALPHA)
        scolor = (64, 64, 64)
        for y in range(0, full_size[1], 4):
            pygame.draw.line(scanline, scolor, (0, y), (full_size[0], y))
            pygame.draw.line(scanline, scolor, (0, y + 1), (full_size[0], y + 1))

        for char in self.charset:
            original = font.render(char, 1, color)

            lined = pygame.Surface(natural_size, pygame.SRCALPHA)
            lined.blit(original, (0, 0))
            lined.blit(scanline, (0, 0))

            glyph = pygame.Surface(scratch, pygame.SRCALPHA)
            glyph.blit(original, (padding, padding))

            large_glyph = smoothscale(glyph, full_size)

            # norml_glyph.blit(scanline, (0, 0))

            bloom = smoothscale(glyph, (10, int(scratch[1] * .80)))
            bloom = smoothscale(bloom, full_size)

            image = pygame.Surface(full_size, pygame.SRCALPHA)
            image.blit(bloom, (0, 0))

            image.blit(large_glyph, (0, 0))
            image.blit(scanline, (0, 0), None, pygame.BLEND_SUB)

            self.cache[char] = image

        self.char_width = int(full_size[0] * .3)
        self.char_height = int(full_size[1] * .35)
        page_width = self.char_width * self.cpl
        self.platten = pygame.Rect(0, self.cursor.y, page_width, 100)
        self.paper = pygame.Rect(0, self.cursor.y, page_width, 1000)

    def initialize(self, context):
        pass

    @staticmethod
    def new_sprite(image, rect):
        sprite = Sprite()
        sprite.image = image
        sprite.rect = rect
        return sprite

    def animate(self, *args, **kwargs):
        ani = Animation(*args, **kwargs)
        self._animations.add(ani)
        return ani

    def add_sprite(self, image, rect, layer=None):
        self._sprites.add(self.new_sprite(image, rect),
                          layer=ternone(layer, self._default_layer))

    def run(self, context):
        flip = pygame.display.flip
        update = self.update
        draw = self.draw
        handle_events = self.handle_event
        screen = pygame.display.get_surface()
        clock = time.time
        frame_time = (1 / 60.) * 1000
        last_draw = 0
        times = deque(maxlen=10)

        self.sounds['boot'].play()
        self.sounds['run'].play(-1, fade_ms=200)

        task = Task(self.next_command, 2500)
        self._animations.add(task)

        self.screen_size = screen.get_size()

        self.running = True
        last_frame = clock()
        while self.running:
            dt = (clock() - last_frame) * 1000
            last_frame = clock()
            times.append(dt)
            dt = sum(times) / 10
            last_draw += dt
            handle_events()
            update(dt)
            if last_draw >= frame_time:
                draw(screen)

                if self.fade_buffer:
                    screen.blit(self.fade_buffer, (0, 0))

                flip()
                last_draw = 0

    def draw(self, surface):
        self._sprites.draw(surface)

        surface.fill((0, 0, 0))

        self.paper.left = self.platten.left

        for line_index, line in enumerate(self.document):
            for position, glyph in line:
                gx, gy = position
                x = gx
                y = gy + (line_index * self.char_height)
                surface.blit(glyph, self.paper.move(x, y))

    def update(self, dt):
        self._animations.update(dt)

    def handle_event(self):
        for event in pygame.event.get():
            if event.type == KEYDOWN:
                if event.key == K_SPACE:
                    self.fade_out()
            if event.type == QUIT:  # this will allow pressing the windows (X) to close the game
                sys.exit(0)

    def strike(self, char, now=False):
        self.paper.left = self.platten.left

        if char == ' ':
            self.advance_one(now)
            return

        elif char == '\n':
            self.cr()
            return

        try:
            glyph = self.cache[char]
            position = [int(self.cursor.x - self.paper.left), 10]
            self.document[self.current_line].append((position, glyph))
            self.advance_one(now)
            return glyph
        except KeyError:
            pass

    def advance_one(self, now=False):
        if now:
            self.platten.left -= self.char_width
        else:
            remove_animations_of(self.platten, self._animations)
            ani = Animation(left=-self.char_width, relative=True, duration=self.platten_speed)
            ani.start(self.platten)
            self._animations.add(ani)

    def press(self, char, sound=80):

        if char in self.charset:
            if sound:
                random.choice(self.sounds['key']).play()
            task = Task(partial(self.strike, char), sound)
        elif char == ' ':
            if sound:
                random.choice(self.sounds['spacebar']).play()
            task = Task(self.advance_one, sound)
        elif char == '\n':
            if sound:
                random.choice(self.sounds['key']).play()
            task = Task(self.cr, sound)
        else:
            raise ValueError(char)

        # don't show character right away b/c sound lag
        self._animations.add(task)

    def release(self, key):
        """

        :param key:
        :return:
        """
        if key in self.pressed:
            self.pressed.remove(key)
            self.advance_one()

    def bs(self):
        """ Backspace

        :return:
        """
        self.mode = 1
        remove_animations_of(self.platten, self._animations)
        ani = Animation(left=self.char_width, relative=True, duration=self.platten_speed)
        ani.start(self.platten)
        self._animations.add(ani)

    def cr(self):
        """ Carriage return

        :return:
        """
        self.current_line += 1
        self.document.append(list())
        self.set_tab(0)

    def set_tab(self, tab=0):
        self.platten.left = tab
        remove_animations_of(self.platten, self._animations)
        ani = Animation(left=0, duration=self.platten_speed)
        ani.start(self.platten)
        self._animations.add(ani)
