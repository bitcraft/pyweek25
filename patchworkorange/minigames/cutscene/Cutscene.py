import logging
import sys
import time
from collections import deque

import animation
import pygame
import yaml
from pygame.locals import *
from pygame.sprite import Group, LayeredUpdates, Sprite
from pygame.transform import smoothscale

from patchworkorange.core.minigamemanager import Minigame
from patchworkorange.core.resources import get_image_asset, get_font_asset, get_data_asset, get_sound_asset
from patchworkorange.core.simplefsm import SimpleFSM
from patchworkorange.core.ui import GraphicBox, surface_clipping_context, draw_text

logger = logging.getLogger(__name__)

SCREEN_SIZE = 1280, 720

"""
portrait notes:
- duplicate layer
- posterize until about 4-8 colors
- desaturate
- slight blur, 4-10% maybe
- set top alpha laer mode to multiply (i think)
- bottom layer, add noise, increase contrast slightly
- entire thing blur slightly

backgrounds:
- blur 25%
- reduce contrast
- desaturate
"""

nope = 'L6VLfxWUIXczsxTPPTHkT3X7EOvtdOLe'


def nope_or_not(d, name, func):
    value = d.get(name, nope)
    if value is not nope:
        func(value)


def none_or_not(d, name, func):
    value = d.get(name)
    if value is not None:
        return func(value)


def ternone(value, default):
    return default if value is None else value


def load_image(filename):
    return pygame.image.load(get_image_asset(filename))


def load_font(name, size):
    return pygame.font.Font(get_font_asset(name), size)


set_events = (
)

dialog_events = (
    # border and caption are required together ============
    ('border', '*', '=', 'set-border'),
    ('border-ok', 'uc', 'b'),
    ('border-ok', 'b', '='),
    ('border-ok', 'c', 'closed'),
    ('border-ok', 'open', '='),
    ('border-ok', 'closed', '='),

    # border and caption are required together ============
    ('caption', '*', '=', 'set-caption'),
    ('caption-ok', 'uc', 'c'),
    ('caption-ok', 'c', '='),
    ('caption-ok', 'b', 'closed'),
    ('caption-ok', 'open', '='),
    ('caption-ok', 'closed', '='),

    # === colors ==========================================
    ('caption-fg', '*', '=', 'set-caption-fg'),
    ('caption-bg', '*', '=', 'set-caption-bg'),
    ('text-fg', '*', '=', 'set-text-fg'),
    ('text-bg', '*', '=', 'set-text-bg'),

    # === choice ==========================================
    ('choice', 'closed', 'closed', ['open', 'choice']),

    # === close ===========================================
    ('close', '*', 'closed'),
    ('eof', '*', '=', 'quit'),

    # === open ============================================
    ('open', 'closed', 'open'),
    ('open', 'open', 'open'),
    ('open-ok', 'closed', 'open'),

    # === text ============================================
    ('text', 'closed', '=', ['open', 'queue-text']),
    ('text', 'open', '=', 'queue-text'),
    ('text-ok', '*', 'waiting'),

    # === input ===========================================
    ('press', 'waiting', 'open', 'resume'),
    ('press', 'open', '='),

    ('music', '*', '=', 'play_music'),
    ('sound', '*', '=', 'play_sound'),

    # === tree ============================================
    ('tree', 'closed', 'closed', ['open', 'tree']),
    ('tree', 'open', 'open', 'tree'),
    ('tree-ok', 'open', 'open'),
)


class ScriptRunner:
    raw_settings = [
        'set-caption-fg',
        'set-caption-bg',
        'set-text-fg',
        'set-text-bg']

    def __init__(self):
        self.target = None
        self.script = None
        self.tree = None
        self.vars = dict()
        self.sm = dict()
        self.operations = {
            'set': self.cmd_set,
            'dialog': self.cmd_dialog,
            'wait': self.cmd_wait,
        }

    def start(self, target, script):
        """
        :type target: Cutscene
        :type script: dict
        """
        self.tree = None
        self.target = target
        self.script = script['script']
        self.vars = {
            '_index': 0,
            '_state': None,
        }
        self.sm = {
            'dialog': SimpleFSM(dialog_events, 'uc')
        }

        trees = script.get('trees')
        if trees:
            for cfg in trees:
                self.program_tree(cfg)

        self.dialog_event('border', 'border-default.png')
        self.resume()

    def resume(self):
        index = self.vars['_index']
        # todo: index inc.
        if index == len(self.script):
            self.dialog_event('eof')
        for item in self.script[index:]:
            for cmd, kwargs in item.items():
                op = self.operations[cmd]
                op(kwargs)

            self.vars['_index'] += 1
            if self.sm['dialog'].state == 'waiting':
                break

    def cmd_set(self, kwargs):
        nope_or_not(kwargs, 'background', self.target.set_background)
        nope_or_not(kwargs, 'portrait', self.target.set_portrait)

    def cmd_dialog(self, kwargs):
        for name, args in kwargs.items():
            self.dialog_event(name, args)

    def cmd_wait(self, kwargs):
        pass

    def dialog_event(self, event, args=None):
        state, actions = self.sm['dialog'](event)
        if actions:
            for action in actions:
                if args:
                    self.handle_action(action, args)
                else:
                    self.handle_action(*action.split('::'))

    def handle_action(self, action, args=None):
        target = self.target

        if action == 'set-border':
            surface = load_image(args).convert_alpha()
            target._border = GraphicBox(surface, fill_tiles=True)
            self.dialog_event('border-ok')

        elif action == 'set-caption':
            target.set_caption(args)
            self.dialog_event('caption-ok')

        elif action == 'queue-text':
            target.queue_dialog_text(args)
            self.dialog_event('text-ok')

        elif action == 'tree':
            self.dialog_event(args + '-open')

        elif action == 'open':
            target.open_dialog()
            self.dialog_event('open-ok')

        elif action == 'add_choice':
            target.queue_dialog_text(args)
            self.dialog_event('add_choice')

        elif action == 'resume':
            self.resume()

        elif action == 'play_music':
            pygame.mixer.music.load(get_sound_asset(args))
            pygame.mixer.music.play(-2)

        elif action == 'play_sound':
            s = pygame.mixer.Sound(get_sound_asset(args))
            s.play()

        elif action == 'quit':
            self.target.running = False

        elif action in self.raw_settings:
            self.vars[action[4:]] = args

        else:
            raise ValueError(action, args)

    def program_tree(self, cfg):
        event_name = cfg['trigger']

        event_trigger = event_name + '-open'
        event_setup = event_name + '-setup'

        events = list()
        events.append((event_trigger, 'open', event_setup, 'add_choice::test'))

        for c in cfg['choices']:
            events.append(('add_choice', event_setup, '='))

        import pprint
        pprint.pprint(events)

        self.sm['dialog'].program(events)


class Cutscene(Minigame):
    GAME_NAME = "Cutscene"
    _default_layer = 1

    def __init__(self, scene_name="cutscene001", scene_file_name="test-cutscene.yaml"):
        self.running = False
        self.script_runner = ScriptRunner()
        self._scene_name = scene_name
        self._scene_file_name = scene_file_name
        self._border = None
        self._sprites = LayeredUpdates()
        self._animations = Group()
        self._dialog_open = False
        self._dialog_rect = None
        self._caption = None
        self._text = None

    def initialize(self, context):
        with open(get_data_asset(self._scene_file_name)) as fp:
            config = yaml.load(fp)
        self.script_runner.start(self, config[self._scene_name])

    @staticmethod
    def new_sprite(image, rect):
        sprite = Sprite()
        sprite.image = image
        sprite.rect = rect
        return sprite

    def animate(self, *args, **kwargs):
        ani = animation.Animation(*args, **kwargs)
        self._animations.add(ani)
        return ani

    def add_sprite(self, image, rect, layer=None):
        self._sprites.add(self.new_sprite(image, rect),
                          layer=ternone(layer, self._default_layer))

    def set_background(self, filename):
        surf = smoothscale(load_image(filename), SCREEN_SIZE).convert()
        rect = (0, 0), SCREEN_SIZE
        self.add_sprite(surf, rect, 0)

    def set_portrait(self, filename):
        size = 340, 680

        # HACK to remove old portrait
        for sprite in self._sprites:
            if sprite.image.get_size() == size:
                self._sprites.remove(sprite)

        if filename is not None:
            surf = smoothscale(load_image(filename), size).convert_alpha()
            rect = (900, 60), size
            self.add_sprite(surf, rect, 1)

    def set_caption(self, value):
        if value is None:
            self._caption = None
            return

        get = self.script_runner.vars.get
        fcolor = Color(get('caption-fg', 'black'))
        font = load_font('pixChicago.ttf', 16)
        if 'caption-bg' in self.script_runner.vars and get('caption-bg') is not None:
            bcolor = Color(get('caption-bg'))
            image = font.render(value, 0, fcolor, bcolor)
            margins = image.get_rect().inflate(45, 0)
            background = pygame.Surface(margins.size)
            background.fill(bcolor)
            background.blit(image, (24, 0))
            self._caption = background
        else:
            self._caption = font.render(value, 0, fcolor)

    def set_text(self, value):
        get = self.script_runner.vars.get
        fcolor = Color(get('text-fg', 'black'))
        bcolor = none_or_not(self.script_runner.vars, 'text-bg', Color)
        font = load_font('pixChicago.ttf', 16)
        w, h = self.final_rect().size
        w -= 48
        final_rect = Rect((0, 0), (w, h))
        self._text = pygame.Surface(final_rect.size, pygame.SRCALPHA)
        draw_text(self._text, value, final_rect, font, fcolor, bcolor)

    def final_rect(self):
        sw, sh = SCREEN_SIZE
        return Rect(sw * .05, sh * .6, sw * .62, sh * .35)

    def queue_dialog_text(self, value):
        self.set_text(value)

    def open_dialog(self):
        self._dialog_open = True
        final_rect = self.final_rect()
        self._dialog_rect = Rect(0, 0, 64, 64, center=final_rect.center)
        ani = self.animate(self._dialog_rect, height=final_rect.height, width=final_rect.width, duration=100)
        ani.schedule(lambda: setattr(self._dialog_rect, "center", final_rect.center), 'on update')

    def close_dialog(self):
        self._dialog_open = False

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
                flip()
                last_draw = 0

        pygame.mixer.music.fadeout(800)

    def draw(self, screen):
        self._sprites.draw(screen)

        if self._dialog_open:
            self.draw_dialog(screen)

    def draw_dialog(self, surface):
        with surface_clipping_context(surface, self._dialog_rect):
            self._border.draw(surface, self._dialog_rect)

        internal = self._dialog_rect.inflate(-48, -6)
        with surface_clipping_context(surface, internal):
            if self._caption:
                rect = self._caption.get_rect()
                rect.top = internal.top
                rect.centerx = internal.centerx
                surface.blit(self._caption, rect)

            if self._text:
                rect = internal.copy()
                rect.top = internal.top + 75
                rect.left = internal.left
                surface.blit(self._text, rect)

    def update(self, dt):
        self._animations.update(dt)

    def button_press(self):
        """ Handles the ACTION button

        :return:
        """
        self.script_runner.dialog_event('press')

    def handle_event(self):
        for event in pygame.event.get():
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    self.running = False
                if event.key == K_SPACE:
                    self.button_press()
            if event.type == QUIT:  # this will allow pressing the windows (X) to close the game
                sys.exit(0)
