import copy
import random
import sys
from logging import getLogger
import pygame
import pytmx
import os
import time
from pytmx.pytmx import TiledTileLayer

from patchworkorange.core.minigamemanager import Minigame
from patchworkorange.core import resources

logger = getLogger(__name__)

BLOCK_SIZE = (32, 32)
HINTS = []
GAME_DICT = {}


class Mastermind(Minigame):
    GAME_NAME = "Mastermind"

    def __init__(self, **kwargs):
        self.background = None
        self.screen = None
        self.clock = None
        self.font = None
        self.invalid_code = False
        self.game_won = False
        self.threat = 0

        self.entered_code = []
        self.correct_code = random.sample(range(9), 4)
        self.layers = []
        self.hint = ["RED" for _ in range(4)]

    def initialize(self, context):
        logger.debug("Mastermind initilaized")
        # logger.debug("Correct-Code is: {}".format(self.correct_code))

        pygame.mouse.set_visible(True)
        self.screen = pygame.display.get_surface()
        self.clock = pygame.time.Clock()
        pygame.display.set_caption("Mastermind")
        self.font = pygame.font.SysFont("monospace", 15, bold=True)

        self.setup_game()

    def run(self, context):
        game_loop = True
        while game_loop:
            game_loop = self.update()
            self.render(self.screen)

            pygame.display.flip()
            self.clock.tick(60)

        if self.goal_met():
            ic_sfc = pygame.image.load(resources.get_image_asset(
                os.path.join("mastermind", "access_granted.png")))
            WINDOW_SIZE = pygame.display.get_surface().get_rect().size
            self.screen.blit(ic_sfc, (WINDOW_SIZE[0]//2 - ic_sfc.get_width()//2,
                                      WINDOW_SIZE[1]//2 - ic_sfc.get_height()//2))

            pygame.display.flip()

            time.sleep(1)
            pygame.mouse.set_visible(False)
            pygame.display.set_mode((1280, 800))

            context["{}.won".format(self.GAME_NAME)] = "true"

        if self.threat >= 10:
            ic_sfc = pygame.image.load(resources.get_image_asset(
                os.path.join("mastermind", "danger_location_compromised.png")))
            self.screen.blit(ic_sfc, (WINDOW_SIZE[0]//2 - ic_sfc.get_width()//2,
                                      WINDOW_SIZE[1]//2 - ic_sfc.get_height()//2))
            context["{}.won".format(self.GAME_NAME)] = "false"

            pygame.display.flip()

            time.sleep(1)
            pygame.mouse.set_visible(False)

    def setup_game(self):
        self.check_for_correct_dimensions()
        self.load_map()

    def check_for_correct_dimensions(self):
        display_info = pygame.display.Info()

        #assert display_info.current_w % BLOCK_SIZE[0] == 0, "Window width not dividable by BLOCK_SIZE.x without rest"
        #assert display_info.current_h % BLOCK_SIZE[1] == 0, "Window height not dividable by BLOCK_SIZE.y without rest"

    def load_map(self):
        tmx = pytmx.util_pygame.load_pygame(resources.get_map_asset('mastermind.tmx'))
        self.layers = tmx.layers

        for o in tmx.objects:
            GAME_DICT[o.name] = pygame.Rect(
                o.x, o.y,
                o.width, o.height
            )

    def update(self):
        if not self.handle_events():
            return False
        if self.threat >= 10:
            return False
        return False if self.goal_met() else True

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit(0)
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.invalid_code:
                    self.invalid_code = False
                else:
                    self.process_numpad_keys(event)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_s:
                    HINTS.append((None, ["GREEN" for _ in range(4)]))
        return True

    def process_numpad_keys(self, event):
        for key in GAME_DICT.keys():
            if self.is_numpad_key_pressed(key, event.pos):
                if self.is_digit(key):
                    self.append_key_to_entered_code(key)
                else:
                    self.process_non_digits(key)

    @staticmethod
    def is_numpad_key_pressed(key, pos):
        return GAME_DICT[key].collidepoint(pos) and "NP_" in key

    @staticmethod
    def is_digit(key):
        return key not in ["NP_DISPLAY", "NP_ENTER", "NP_C"]

    def append_key_to_entered_code(self, key):
        if len(self.entered_code) < 4 and int(key[3:]) not in self.entered_code:
            self.entered_code.append(int(key[3:]))

    def process_non_digits(self, key):
        if key == "NP_C":
            self.entered_code.clear()
        elif key == "NP_ENTER":
            hint = []

            if len(self.entered_code) < 4:
                self.invalid_code = True
                return

            for i, digit in enumerate(self.entered_code):
                if digit in self.correct_code:
                    if self.entered_code.index(digit) == self.correct_code.index(digit):
                        hint.append("GREEN")
                    else:
                        hint.append("YELLOW")
                        self.threat += 1 if self.threat > 0 else 0
                else:
                    hint.append("RED")
                    self.threat += 1

            HINTS.append((copy.deepcopy(self.entered_code), hint))

            self.entered_code.clear()

    def render(self, screen):
        screen.fill(pygame.Color("BLACK"))

        self.render_layers(screen)
        self.render_display(screen)
        self.render_hints(screen)
        self.render_threat(screen)

        if self.invalid_code:
            ic_sfc = pygame.image.load(resources.get_image_asset(os.path.join("mastermind", "invalid_code.png")))
            screen.blit(ic_sfc, (WINDOW_SIZE[0]//2 - ic_sfc.get_width()//2, WINDOW_SIZE[1]//2 - ic_sfc.get_height()//2))

    def render_layers(self, screen):
        for layer in self.layers:
            if isinstance(layer, TiledTileLayer):
                self.render_layer(screen, layer)

    @staticmethod
    def render_layer(screen, layer):
        w, h = BLOCK_SIZE
        for x, y, tile in layer.tiles():
            screen.blit(tile, (x * w, y * h))

    def render_display(self, screen):
        for i, digit in enumerate(self.entered_code):
            label = self.font.render(str(digit), 1, pygame.Color("BLACK"))

            # center of np display, moving pos of next digit to be half a tile further right
            draw_pos = tuple([x + y for x, y in zip(GAME_DICT["NP_DISPLAY"].bottomleft, (
                (i * BLOCK_SIZE[0] // 2) + BLOCK_SIZE[0] // 2, -0.75 * BLOCK_SIZE[0]))])

            screen.blit(label, draw_pos)

    @staticmethod
    def goal_met():
        return len(HINTS) > 0 and all(hint == "GREEN" for hint in HINTS[-1][1])

    def render_hints(self, screen):
        self.render_hint_lines(screen)
        self.render_hint_lamps(screen)

    def render_hint_lines(self, screen):
        for i, hint in enumerate(HINTS):
            label = self.font.render(str(hint[0]), 1, (0, 255, 0))

            draw_pos = tuple([x + y for x, y in zip(GAME_DICT["LINE_{}".format(i+1)].bottomleft, (
                (BLOCK_SIZE[0] // 2) + BLOCK_SIZE[0] // 2, -0.75 * BLOCK_SIZE[0]))])
            screen.blit(label, draw_pos)

    @staticmethod
    def render_hint_lamps(screen):
        for i, hint in enumerate(HINTS):
            for j, lamp in enumerate(hint[1]):
                draw_pos = tuple([x + y for x, y in zip(GAME_DICT["HINT_{}".format(i+1)].bottomleft, (
                    (j*BLOCK_SIZE[0] // 2) + BLOCK_SIZE[0], int(-0.5 * BLOCK_SIZE[0])))])
                pygame.draw.circle(screen, pygame.Color(lamp), draw_pos, 10)

    def render_threat(self, screen):
        for i in range(self.threat):
            if i >= 10:
                break
            t = GAME_DICT["Threat_{}".format(i+1)]
            if i < 4:
                color = "green"
            elif i < 8:
                color = "yellow"
            else:
                color = "red"
            pygame.draw.rect(screen, pygame.Color(color), t)



