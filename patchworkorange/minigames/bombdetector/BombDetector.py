import sys

import collections

import animation
from pygame.sprite import Group
from patchworkorange.core import resources
from patchworkorange.core.minigamemanager import Minigame
from logging import getLogger
import pygame
import pytmx
import math

logger = getLogger(__name__)

WINDOW_SIZE = (1280, 720)
UPDATE_FREQUENCY = 300
FRAME_DELAY = 1000.0 / 60.0

GAME_DICT = {}

BEEPER = pygame.USEREVENT + 1


class BombDetector(Minigame):
    GAME_NAME = "BombDetector"

    def __init__(self):
        self.screen = None
        self.clock = None
        self.font = None
        self.player = None
        self.layers = None
        self.beep = None
        self.distance = None
        self.key_held = False
        self.visual = None
        self.visual_color = None
        self.jurassic = None
        self.animations = Group()

    def initialize(self, context):
        pygame.mixer.init()

        self.screen = pygame.display.set_mode(WINDOW_SIZE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 15, bold=True)
        self.beep = pygame.mixer.Sound(resources.get_sound_asset("beeps.wav"))
        pygame.mixer.music.load(resources.get_sound_asset("computer_loop.wav"))
        pygame.mixer.music.set_volume(0.01)

        pygame.time.set_timer(BEEPER, 2000)

        self.load_map()

        self.player = Player(GAME_DICT["Player"])
        self.visual = pygame.Surface(WINDOW_SIZE).convert_alpha()

        self.visual_color = pygame.Color("red")
        self.visual_color.a = 128

    def run(self, context):
        pygame.mixer.music.play(-1)

        game_loop = True
        delta_accumulator = 0.0
        while game_loop:
            delta = self.clock.tick(UPDATE_FREQUENCY)
            delta_accumulator += delta
            if delta_accumulator >= FRAME_DELAY:
                self.render()
                delta_accumulator = 0.0

            game_loop = self.update(delta)
            self.render()

            pygame.display.flip()

        if self.goal_met():
            logger.debug("YEAH! YOU WON!")
            context["{}.won".format(self.GAME_NAME)] = "true"
        else:
            context["{}.won".format(self.GAME_NAME)] = "false"

    def update(self, delta):
        if not self.handle_events(delta):
            return False
        self.distance = self.euclidean(self.player.rect.center, GAME_DICT["Terminal"].center)

        if self.key_held and (self.jurassic is None or self.jurassic.finished):
            self.player.update(pygame.key.get_pressed(), delta)

        if any(self.player.rect.colliderect(value) for key, value in GAME_DICT.items() if "Jurassic" in key) \
                and self.jurassic is None:
            self.jurassic = JurassicPark()
            pygame.time.set_timer(CLEVER_GIRL, 2000)

        if self.jurassic is not None and not self.jurassic.finished:
            self.jurassic.update(delta)

        self.update_visual()

        self.animations.update(delta)

        return True if not self.goal_met() else False

    def update_visual(self):
        red_ratio = self.distance / 1250
        red = int(red_ratio * 255)
        green = int((1-red_ratio) * 255)

        self.visual_color.r = red
        self.visual_color.g = green
        self.visual_color.a -= 1 if self.visual_color.a != 0 else 0

    @staticmethod
    def euclidean(a, b):
        return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)

    def render(self):
        self.render_layers()

        self.visual.fill(self.visual_color)
        self.screen.blit(self.visual, (0, 0))
        if self.jurassic is not None:
            self.jurassic.render(self.screen)

        self.player.render(self.screen)

        if self.jurassic is not None and self.jurassic.show_girl:
            if not self.jurassic.finished:
                self.screen.blit(self.jurassic.message, (10, 300))

    def handle_events(self, delta):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit(0)
            if event.type == pygame.KEYDOWN:
                if self.jurassic is None or self.jurassic.finished:
                    if event.key in [pygame.K_DOWN, pygame.K_UP, pygame.K_LEFT, pygame.K_RIGHT]:
                        self.player.update(pygame.key.get_pressed(), delta)
                    self.key_held = True
                else:
                    if event.key == pygame.K_SPACE:
                        print("yes")
                    if event.key == pygame.K_s:
                        return False
            if event.type == BEEPER:
                self.beep.set_volume(1-self.distance/1255)
                self.beep.play()
                self.visual_color.a = 128
            if event.type == pygame.KEYUP:
                if self.jurassic is None or self.jurassic.finished:
                    if 1 not in collections.Counter(pygame.key.get_pressed()):
                        self.key_held = False
            if event.type == CLEVER_GIRL:
                self.jurassic.show_girl = True
                pygame.time.set_timer(CLEVER_GIRL_2, 1000)
            if event.type == CLEVER_GIRL_2:
                self.jurassic.start_animation()
        return True

    def load_map(self):
        tmx = pytmx.util_pygame.load_pygame(resources.get_map_asset('maze.tmx'))
        self.layers = tmx.layers

        for i, o in enumerate(tmx.objects):
            GAME_DICT[o.name if o.name not in ["Jurassic", "Wall", "Stop"] else "{}_{}".format(o.name, i)] = pygame.Rect(
                o.x, o.y,
                o.width, o.height
            )

    def render_layers(self):
        for layer in self.layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                self.render_layer(layer)

    def render_layer(self, layer):
        w, h = BLOCK_SIZE
        for x, y, tile in layer.tiles():
            self.screen.blit(tile, (x * w, y * h))

    def goal_met(self):
        return GAME_DICT["Terminal"].colliderect(self.player.rect)


BLOCK_SIZE = (32, 32)
PLAYER_SIZE = (20, 20)


class Player(object):
    SPEED = 7.5 / 1000.0

    def __init__(self, rect):
        self.pos = (rect.left // PLAYER_SIZE[0], rect.top // PLAYER_SIZE[1])
        self.rect = rect
        self.torch = pygame.image.load(resources.get_image_asset("torch.png")).convert_alpha()
        self.font = pygame.font.SysFont("monospace", 15, bold=True)
        self.stop = self.font.render("I should not go to there considering what just happened!!", 1, pygame.Color("Red"))
        self.hit_stop = False

    def update(self, key, delta):
        self.move(key, delta)
        self.rect = self.update_bbox()

    def move(self, key, delta):
        if key[pygame.K_DOWN]:
            self.change_position((0, 1), delta)
        elif key[pygame.K_UP]:
            self.change_position((0, -1), delta)
        elif key[pygame.K_RIGHT]:
            self.change_position((1, 0), delta)
        elif key[pygame.K_LEFT]:
            self.change_position((-1, 0), delta)

    def update_bbox(self):
        return pygame.Rect(*self.pos_as_px(self.pos), *PLAYER_SIZE)

    def change_position(self, direction, delta):
        x, y = self.pos
        if direction[0] != 0:  # left/right
            new_x, new_y = x + (direction[0]*delta) * Player.SPEED, y

        else:
            new_x, new_y = x, y + (direction[1]*delta) * Player.SPEED

        new_pos = (new_x, new_y)
        if self.not_crossing_wall(new_pos) and self.not_colliding_stop(new_pos):
            self.pos = new_pos[0], new_pos[1]
            self.hit_stop = False
        if not self.not_colliding_stop(new_pos):
            self.hit_stop = True

    def render(self, screen):
        pygame.draw.rect(screen, pygame.Color("blue"), self.rect)

        rect = self.torch.get_rect()
        rect.center = self.rect.center
        screen.blit(self.torch, rect.topleft)

        if self.hit_stop:
            screen.blit(self.stop, (10, 300))

    def not_crossing_wall(self, new_position):
        player = pygame.Rect(*self.pos_as_px(new_position), *PLAYER_SIZE)
        return all(not player.colliderect(value) for key, value in GAME_DICT.items() if "Wall" in key)

    def not_colliding_stop(self, new_position):
        player = pygame.Rect(*self.pos_as_px(new_position), *PLAYER_SIZE)
        return all(not player.colliderect(value) for key, value in GAME_DICT.items() if "Stop" in key)

    def pos_as_px(self, position):
        px = [x * y for x, y in zip(position, PLAYER_SIZE)]
        return tuple(px)


CLEVER_GIRL = pygame.USEREVENT + 2
CLEVER_GIRL_2 = pygame.USEREVENT + 3


class JurassicPark(object):
    def __init__(self):
        self.font = pygame.font.SysFont("monospace", 15, bold=True)
        self.muldoon = GAME_DICT["Muldoon"]
        self.girl = GAME_DICT["Girl"]
        self.raptor = GAME_DICT["Raptor"]

        self.message = self.font.render("CLEVER GIRL!", 1, pygame.Color("Red"))
        self.show_girl = False
        self.animations = Group()
        self.finished = False

    def render(self, screen):
        pygame.draw.rect(screen, pygame.Color("yellow"), self.muldoon)
        pygame.draw.rect(screen, pygame.Color("red"), self.raptor)

        if self.show_girl:
            pygame.draw.rect(screen, pygame.Color("cyan"), self.girl)

    def update(self, delta):
        self.animations.update(delta)

    def start_animation(self):
        ani = self.animate(self.girl, top=self.muldoon.top-3, duration=50)
        ani.schedule(lambda: setattr(self, "finished", True), 'on finish')

    def animate(self, *args, **kwargs):
        ani = animation.Animation(*args, **kwargs)
        self.animations.add(ani)
        return ani
