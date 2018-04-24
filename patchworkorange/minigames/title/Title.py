import sys

import pygame
from pygame.transform import smoothscale

from patchworkorange import GAME_TITLE
from patchworkorange.core.minigamemanager import Minigame
from patchworkorange.core.resources import get_image_asset, get_font_asset, get_sound_asset


def load_image(filename):
    return pygame.image.load(get_image_asset(filename))


def load_font(name, size):
    return pygame.font.Font(get_font_asset(name), size)


class Title(Minigame):
    GAME_NAME = "Title"

    def initialize(self, context):
        pass

    def run(self, context):
        pygame.mixer.music.load(get_sound_asset("Crypto.mp3"))
        pygame.mixer.music.play(-2)
        surface = pygame.display.get_surface()
        font = load_font("Closeness-Bold-Italic.ttf", 90)
        text_surface = font.render(GAME_TITLE, 1, pygame.Color("orange"))
        bkg = load_image('title.jpg')
        bkg = smoothscale(bkg, surface.get_size())
        surface.blit(bkg, (0, 0))
        surface.blit(text_surface, (64, 400))
        pygame.display.flip()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sys.exit(0)
                elif event.type in {pygame.KEYUP, pygame.MOUSEBUTTONUP}:
                    pygame.mixer.music.fadeout(800)
                    return
