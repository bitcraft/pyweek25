import os
import random
import sys
from logging import getLogger

import collections
import pygame
import pytmx
from pygame import USEREVENT as FIRIN_MA_LAZ0R
from pytmx.pytmx import TiledTileLayer

from patchworkorange.core import resources
from patchworkorange.core.minigamemanager import Minigame

logger = getLogger(__name__)

BLOCK_SIZE = (32, 32)
FREE_SERVERS = list(range(9))
GAME_DICT = {}

FIX_ME = ["INACTIVE" for _ in range(9)]

WINDOW_SIZE = (1280, 720)
FIRIN_MA_LAZ0R -= 10
WIN_SCORE = 20


class FixAServer(Minigame):
    GAME_NAME = "FixAServer"
    UPDATE_FREQUENCY = 300
    FRAME_DELAY = 1000.0 / 60.0

    def __init__(self, **kwargs):
        self.win_score = WIN_SCORE if "WIN_SCORE" not in kwargs else kwargs["WIN_SCORE"]
        self.screen = None
        self.clock = None
        self.font = None
        self.time = 25 * 1000
        self.missed = 0
        self.score = 0
        self.areas = [("Research", (250, 450)), ("Human Resources", (900, 100)), ("Server-Farm", (100, 50)),
                      ("System Admins", (800, 400))]
        self.labels = []
        self.background = pygame.image.load(resources.get_image_asset("terminal.png"))
        pc = pygame.image.load(resources.get_image_asset("server.png"))
        w, h = pc.get_size()
        self.pc = pygame.transform.scale(pc, (w * 2, h * 2)).convert()
        self.pc.set_colorkey((255, 0, 255))

        self.tried_fixing = 0

    def initialize(self, context):
        logger.debug("FixAServer initialized")
        pygame.mixer.init()
        pygame.mixer.music.load(resources.get_sound_asset("405603__frankum__newtime-electronic-music-track.mp3"))
        pygame.mixer.music.play()

        pygame.mouse.set_visible(True)
        self.screen = pygame.display.set_mode(WINDOW_SIZE)
        self.screen.set_colorkey((255, 0, 255))
        self.clock = pygame.time.Clock()
        pygame.display.set_caption(self.GAME_NAME)
        pygame.time.set_timer(FIRIN_MA_LAZ0R + 1, 1200)
        self.font = pygame.font.SysFont("monospace", 15, bold=True)

        for area, pos in self.areas:
            self.labels.append(self.font.render(area, 1, pygame.Color("green")))

        self.setup_game()

    def run(self, context):
        game_loop = True
        delta_accumulater = 0.0
        while game_loop:
            delta = self.clock.tick(self.UPDATE_FREQUENCY)
            game_loop = self.update(delta)
            delta_accumulater += delta
            if delta_accumulater >= self.FRAME_DELAY:
                self.render()
                delta_accumulater = 0.0

            pygame.display.flip()

        if self.goal_met():
            context["{}.won".format(self.GAME_NAME)] = "true"
            logger.debug("YEAH! YOU WIN!")

        if self.score >= 20:
            context["{}.won".format(self.GAME_NAME)] = "true"

        if self.missed > 6:
            logger.debug("Oh no! You LOST!")
            context["{}.won".format(self.GAME_NAME)] = "false"

        pygame.mouse.set_visible(False)

    def fix_server(self, i):
        pygame.time.set_timer(FIRIN_MA_LAZ0R + 2 + i, 0)
        if FIX_ME[i] == "ACTIVE" and self.score < 20:
            FIX_ME[i] = "INACTIVE"
            FREE_SERVERS.append(i)
            self.missed += 1

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit(0)
            if event.type == pygame.MOUSEBUTTONDOWN:
                return self.handle_mouse_click(event)
            if event.type == FIRIN_MA_LAZ0R + 1:
                if collections.Counter(FIX_ME)["INACTIVE"] > 7:
                    r = random.choice(FREE_SERVERS)
                    # if self.score == 20:
                    #    pygame.time.set_timer(FIRIN_MA_LAZ0R+1, 0)
                    #    r = random.choice([7, 8, 9])
                    FREE_SERVERS.remove(r)
                    pygame.time.set_timer(FIRIN_MA_LAZ0R + 2 + r, 1000)
                    FIX_ME[r] = "ACTIVE"
            if event.type == FIRIN_MA_LAZ0R + 2 + 0:
                self.fix_server(0)
            if event.type == FIRIN_MA_LAZ0R + 2 + 1:
                self.fix_server(1)
            if event.type == FIRIN_MA_LAZ0R + 2 + 2:
                self.fix_server(2)
            if event.type == FIRIN_MA_LAZ0R + 2 + 3:
                self.fix_server(3)
            if event.type == FIRIN_MA_LAZ0R + 2 + 4:
                self.fix_server(4)
            if event.type == FIRIN_MA_LAZ0R + 2 + 5:
                self.fix_server(5)
            if event.type == FIRIN_MA_LAZ0R + 2 + 6:
                self.fix_server(6)
            if event.type == FIRIN_MA_LAZ0R + 2 + 7:
                self.fix_server(7)
            if event.type == FIRIN_MA_LAZ0R + 2 + 8:
                self.fix_server(8)

        return True

    def update(self, delta):
        if not self.handle_events():
            return False
        self.time -= delta

        if self.missed >= 6:
            return False

        return False if self.goal_met() else True

    def render(self):
        # self.screen.fill(pygame.Color("black"))
        self.screen.blit(self.background, (0, 0))

        self.render_layers()
        self.render_pcs()
        self.render_fix_me_messages()
        self.render_score()
        self.render_areas()

    def goal_met(self):
        return self.time <= 0

    def setup_game(self):
        self.load_map()

    def load_map(self):
        tmx = pytmx.util_pygame.load_pygame(resources.get_map_asset('fix-a-server.tmx'))
        self.layers = tmx.layers

        for o in tmx.objects:
            GAME_DICT[o.name] = pygame.Rect(
                o.x, o.y,
                o.width, o.height
            )

    def render_layers(self):
        for layer in self.layers:
            if isinstance(layer, TiledTileLayer):
                self.render_layer(layer)

    def render_layer(self, layer):
        w, h = BLOCK_SIZE
        for x, y, tile in layer.tiles():
            # tile = tile.convert()
            tile.set_colorkey((255, 0, 255))
            self.screen.blit(tile, (x * w, y * h))

    def handle_mouse_click(self, event):
        for key, value in GAME_DICT.items():
            if value.collidepoint(event.pos):
                pygame.time.set_timer(FIRIN_MA_LAZ0R + 2 + int(key[-1]), 0)
                FIX_ME[int(key[-1])] = "INACTIVE"
                self.score += 1
                FREE_SERVERS.append(int(key[-1]))
        return True

    def render_fix_me_messages(self):
        for i, server in enumerate(FIX_ME):
            if server == "ACTIVE":
                server_pos = GAME_DICT["Server_{}".format(i)]
                fixme_surface = pygame.image.load(resources.get_image_asset(os.path.join("fixaserver", "fixme.png")))
                pos = tuple([x - y for x, y in zip(server_pos.center, (
                    fixme_surface.get_rect().width // 2, fixme_surface.get_rect().height // 2))])
                self.screen.blit(fixme_surface, pos)

    def render_score(self):
        label = self.font.render("Missed: {}/6".format(str(self.missed)), 1, pygame.Color("RED"))
        self.screen.blit(label, (10, 450))
        label = self.font.render("Time: {}".format(str(self.time / 1000.0)), 1, pygame.Color("GREEN"))
        self.screen.blit(label, (500, 10))

    def render_areas(self):
        for i, (_, pos) in enumerate(self.areas):
            self.screen.blit(self.labels[i], pos)

    def render_pcs(self):
        for key, value in GAME_DICT.items():
            if key is not None and "Server" in key:
                self.screen.blit(self.pc, value.topleft)
