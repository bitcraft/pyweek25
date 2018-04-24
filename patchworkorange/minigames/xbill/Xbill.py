import sys
from functools import partial
from patchworkorange.core.minigamemanager import Minigame
from logging import getLogger
import pygame
import random
from pygame import USEREVENT as TIMER_ID
from pygame.sprite import Group, Sprite
from patchworkorange.core import resources
import os

from animation import Animation

logger = getLogger(__name__)

WINDOW_SIZE = (1280, 720)


class Xbill(Minigame):
    GAME_NAME = "Xbill"

    UPDATE_FREQUENCY = 300
    FRAME_DELAY = 1000.0 / 60.0

    GAME_DURATION = 60*1000

    BILL_SPAWN_INTERVAL = 2 * 1000

    def __init__(self, **kwargs):
        self.background = None
        self.screen = None
        self.clock = None
        self.font = None
        self.terminals = []
        self.bills = []
        self.floating_texts = []
        self.countdown = 0

    def initialize(self, context):
        self.screen = pygame.display.set_mode(WINDOW_SIZE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 15, bold=True)

        self.countdown = Xbill.GAME_DURATION

        self.terminals.append(Terminal(640, 360))
        self.terminals.append(Terminal(740, 160))
        self.terminals.append(Terminal(840, 260))
        self.terminals.append(Terminal(540, 260))
        self.terminals.append(Terminal(440, 320))
        self.terminals.append(Terminal(340, 420))
        self.terminals.append(Terminal(790, 320))
        self.terminals.append(Terminal(256, 128))
        self.terminals.append(Terminal(1060, 425))
        self.terminals.append(Terminal(900, 550))

        pygame.display.set_caption(Xbill.GAME_NAME)
        pygame.mouse.set_visible(True)

        pygame.time.set_timer(TIMER_ID+1, Xbill.BILL_SPAWN_INTERVAL)

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

        if self.countdown <= 0:
            context["{}.won".format(self.GAME_NAME)] = "true"
            pygame.mouse.set_visible(False)

        # TODO: Wat to do here?
        """ 
        if self.get_free_terminal() is not None:
            context["{}.won".format(self.GAME_NAME)] = "false"
        """

    def update(self, delta):
        if not self.handle_events(delta):
            return False

        for terminal in self.terminals:
            terminal.update(delta)

        for floating_text in self.floating_texts[:]:
            if not floating_text.update(delta):
                self.floating_texts.remove(floating_text)

        for bill in self.bills[:]:
            bill.update(delta)
            if bill.destroy:
                self.bills.remove(bill)

        self.countdown -= delta
        if self.countdown <= 0:
            logger.debug("you win")
            pygame.mouse.set_visible(False)
            return False

        return True

    def render(self):
        self.screen.fill(pygame.Color("BLACK"))

        for terminal in self.terminals:
            terminal.render(self.screen)

        for bill in self.bills:
            bill.render(self.screen)

        for floating_text in self.floating_texts:
            floating_text.render(self.screen)

        self.render_time(self.screen)

    def render_time(self, screen):
        label = self.font.render("Countdown: "+str(self.countdown/1000), 1, pygame.Color("green"))
        screen.blit(label,  (640-24,16))

    def handle_events(self, delta):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit(0)
            if event.type == pygame.MOUSEBUTTONDOWN:
                return self.handle_mouse_click(event)
            if event.type == TIMER_ID+1: # create bill and send towards terminal
                self.bills.append(self.send_bill())
                free_terminal = self.get_free_terminal()
                if free_terminal is None:
                    logger.debug("you lose")
                    return False
                self.bills[-1].goto_terminal(free_terminal)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_s:
                    self.countdown = 0

        return True

    def handle_mouse_click(self, event):
        for terminal in self.terminals:
            if terminal.rect.collidepoint(event.pos):
                if terminal.block_duration == 0 and not terminal.infected:
                    terminal.prevent_patch()
                    x, y = terminal.pos
                    self.floating_texts.append(FloatingText(x-16, y-16, "Blocked!", self.font))
        return True

    def get_free_terminal(self):
        free_terminals = [terminal for terminal in self.terminals if not terminal.infected]
        if len(free_terminals) > 0:
            return random.choice(free_terminals)
        else:
            return None

    def send_bill(self):
        area = random.randint(1, 4)
        width = 16
        x, y = (0, 0)
        if area == 1: # LEFT
            x, y = (16, random.randint(width, 720-width*3))
        if area == 2: # RIGHT
            x, y = (1280-width*3, random.randint(width, 720-width*3))
        if area == 3: # TOP
            x, y = (random.randint(width, 1280-width*3), width)
        if area == 4: # BOTTOM
            x, y = (random.randint(width, 1280-width*3), 720-width*3)
        return Bill(x, y)

class Terminal(Sprite):
    SIZE = (32, 32)

    def __init__(self, x, y):
        super(Terminal, self).__init__()
        self.image = pygame.image.load(resources.get_image_asset(os.path.join("xbill", "terminal.png"))).convert()
        self.pos = (x, y)
        self.rect = pygame.Rect(self.pos, Terminal.SIZE)
        self.block_duration = 0.0
        self.patch_progress = 0.0
        self.infected = False
        self.neighors = []

    def render(self, screen):
        screen.blit(self.image, self.rect)

    def update(self, delta):
        self.rect.topleft = self.pos
        self.block_duration = max(0, self.block_duration-delta)

    def prevent_patch(self):
        self.block_duration = 2 * 1000

class Bill(Sprite):
    SIZE = (32, 50)
    def __init__(self, x, y):
        super(Bill, self).__init__()
        self.image = pygame.image.load(resources.get_image_asset(os.path.join("xbill", "bill.png"))).convert()
        self.pos = (x, y)
        self.animations = Group()
        self.rect = pygame.Rect(self.pos, Bill.SIZE)
        self.destroy = False
        self.image.set_colorkey((255, 0, 255))

    def render(self, screen):
        screen.blit(self.image, self.rect)

    def update(self, delta):
        self.animations.update(delta)

    def goto_terminal(self, terminal):
        x, y = terminal.pos
        x_anim = Animation(self.rect, centerx=x, duration=4000)
        y_anim = Animation(self.rect, centery=y, duration=4000)
        self.animations.add(x_anim)
        self.animations.add(y_anim)
        x_anim.schedule(partial(self.on_arrived_at_terminal, terminal), "on finish")

    def on_arrived_at_terminal(self, terminal):
        if terminal.block_duration == 0:
            terminal.infected = True
            terminal.image = pygame.image.load(resources.get_image_asset(os.path.join("xbill", "terminal_infected.png"))).convert()
        self.destroy = True

class FloatingText(object):
    def __init__(self, x, y, label, font):
        self.pos = (x, y)
        self.label = font.render(label, 1, pygame.Color("white"))
        self.life_time = 2 * 1000

    def render(self, screen):
        screen.blit(self.label, self.pos)

    def update(self, delta):
        self.life_time -= delta
        x, y = self.pos
        self.pos = (x, y-0.04)
        if self.life_time <= 0:
            return False
        return True
