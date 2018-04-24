import sys
from logging import getLogger

import pygame
import pytmx.util_pygame
from pytmx.pytmx import TiledTileLayer

from patchworkorange.core import resources
from patchworkorange.core.minigamemanager import Minigame

BLOCK_SIZE = (32, 32)
WALLS = []
BOXES = []
GOALS = []
PLAYER = []

logger = getLogger(__name__)


class Sokoban(Minigame):
    GAME_NAME = "Sokoban"

    def __init__(self, **kwargs):
        self.background = None
        self.player = None
        self.screen = None
        self.clock = None

        self.level = kwargs["level"]

        self.layers = []

    def initialize(self, context):
        del BOXES[:]

        size = (640, 480)
        self.screen = pygame.display.set_mode(size)
        self.clock = pygame.time.Clock()
        pygame.display.set_caption("Sokoban")

        self.setup_game()

    def run(self, context):
        game_loop = True
        while game_loop:
            game_loop = self.update()
            self.render(self.screen)

            pygame.display.flip()
            self.clock.tick(60)

        if self.goal_met():
            print("YEAH! YOU WON!")
            pygame.display.set_mode((1280, 800))
            context["Sokoban.won"] = "true"

    def setup_game(self):
        self.check_for_correct_dimensions()
        self.load_map()

    @staticmethod
    def check_for_correct_dimensions():
        display_info = pygame.display.Info()

        assert display_info.current_w % BLOCK_SIZE[0] == 0, "Window width not dividable by BLOCK_SIZE.x without rest"
        assert display_info.current_h % BLOCK_SIZE[1] == 0, "Window height not dividable by BLOCK_SIZE.y without rest"

    def load_map(self):
        tmx = pytmx.util_pygame.load_pygame(resources.get_map_asset('sokoban_map{}.tmx'.format(self.level)))
        self.layers = tmx.layers

        self.build_static_props(tmx, WALLS, "Wall")
        self.build_static_props(tmx, GOALS, "Goal")

        self.build_boxes(tmx)
        self.spawn_player(tmx)

    @staticmethod
    def build_static_props(tmx, array, name):
        for o in tmx.objects:
            if o.name == name:
                array.append(
                    pygame.Rect(
                        o.x, o.y,
                        o.width, o.height
                    )
                )

    @staticmethod
    def build_boxes(tmx):
        for o in tmx.objects:
            if o.name == "Box":
                BOXES.append(
                    Box((o.x // BLOCK_SIZE[0], o.y // BLOCK_SIZE[1]))
                )

    def spawn_player(self, tmx):
        for o in tmx.objects:
            if o.name == "Player":
                position = (o.x // BLOCK_SIZE[0], o.y // BLOCK_SIZE[1])
                self.player = Player(position)

    def update(self):
        if not self.handle_events():
            return False
        return False if self.goal_met() else True

    def reset_game(self):
        del BOXES[:]
        self.setup_game()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit(0)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                elif event.key != pygame.K_F12:
                    self.player.update(event.key)
                else:
                    self.reset_game()
        return True

    @staticmethod
    def goal_met():
        return all(any(box.intersects(goal) for goal in GOALS) for box in BOXES)

    def render(self, screen):
        screen.fill((0, 0, 0))

        self.render_layers(screen)
        self.player.render(screen)
        self.render_boxes(screen)

    def render_layers(self, screen):
        for layer in self.layers:
            if isinstance(layer, TiledTileLayer):
                self.render_layer(screen, layer)

    @staticmethod
    def render_layer(screen, layer):
        w, h = BLOCK_SIZE
        for x, y, tile in layer.tiles():
            screen.blit(tile, (x * w, y * h))

    @staticmethod
    def render_boxes(screen):
        for box in BOXES:
            pygame.draw.rect(screen, box.color, box.bbox)


class Box(object):
    def __init__(self, position):
        self.size = BLOCK_SIZE
        self.position = position
        self.bbox = self.update_bbox()
        self.color = (0, 0, 255)

    @staticmethod
    def render():  # TODO: Is this even being called anywhere?
        pygame.draw.rect()

    def update_bbox(self):
        return pygame.Rect(*self.pos_as_px(self.position), *self.size)

    def move(self, direction):
        self.position = tuple([x + y for x, y in zip(self.position, direction)])
        self.bbox = self.update_bbox()

    def can_move_there(self, direction):
        new_position = tuple([x + y for x, y in zip(self.position, direction)])
        return self.not_crossing_wall(new_position) and self.does_not_hit_other_box(new_position)

    def does_not_hit_other_box(self, new_position):
        new_bbox = pygame.Rect(*self.pos_as_px(new_position), *BLOCK_SIZE)
        return all(not new_bbox.colliderect(box.bbox) for box in BOXES if box != self)

    def pos_as_px(self, position):
        px = [x * y for x, y in zip(position, self.size)]
        return tuple(px)

    def not_crossing_wall(self, new_position):
        bbox = pygame.Rect(*self.pos_as_px(new_position), *BLOCK_SIZE)
        return all(not bbox.colliderect(wall) for wall in WALLS)

    def intersects(self, rect):
        return self.bbox.colliderect(rect)


class Player(object):
    def __init__(self, position):
        self.size = BLOCK_SIZE
        self.position = position
        self.bbox = self.update_bbox()
        self.color = (255, 0, 0)

    def update(self, key):
        self.move(key)

    def move(self, key):
        if key == pygame.K_DOWN:
            self.change_position((0, 1))
        elif key == pygame.K_UP:
            self.change_position((0, -1))
        elif key == pygame.K_RIGHT:
            self.change_position((1, 0))
        elif key == pygame.K_LEFT:
            self.change_position((-1, 0))

    def update_bbox(self):
        return pygame.Rect(*self.pos_as_px(self.position), *self.size)

    def change_position(self, direction):
        new_position = tuple([x + y for x, y in zip(self.position, direction)])
        if self.not_crossing_window_border(new_position) and self.not_crossing_wall(new_position):
            hitted_box = self.hits_box(new_position)
            if hitted_box:
                if not hitted_box.can_move_there(direction):
                    return
                hitted_box.move(direction)
            self.position = new_position
            self.bbox = self.update_bbox()

    def hits_box(self, position):
        new_bbox = pygame.Rect(*self.pos_as_px(position), *BLOCK_SIZE)
        for box in BOXES:
            if new_bbox.colliderect(box.bbox):
                return box
        return None

    def not_crossing_window_border(self, new_position):
        return self.top_left_border_not_hit(new_position) and self.bottom_right_border_not_hit(new_position)

    def not_crossing_wall(self, new_position):
        player = pygame.Rect(*self.pos_as_px(new_position), *BLOCK_SIZE)
        return all(not player.colliderect(wall) for wall in WALLS)

    @staticmethod
    def top_left_border_not_hit(new_position):
        return all(p >= 0 for p in new_position)

    def bottom_right_border_not_hit(self, new_position):
        return all(True if x < y else False for x, y in zip(new_position, self.left_down_border()))

    @staticmethod
    def left_down_border():
        display_info = pygame.display.Info()
        return display_info.current_w / BLOCK_SIZE[0], display_info.current_h / BLOCK_SIZE[1]

    def pos_as_px(self, position):
        px = [x * y for x, y in zip(position, self.size)]
        return tuple(px)

    def render(self, screen):
        pygame.draw.rect(screen, self.color, self.bbox)
