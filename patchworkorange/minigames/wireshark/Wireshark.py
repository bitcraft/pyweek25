import sys

import collections

from logging import getLogger
from patchworkorange.core.minigamemanager import Minigame
from pygame import USEREVENT as TIMER_ID
from pygame.sprite import Sprite
from patchworkorange.core import resources
import random
import pygame
import time
import os

logger = getLogger(__name__)
WINDOW_SIZE = (640, 480)
NEXT_ATTACKER = 1

class Wireshark(Minigame):
    GAME_NAME = "Wireshark"
    UPDATE_FREQUENCY = 300
    FRAME_DELAY = 1000.0 / 60.0
    MAX_ATTACKERS = 6
    PACKET_SPAWN_INTERVAL = 600
    ATTACKER_SPAWN_INTERVAL = 1800
    MAX_LEAKS = 50
    ATTACKS_STARTED = False
    SECRET = "ALLYOURBASEAREBELONGTOUS"
    MAX_SCORE = len(SECRET)

    def __init__(self, **kwargs):
        self.screen = None
        self.player = None
        self.clock = None
        self.key_held = False
        self.attackers = []
        self.remaining_attacker_positions = []
        self.packets = []
        self.key = ""
        self.key_map = []
        self.score = 0
        self.leaks = 0
        self.leak_bar = None
        self.font = None

    def initialize(self, context):
        logger.debug("Wireshark started")
        self.screen = pygame.display.set_mode(WINDOW_SIZE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 15, bold=True)

        self.key = ""
        self.key_map = random.sample(range(len(Wireshark.SECRET)), len(Wireshark.SECRET))
        self.remaining_attacker_positions = [x * 32 for x in range(WINDOW_SIZE[0] // 32)]
        self.player = Player()
        self.leak_bar = LeakBar(20, 5)

        pygame.display.set_caption(Wireshark.GAME_NAME)
        pygame.time.set_timer(TIMER_ID+1, Wireshark.ATTACKER_SPAWN_INTERVAL)
        pygame.time.set_timer(TIMER_ID+3, 50)
        pygame.mouse.set_visible(False)

    def run(self, context):
        game_loop = True
        delta_accumulater = 0.0
        while game_loop:
            delta = self.clock.tick(self.UPDATE_FREQUENCY)
            delta_accumulater += delta
            if delta_accumulater >= self.FRAME_DELAY:
                self.render()
                delta_accumulater = 0.0
            game_loop = self.update(delta)
            pygame.display.flip()

        if self.win_condition():
            context["{}.won".format(self.GAME_NAME)] = "true"
            pygame.display.set_mode((1280, 800))

        if self.leaks > Wireshark.MAX_LEAKS:
            context["{}.won".format(self.GAME_NAME)] = "false"

        pygame.display.flip()

    def update(self, delta):
        if not self.handle_events(delta):
            return False

        self.player.update()

        for attacker in self.attackers:
            attacker.update()

        for packet in self.packets[:]:
            packet.update()
            if self.player.rect.colliderect(packet.rect):
                self.packets.remove(packet)
                self.score += 1
            if packet.pos[1] > 480:
                self.packets.remove(packet)
                self.leaks += 1
                self.score = max(0, self.score-1)

        if self.lose_condition():
            return False

        return False if self.win_condition() else True

    def render(self):
        self.screen.fill(pygame.Color("BLACK"))

        self.player.render(self.screen)

        for attacker in self.attackers:
            attacker.render(self.screen)

        for packet in self.packets:
            packet.render(self.screen)

        self.render_key()
        self.leak_bar.render(self.screen, self.leaks)

    def handle_events(self, delta):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit(0)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_s:
                    self.score = len(Wireshark.SECRET)
                self.key_held = True
            if event.type == pygame.KEYUP:
                if 1 not in collections.Counter(pygame.key.get_pressed()):
                    self.key_held = False
            if event.type == TIMER_ID+1:
                if len(self.attackers) < Wireshark.MAX_ATTACKERS:
                    self.spawn_attacker()
            if event.type == TIMER_ID+2:
                random_attacker = random.randint(0, len(self.attackers)-1)
                self.packets.append(self.attackers[random_attacker].sendPacket())
            if event.type == TIMER_ID+3:
                self.key = random.sample(Wireshark.SECRET, len(Wireshark.SECRET))
                decrypted_key = self.key
                for i in range(self.score):
                    decrypted_key[self.key_map[i]] = Wireshark.SECRET[self.key_map[i]]
                self.key = ''.join(decrypted_key)

        if self.key_held:
            self.player.move(pygame.key.get_pressed(), delta)

        for packet in self.packets:
            packet.move(delta)

        return True

    def win_condition(self):
        if self.score == len(Wireshark.SECRET):
            return True
        return False

    def lose_condition(self):
        if self.leaks > Wireshark.MAX_LEAKS:
            return True
        return False

    def spawn_attacker(self):
        slot = random.randint(0, len(self.remaining_attacker_positions) - 1)
        x = self.remaining_attacker_positions[slot]
        self.remaining_attacker_positions.pop(slot)
        self.attackers.append(Attacker(x, 50))
        if not Wireshark.ATTACKS_STARTED:
            pygame.time.set_timer(TIMER_ID+2, Wireshark.PACKET_SPAWN_INTERVAL)
            Wireshark.ATTACKS_STARTED = True

        if len(self.remaining_attacker_positions) == 0:
            pygame.time.set_timer(TIMER_ID+1, 0)

    def render_key(self):
        label = self.font.render("Key:"+self.key, 1, pygame.Color("GREEN"))
        self.screen.blit(label, (200, 10))

class Player(object):
    SIZE = (25, 50)
    SPEED = 400.0 / 1000.0  # pixels per second

    def __init__(self):
        self.pos = (320.0, 400.0)
        self.rect = pygame.Rect(self.pos, Player.SIZE)

    def render(self, screen):
        pygame.draw.rect(screen, pygame.Color("blue"), self.rect)

    def update(self):
        self.rect.topleft = self.pos

    def move(self, key, delta):
        if key[pygame.K_RIGHT]:
            x, y = self.pos
            new_x = max(0, min(WINDOW_SIZE[0]-self.rect.width, (x + delta * self.SPEED)))
            self.pos = (new_x, y)
        if key[pygame.K_LEFT]:
            x, y = self.pos
            new_x = max(0, min(WINDOW_SIZE[0], (x - delta * self.SPEED)))
            self.pos = (new_x, y)

class Attacker(Sprite):
    SIZE = (32, 32)

    def __init__(self, x, y):
        super(Attacker, self).__init__()
        self.image = pygame.image.load(resources.get_image_asset(os.path.join("wireshark", "cloud.png"))).convert()
        self.pos = (x, y)
        self.rect = pygame.Rect(self.pos, Attacker.SIZE)
        self.image.set_colorkey((255, 0, 255))

    def render(self, screen):
        screen.blit(self.image, self.rect)

    def update(self):
        self.rect.topleft = self.pos

    def sendPacket(self):
        x, y = self.pos
        return Packet(x+8, y+Packet.SIZE[1])

class Packet(Sprite):
    SIZE = (16, 16)
    SPEED = .2

    def __init__(self, x, y):
        super(Sprite, self).__init__()
        self.image = pygame.image.load(resources.get_image_asset(os.path.join("wireshark", "bits.png"))).convert()
        self.image.set_colorkey((255, 0, 255))
        self.pos = (x, y)
        self.rect = pygame.Rect(self.pos, Packet.SIZE)

    def render(self, screen):
        screen.blit(self.image, self.rect)

    def update(self):
        self.rect.topleft = self.pos

    def move(self, delta):
        x, y = self.pos
        new_y = y + delta * self.SPEED
        self.pos = (x, new_y)

class LeakBar(object):
    SIZE = (100, 35)

    def __init__(self, x, y):
        self.pos = (x, y)
        self.rect = pygame.Rect(self.pos, LeakBar.SIZE)

    def render(self, screen, leaks):
        leaks *= 2
        if leaks > 0:
            color = "green"
            if leaks > 30:
                color = "yellow"
            if leaks >= 75:
                color = "red"
            pygame.draw.rect(screen, pygame.Color(color), pygame.Rect(self.pos, (leaks, 35)))
        pygame.draw.rect(screen, pygame.Color("white"), self.rect, 2)
