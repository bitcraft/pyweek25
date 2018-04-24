import sys

import collections
import copy
import random

import pygame
from logging import getLogger
import pytmx
from math import sqrt

from pygame.rect import Rect

from patchworkorange.core.minigamemanager import Minigame
from patchworkorange.core import resources

from time import sleep

WINDOW_SIZE = (1280, 720)

logger = getLogger(__name__)


class FirewallBreaker(Minigame):
    GAME_NAME = "FirewallBreaker"
    UPDATE_FREQUENCY = 300  # Update positioning 300 times per second
    FRAME_DELAY = 1000.0 / 60.0   # Milliseconds between updates

    def __init__(self, map_name="breakout-1.tmx", **kwargs):
        self.clock = None
        self.screen = None
        self.player = None
        self.ball = None
        self.start_ball = False
        self.key_held = False
        self.check_for_player_collision = True
        self.bricks = []
        self.font = None
        self.powerup = None
        self.message = None
        self.background = None
        self.map_name = map_name

    def run(self, context):
        pygame.mixer.music.play(-1)

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

        if self.ball.lives == 0:
            logger.debug("OH NO! YOU LOST!")
            context["{}.won".format(self.GAME_NAME)] = "false"

        if self.goal_met():
            pygame.mixer.music.stop()
            context["{}.won".format(self.GAME_NAME)] = "true"
            logger.debug("YEAH! YOU WON!")

    def initialize(self, context):
        pygame.mouse.set_visible(False)
        self.screen = pygame.display.set_mode(WINDOW_SIZE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 15, bold=True)
        pygame.display.set_caption("Breakout")
        pygame.time.set_timer(pygame.USEREVENT + 4, 10000)
        pygame.mixer.init()

        background = pygame.transform.scale(pygame.image.load(resources.get_image_asset("terminal.png")), WINDOW_SIZE)
        self.background = background.convert()

        pygame.mixer.music.load(resources.get_sound_asset("dance_electro.mp3"))
        pygame.mixer.music.set_volume(0.2)

        self.setup_game()

    def update(self, delta):
        if not self.handle_events(delta):
            return False

        self.check_collision()
        self.player.update()
        self.ball.update(delta, self.player)
        if self.powerup is not None:
            if self.powerup.pos[1] < WINDOW_SIZE[1]:
                self.powerup.update(delta)
            else:
                self.powerup = None
        return False if self.goal_met() else True

    def render(self):
        self.screen.blit(self.background, (0, 0))
        self.render_bricks()
        self.player.render(self.screen)
        self.ball.render(self.screen)
        if self.powerup is not None:
            self.powerup.render(self.screen)

        if self.player.has_powerup:
            label = self.font.render(self.message, 1, pygame.Color("GREEN"))
            self.screen.blit(label, (10, 5))

    def handle_events(self, delta):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit(0)
            if event.type == pygame.MOUSEMOTION:
                self.player.pos = (event.pos[0] - self.player.rect.width / 2, self.player.pos[1])
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if self.ball.lives > 0:
                        if self.ball.move_ball:
                            if self.player.has_powerup:
                                self.message = "ATTACKING PORT 80 !!!"
                                self.ball.move_ball = False
                                pygame.time.set_timer(pygame.USEREVENT + 2, 300)
                                pygame.time.set_timer(pygame.USEREVENT + 3, 3000)
                                sound = pygame.mixer.Sound(resources.get_sound_asset("freshquark.wav"))
                                sound.play()
                        self.ball.move_ball = True
                    else:
                        return False
                if event.key == pygame.K_s:
                    self.bricks = []

                self.key_held = True
            if event.type == pygame.KEYUP:
                if 1 not in collections.Counter(pygame.key.get_pressed()):
                    self.key_held = False
            if event.type == pygame.USEREVENT+1:
                self.check_for_player_collision = True
            if event.type == pygame.USEREVENT+2:
                item = random.choice(self.bricks)
                self.bricks.remove(item)
            if event.type == pygame.USEREVENT+3:
                self.player.has_powerup = False
                self.ball.move_ball = True
                pygame.time.set_timer(pygame.USEREVENT + 2, 0)
                pygame.time.set_timer(pygame.USEREVENT + 3, 0)
            if event.type == pygame.USEREVENT+4:
                # self.ball.SPEED += 50.0 / 1000.0
                pass

        if self.key_held:
            self.player.move(pygame.key.get_pressed(), delta)

        return True

    def goal_met(self):
        return len(self.bricks) == 0

    def setup_game(self):
        self.player = Player()
        self.ball = Ball()
        self.load_map()

    def check_collision(self):
        if self.player.rect.colliderect(self.ball.bbox) and self.check_for_player_collision:
            self.check_for_player_collision = False
            pygame.time.set_timer(pygame.USEREVENT + 1, 250)

            dist = self.ball.bbox.center[0] - self.player.rect.center[0]
            ratio = max(dist/(self.player.rect.width//2), -0.75) if dist > 0 else min(dist/(self.player.rect.width//2), 0.75)

            new_x = ratio

            self.ball.direction = new_x, -1
            logger.debug(self.ball.direction)

            sound = pygame.mixer.Sound(resources.get_sound_asset("shield.wav"))
            sound.play()

        for brick in self.bricks[:]:
            if self.ball.bbox.colliderect(brick):
                assert self.ball.bbox != self.ball.old_bbox

                """
                 (1, 1)    = 
                 (1, -1)   =
                 (-1, 1)   =
                 (-1, -1)  =
                
                
                """
                dx, dy = self.ball.direction
                if dx == 0 and dy != 0:  # up/down (0, 1)
                    if dy > 0:
                        # hit top brick
                        dx *= -1
                    else:
                        # hit bottom
                        dy *= -1

                elif dx != 0 and dy == 0:  # left/right (1, 0)
                    assert not True

                elif dx > 0 and dy > 0:  # down/right (1, 1)
                    # top or left
                    if self.ball.old_bbox.bottom > brick.top:
                        # hit left
                        dx *= -1
                    else:
                        # hit top
                        dy *= -1

                elif dx < 0 and dy > 0:  # down/left (-1, 1)
                    # top or right
                    if self.ball.old_bbox.bottom > brick.top:
                        # hit right
                        dx *= -1
                    else:
                        # hit top
                        dy *= -1

                elif dx < 0 and dy < 0:  # up/left (-1, -1)
                    # bottom and right
                    if self.ball.old_bbox.top < brick.bottom:
                        # hit right
                        dx *= -1
                    else:
                        # hit bottom
                        dy *= -1

                elif dx > 0 and dy < 0:  # up/right (1, -1)
                    # bottom and left
                    if self.ball.old_bbox.top < brick.bottom:
                        # hit left
                        dx *= -1
                    else:
                        # hit bottom
                        dy *= -1

                self.ball.direction = dx, dy
                self.ball.bbox = self.ball.old_bbox

                for b in self.bricks[:]:
                    assert not b.colliderect(self.ball.bbox)

                self.bricks.remove(brick)

                sound = pygame.mixer.Sound(resources.get_sound_asset("open_hat.wav"))
                sound.play()

                if random.random() < 0.80 and not self.player.has_powerup and self.powerup is None:
                    self.powerup = PowerUp(brick.topleft)
                break

        if self.powerup is not None and self.player.rect.colliderect(self.powerup.bbox):
            self.powerup = None
            self.player.has_powerup = True

            self.message = "Port 80 exposed! Start SQL Injection"
            logger.debug("PowerUp Collected!")

    def load_map(self):
        tmx = pytmx.util_pygame.load_pygame(resources.get_map_asset(self.map_name))

        for o in tmx.objects:
            self.bricks.append(
                pygame.Rect(o.x, o.y, o.width, o.height)
            )

    def render_bricks(self):
        self.screen.lock()
        for i, brick in enumerate(self.bricks):
            color = "red" if i % 2 == 0 else "maroon"
            pygame.draw.rect(self.screen, pygame.Color(color), brick, 1)
        self.screen.unlock()


class Player(object):
    SIZE = (100, 20)
    SPEED = 800.0 / 1000.0  # pixels per second

    def __init__(self):
        self.pos = (WINDOW_SIZE[0]//2 - self.SIZE[0]//2, WINDOW_SIZE[1]-50)
        self.rect = pygame.Rect(self.pos, Player.SIZE)
        self.has_powerup = False

    def render(self, screen):
        pygame.draw.rect(screen, pygame.Color("red"), self.rect)

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


class Ball(object):
    SIZE = (15, 15)
    RESET_POS = (WINDOW_SIZE[0]//2 - SIZE[0]//2, WINDOW_SIZE[1]-70)
    SPEED = 400.0 / 1000.0  # pixels per second
    DEFAULT_DIR = (1.0, -1.0)

    def __init__(self):
        self.pos = Ball.RESET_POS
        self.bbox = pygame.Rect(self.pos, Ball.SIZE)
        self.direction = Ball.DEFAULT_DIR
        self.move_ball = False
        self.lives = 4
        self.font = pygame.font.SysFont("monospace", 15, bold=True)
        self.old_bbox = None

    def render(self, screen):
        pygame.draw.rect(screen, pygame.Color("cyan"), self.bbox)

        if self.lives == 3 and not self.move_ball:
            self.show_live_lost_message(screen, "Man this firewall is really tough to break!")
        if self.lives == 2 and not self.move_ball:
            self.show_live_lost_message(screen, "I should be more careful! I don't want to get caught!")
        if self.lives == 1 and not self.move_ball:
            self.show_live_lost_message(screen, "Damn! I think the monitoring system is getting aware of me.")
        if self.lives == 0 and not self.move_ball:
            self.show_live_lost_message(screen, "That's enough! I need to stop, I think they found me!")

    def show_live_lost_message(self, screen, msg):
        label = self.font.render(msg, 1, pygame.Color("red"))
        screen.blit(label, (10, 300))

    def update(self, delta, player):
        if not self.move_ball:
            self.pos = player.rect.center[0]-self.bbox.width//2, player.rect.top - self.bbox.height-5
        else:
            self.move(delta)
        self.bbox = pygame.Rect(self.pos, Ball.SIZE)

        if self.pos[1] == WINDOW_SIZE[1]:
            self.pos = Ball.RESET_POS
            self.move_ball = False
            self.lives -= 1
            self.direction = Ball.DEFAULT_DIR
            self.SPEED = 400.0 / 1000.0

    def move(self, delta):
        x, y = self.pos
        dx, dy = self.direction
        if y <= 0:
            dy *= -1
        elif x <= 0 or x + self.bbox.width >= WINDOW_SIZE[0]-1:
            dx *= -1
        new_x, new_y = x + dx * self.SPEED * delta, y + dy * self.SPEED * delta
        self.old_bbox = self.bbox
        self.pos = (max(0.0, min(new_x, WINDOW_SIZE[0]-1)), max(0.0, min(new_y, WINDOW_SIZE[1])))
        self.direction = (dx, dy)


class PowerUp(object):
    SIZE = (15, 15)
    SPEED = 100.0 / 1000.0  # pixels per second

    def __init__(self, pos):
        self.pos = pos
        self.bbox = pygame.Rect(self.pos, Ball.SIZE)
        self.direction = (0.0, 1.0)  # pixels per second

    def render(self, screen):
        pygame.draw.rect(screen, pygame.Color("green"), self.bbox)

    def update(self, delta):
        self.bbox = pygame.Rect(self.pos, Ball.SIZE)
        self.move(delta)

    def move(self, delta):
        x, y = self.pos
        dx, dy = self.direction
        if y <= 0:
            dy *= -1
        elif x <= 0 or x + self.bbox.width >= WINDOW_SIZE[0]:
            dx *= -1
        new_x, new_y = x + dx * self.SPEED * delta, y + dy * self.SPEED * delta
        self.pos = (max(0.0, min(new_x, WINDOW_SIZE[0])), max(0.0, min(new_y, WINDOW_SIZE[1])))
        self.direction = (dx, dy)
