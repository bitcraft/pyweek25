import random
import sys
from functools import partial
from logging import getLogger
from math import atan2, pi

import pygame
import pyscroll
from animation import Task, Animation
from pygame.rect import Rect
from pygame.sprite import Sprite, Group, spritecollide, LayeredUpdates
from pygame.transform import scale
from pytmx import load_pygame

from patchworkorange.core import resources
from patchworkorange.core.adventuregraph import InvalidEdgeException
from patchworkorange.core.adventuregraph import load_yaml_data, Visitor, build_graph_from_yaml_data
from patchworkorange.core.clippie import Clippie
from patchworkorange.core.minigamemanager import Minigame, ExitGameAction
from patchworkorange.core.resources import get_data_asset
from patchworkorange.core.supersprite import RelativeGroup
from patchworkorange.core.ui import GraphicBox, PyscrollGroup, draw_text
from patchworkorange.minigames.graphview.behaviors import RunMinigameActivation

logger = getLogger(__name__)
COLOR_KEY = (255, 0, 255)


class GraphView(Minigame):
    GAME_NAME = "GraphView"

    def __init__(self, graph_yaml=None, graph_tmx=None):
        self.visitor = None
        self.scroll_group = None
        self.graph_yaml = graph_yaml
        self.graph_tmx = graph_tmx
        self.visitor_cursor = None
        self.vertex_group = VertexLookupGroup()
        self.hud_group = None
        self.hud_button = None
        self.pointer = None
        self.sprites = LayeredUpdates()
        self._animations = Group()

    def animate(self, *args, **kwargs):
        ani = Animation(*args, **kwargs)
        self._animations.add(ani)
        return ani

    def initialize(self, context):

        screen = pygame.display.get_surface()
        adventure_graph = build_graph_from_yaml_data(load_yaml_data(get_data_asset(self.graph_yaml)))
        self.visitor = Visitor.visit_graph(adventure_graph, context)

        tmx_data = load_pygame(resources.get_map_asset(self.graph_tmx))
        map_data = pyscroll.TiledMapData(tmx_data)
        map_layer_size = screen.get_width(), int(screen.get_height() * .80)
        map_layer_rect = Rect((0, 0), map_layer_size)
        map_layer = pyscroll.BufferedRenderer(map_data, map_layer_size)

        self.scroll_group = PyscrollGroup(map_layer=map_layer)

        self.pointer = PointerSprite(self.vertex_group, self.scroll_group)
        # self.pointer.selected_vertex_id = "START"
        self.sprites.add(self.pointer, layer=100)

        sw, sh = screen.get_size()
        hud_rect = Rect(20, sh * .76, sw * .80, sh * .2)
        border_image = load_image('border-default.png').convert_alpha()
        self.hud_group = HUDGroup(hud_rect, border_image)
        info = VertexInfoSprite(self.visitor)
        info.rect = Rect(12, 12, hud_rect.width - 250, hud_rect.height - 24)
        self.hud_group.add(info)
        self.hud_group.open()

        self.hud_button = HUDButton(self.hud_group, 850, 70)
        self.hud_group.add(self.hud_button)

        edges = list()
        for vertex in self.visitor.graph.vertex_index.values():
            vertex_sprite = VertexSprite(vertex)
            self.vertex_group.add(vertex_sprite)
            self.scroll_group.add(vertex_sprite)
            for edge in vertex.edges:
                edges.append(edge)

        edge_sprites = dict()
        for edge in edges:
            key = [edge.from_vertex.vertex_id, edge.to_vertex.vertex_id]
            key.sort()
            key = tuple(key)
            if key not in edge_sprites:
                edge_sprite = EdgeSprite(edge, self.scroll_group)
                from_vertex_sprite = self.vertex_group[edge.from_vertex.vertex_id]
                to_vertex_sprite = self.vertex_group[edge.to_vertex.vertex_id]
                from_vertex_sprite.edge_sprites.append(edge_sprite)
                to_vertex_sprite.edge_sprites.append(edge_sprite)
                edge_sprites[key] = edge_sprite

        self.visitor_cursor = VisitorCursor(self.visitor, self.pointer, self.vertex_group, self.scroll_group)

        if context.get('show_clippie', False):
            c = Clippie(self.sprites, self._animations, context)
            c.rect.topleft = 1100, 550
            self.sprites.add(c)
            self.visitor_cursor.clippie = c

        clock = pygame.time.Clock()

        pygame.display.flip()
        pygame.mouse.set_visible(False)

        while True:
            delta = clock.tick(60)
            events = pygame.event.get()
            self.hud_group.update(delta, events)
            for event in events:
                if event.type == pygame.QUIT:
                    sys.exit(0)
                elif event.type == pygame.KEYDOWN or self.hud_button.handle_click:
                    vertex_id = self.visitor_cursor.current_vertex_sprite.vertex_id
                    if self.hud_button.handle_click or pygame.K_SPACE == event.key and vertex_id == self.pointer.selected_vertex_id:
                        self.hud_button.handle_click = False
                        if self.visitor.current_vertex.can_activate(self.visitor.context):
                            activation_dict = self.visitor.activate_current_vertex()
                            if activation_dict["command"] == "launch-mini-game":
                                r = RunMinigameActivation(activation_dict["command"],
                                                          activation_dict["activation-keyword-args"])

                                logger.debug("Stating game: {} with arguments {}".format(r.mini_game_name,
                                                                                         r.mini_game_keyword_args))
                                unhandled_actions = self.minigame_manager.run_minigame(r.mini_game_name,
                                                                                       self.visitor.context,
                                                                                       r.post_run_actions,
                                                                                       **r.mini_game_keyword_args if r.mini_game_keyword_args is not None else {})

                                if self.has_exit_action(unhandled_actions):
                                    return

                        else:
                            vertex = self.visitor.current_vertex
                            failing = vertex.activation_pre_requisites.get_failing_pre_requisites(self.visitor.context)
                            self.visitor.context['gamestate.dialog_text'] = failing[0].hint
                            self.visitor_cursor.animations.add(Task(self.visitor_cursor.clear_hint, 5000))

            self.scroll_group.update(delta, events)
            # self.hud_group.update(delta, events)
            self.sprites.update(delta, events)
            self._animations.update(delta)
            self._update_edge_colors()

            x_offset = ((self.visitor_cursor.rect.x - self.scroll_group.view.x) - self.pointer.rect.x) / 2
            self.scroll_group.center((self.visitor_cursor.rect.x - x_offset, 0))

            self.scroll_group.draw(screen, map_layer_rect)

            screen.fill((200, 200, 200), (0, sh * .75, 1280, 200))

            self.hud_group.draw(screen)
            self.sprites.draw(screen)

            screen.blit(self.pointer.image, self.pointer.rect)
            pygame.display.flip()

    def has_exit_action(self, unhandle_actions):
        for u in unhandle_actions:
            if u.ACTION_NAME == ExitGameAction.ACTION_NAME:
                return True
        return False

    def run(self, context):
        pass

    def _update_edge_colors(self):
        for key, vertex_sprite in self.vertex_group.lookup.items():
            for e in vertex_sprite.edge_sprites:
                if e.edge.can_traverse(self.visitor.context):
                    e.color = pygame.Color("GREEN")


def load_image(filename):
    return pygame.image.load(resources.get_image_asset(filename))


class VisitorCursor(Sprite):
    PURPLE = (255, 0, 255)
    _layer = 3
    image = pygame.image.load(resources.get_image_asset("visitor.png"))

    def __init__(self, visitor, pointer, vertex_sprite_group, *groups):
        super(VisitorCursor, self).__init__(*groups)
        self.vertex_sprite_group = vertex_sprite_group
        self.visitor = visitor
        self.pointer = pointer
        self.current_vertex_sprite = vertex_sprite_group[self.visitor.current_vertex.vertex_id]
        self.rect = Rect((0, 0), self.image.get_rect().size)
        self.rect.center = self.visitor.current_vertex.coordinates
        self.animations = Group()
        self.moving = False
        self.image = self.image.convert()
        self.image.set_colorkey(COLOR_KEY)

    def clear_hint(self):
        try:
            del self.visitor.context['gamestate.dialog_text']
        except KeyError:
            pass

    def update(self, delta, events):
        self.animations.update(delta)
        if self.pointer.selected_vertex_id is None or self.moving:
            return

        try:
            edge = self.visitor.current_vertex.get_edge_by_to_vertex_id(self.pointer.selected_vertex_id)
            if edge.can_traverse(self.visitor.context):
                self.goto_destination(self.pointer.selected_vertex_id)
                self.pointer.selected_vertex_id = None
            else:
                failing = edge.traversal_pre_requisites.get_failing_pre_requisites(self.visitor.context)
                for f in failing:
                    fail_msg = "Pre-Requisite not met: (Key: {}, Value: {}, Hint: {})".format(f.key, f.value, f.hint)
                    logger.debug(fail_msg)

                    if self.visitor.context['show_clippie']:
                        self.clippie.queue_text("I see that you are trying to go there.")
                        self.clippie.queue_text("Do you want some help?", 2000)
                        self.clippie.queue_text("Its just not possible to go there now.", 2000)
                        self.clippie.queue_text("Are you sure you know what you are doing?")

                    self.visitor.context['gamestate.dialog_text'] = f.hint
                    self.animations.add(Task(self.clear_hint, 5000))
                    self.pointer.selected_vertex_id = None  # to avoid spam in logger

                    break  # just show the first hint

        except InvalidEdgeException:
            return

    def goto_destination(self, destination_vertex_id):
        x, y = self.visitor.graph.vertex_index[destination_vertex_id].coordinates
        # x_anim = Animation(self.rect, centerx=x, duration=1000, transition="in_quad")
        # y_anim = Animation(self.rect, centery=y, duration=1000, transition="out_quad")
        x_anim = Animation(self.rect, centerx=x, duration=1000, transition="in_out_quint")
        y_anim = Animation(self.rect, centery=y, duration=1000, transition="in_out_quint")
        self.animations.add(x_anim)
        self.animations.add(y_anim)
        x_anim.schedule(partial(self.on_arrived_at_new_destination, destination_vertex_id), "on finish")

    def on_arrived_at_new_destination(self, destination_vertex_id):
        logger.debug("Arrived at %s" % destination_vertex_id)
        self.moving = False
        self.visitor.go_to_vertex(destination_vertex_id)
        self.current_vertex_sprite = self.vertex_sprite_group[destination_vertex_id]

        if self.visitor.context['show_clippie']:
            msg = random.choice([
                'Are you sure you want to go there?',
                'Is that really where you need to be?',
                'Do you want any help?',
                'We shouldn\'t be wasting any time.',
                'I see that you have changed positions.'
            ])
            self.clippie.push_text(msg)

class VertexSprite(Sprite):
    _layer = 2

    def __init__(self, vertex, *groups):
        super(VertexSprite, self).__init__(*groups)
        self.vertex = vertex
        self.vertex_id = vertex.vertex_id

        # really shouldn't do stuff like this in __init__, but oh well
        image = pygame.image.load(resources.get_image_asset(vertex.icon))
        w, h = image.get_size()
        image = scale(image, (w * 2, h * 2))
        self.image = image.convert()
        self.image.set_colorkey(COLOR_KEY)
        self.image.set_alpha(255)

        self.edge_sprites = list()
        self.rect = Rect((0, 0), self.image.get_rect().size)
        self.rect.center = vertex.coordinates


class EdgeSprite(Sprite):
    _layer = 1
    GREEN = (0, 255, 0)
    RED = (255, 0, 0)
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3

    def __init__(self, edge, *groups):
        super(EdgeSprite, self).__init__(*groups)
        self.edge = edge
        self.image = None
        self.rect = None
        self.color = self.RED

    def update(self, delta, events):
        # if self.image is None:
        self.render_image()

    def render_image(self):
        """Because we need the path lines to scroll around on the scroll layer and always at the right depth, we can't
        just draw them to the screen. Instead, we create a sprite per distinct edge and try to line up the rect of
        the sprite so that two of its corners are at the center of the two nodes connected by the edge. Then we draw
        a line through the rect between the two connecting corners. This is harder to do correctly than it sounds...
        """
        line_width = 3
        x1, y1, x2, y2 = self.get_coordinates()

        w, h = (max(abs(x2 - x1), line_width), max(abs(y2 - y1), line_width))
        size = (w, h)

        self.rect = Rect((0, 0), size)
        self.image = pygame.Surface(size, pygame.SRCALPHA).convert()
        self.image.set_colorkey(COLOR_KEY)
        self.image.fill(COLOR_KEY)

        # Remember, Y axis is inverted
        angle = (atan2(y2 - y1, x2 - x1) * 180.0) / pi
        # Normalize the angle to 0-360
        angle = (angle + 360) % 360

        if h == line_width or w == line_width:
            self.image.fill(self.color)

        if 0 <= angle < 90:  # down and to the right, Quadrant IV
            self.rect.topleft = x1, y1
            pygame.draw.line(self.image, self.color, (0, 0), size, line_width)
        elif 90 <= angle < 180:  # down and to the left, Quadrant III
            self.rect.topright = x1, y1
            pygame.draw.line(self.image, self.color, (w, 0), (0, h), line_width)
        elif 180 <= angle < 270:  # up and to the left, Quadrant II
            self.rect.bottomright = x1, y1
            pygame.draw.line(self.image, self.color, (0, 0), size, line_width)
        elif 270 <= angle < 360:  # up and to the right, Quadrant I
            self.rect.bottomleft = x1, y1
            pygame.draw.line(self.image, self.color, (0, h), (w, 0), line_width)

    def get_coordinates(self):
        x1, y1 = self.edge.from_vertex.coordinates
        x2, y2 = self.edge.to_vertex.coordinates
        return x1, y1, x2, y2


class PointerSprite(Sprite):
    _layer = 999
    image = pygame.image.load(resources.get_image_asset("pointer.png"))
    SPEED = 100  # pixels per second
    MAX_SPEED = 500
    ACCELERATION = .1
    MOVE = {  # pixels per second X, pixels per second Y
        pygame.K_LEFT: (-SPEED, 0),
        pygame.K_RIGHT: (SPEED, 0),
        pygame.K_UP: (0, -SPEED),
        pygame.K_DOWN: (0, SPEED)
    }

    def __init__(self, vertex_group, scroll_group, *groups):
        super(PointerSprite, self).__init__(*groups)
        self.rect = Rect((0, 0), self.image.get_rect().size)
        self.movement = (0.0, 0.0)
        self.selected_vertex_id = None
        self.vertex_group = vertex_group

        self.image = self.image.convert()
        self.image.set_colorkey(COLOR_KEY)

        # The scroll_group is needed because the pointer exists in screen space, not world space. We have to translate
        # the screen location of the hotspot to its relative position in world space.
        self.scroll_group = scroll_group

    def update(self, delta, events):
        self.process_events(events)
        self.rect.move_ip(*self.calculate_movement(delta))
        self.clamp_topleft()

    def clamp_topleft(self):
        w, h = pygame.display.get_surface().get_rect().size
        x, y = self.rect.topleft
        x = min(max(0, x), w)
        y = min(max(0, y), h)
        self.rect.topleft = (x, y)

    def process_events(self, events):
        for event in events:
            if pygame.MOUSEMOTION == event.type:
                self.movement = (0.0, 0.0)
                self.rect.topleft = event.pos
            elif pygame.MOUSEBUTTONUP == event.type:
                self.check_vertex_collision()
            elif pygame.KEYDOWN == event.type:
                if pygame.K_SPACE == event.key:
                    self.check_vertex_collision()
                else:
                    x, y = self.movement
                    dx, dy = self.MOVE.get(event.key, (0.0, 0.0))
                    self.movement = (x + dx, y + dy)
            elif pygame.KEYUP == event.type:
                if pygame.K_LEFT == event.key or pygame.K_RIGHT == event.key:
                    self.movement = (0.0, self.movement[1])
                elif pygame.K_UP == event.key or pygame.K_DOWN == event.key:
                    self.movement = (self.movement[0], 0.0)

    def check_vertex_collision(self):
        vertices = spritecollide(self, self.vertex_group, False, self.collide_hotspot)
        if vertices:
            self.selected_vertex_id = vertices[0].vertex.vertex_id
            logger.debug("Selected vertex %s" % self.selected_vertex_id)

    @staticmethod
    def collide_hotspot(pointer, vertex_sprite):
        view_x, view_y = pointer.scroll_group.view.topleft
        pointer_x, pointer_y = pointer.rect.topleft
        hotspot = (view_x + pointer_x, view_y + pointer_y)
        return vertex_sprite.rect.collidepoint(hotspot)

    def calculate_movement(self, delta):
        amount = delta / 1000.0
        dx, dy = self.movement

        if dx != 0 or dy != 0:
            dx += dx * self.ACCELERATION
            dy += dy * self.ACCELERATION
            if abs(dx) > self.MAX_SPEED:
                dx = -self.MAX_SPEED if dx < 0 else self.MAX_SPEED
            if abs(dy) > self.MAX_SPEED:
                dy = -self.MAX_SPEED if dy < 0 else self.MAX_SPEED
            self.movement = (dx, dy)

        return amount * dx, amount * dy


class VertexLookupGroup(Group):

    def __init__(self, *sprites):
        self.lookup = {}
        super(VertexLookupGroup, self).__init__(*sprites)

    def add(self, *sprites):
        self.assert_are_vertex_sprites(*sprites)
        self.lookup.update({s.vertex_id: s for s in sprites})
        super(VertexLookupGroup, self).add(*sprites)

    def __getitem__(self, vertex_id):
        return self.lookup[vertex_id]

    @staticmethod
    def assert_are_vertex_sprites(*sprites):
        if len(sprites) > 0:
            assert (all(isinstance(sprite, VertexSprite) for sprite in sprites))


class HUDGroup(RelativeGroup):
    def __init__(self, rect, border_image, **kwargs):
        super(HUDGroup, self).__init__(rect)
        self._border_rect = None  # type: pygame.Rect
        self._border = GraphicBox(border_image, fill_tiles=True)

    def open(self):
        self._border_rect = Rect(0, 0, 64, 64, center=self.rect.center)
        ani = self.animate(self._border_rect,
                           height=self.rect.height,
                           width=self.rect.width,
                           duration=300,
                           transition='out_quint')
        ani.schedule(lambda: setattr(self._border_rect, "center", self.rect.center), 'on update')

    def draw(self, surface):
        self._border.draw(surface, self._border_rect)
        super(HUDGroup, self).draw(surface)


class HUDSprite(Sprite):
    _layer = 0

    def __init__(self):
        super(HUDSprite, self).__init__()
        self.image = pygame.image.load(resources.get_image_asset("hud.png")).convert()
        self.image.set_colorkey(COLOR_KEY)
        self.rect = self.image.get_rect()


class HUDButton(Sprite):
    _layer = 2

    def __init__(self, hud_group, x, y):
        super(HUDButton, self).__init__()
        self.image = pygame.image.load(resources.get_image_asset("button.png")).convert()
        self.image.set_colorkey(COLOR_KEY)
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
        self.label = None
        self.text = "Enter"
        self.hud_group = hud_group
        self.handle_click = False

    def update(self, delta, events):
        self.process_events(events)
        self.render_text()

    def process_events(self, events):
        for event in events:
            if pygame.MOUSEBUTTONUP == event.type:
                x, y = event.pos
                dx, dy = self.hud_group.rect.topleft
                if self.rect.collidepoint((x - dx, y - dy)):
                    self.handle_click = True
                    logger.debug("button clicked!")

    def render_text(self):
        font = pygame.font.SysFont("monospace", 24, bold=True)
        self.label = font.render(self.text, 1, pygame.Color("black"))
        text_center = 72 - 6.5 * len(self.text)  # not precise
        rect = Rect(text_center, 10, 0, 0)
        self.image.blit(self.label, rect)


class VertexInfoSprite(Sprite):
    _layer = 1
    FONT_COLOR = (64, 64, 64)

    def __init__(self, visitor):
        super(VertexInfoSprite, self).__init__()
        self.rect = Rect(0, 0, 0, 0)
        self.image = None
        self.visitor = visitor
        self.vertex_info_string = None
        self.font = pygame.font.SysFont("Courier", 24, True)

    def update(self, delta, events):
        info_string = self.get_current_info_string()
        if self.vertex_info_string != info_string:
            self.vertex_info_string = info_string
            self.render_image()

    def get_current_info_string(self):
        try:
            return self.visitor.context['gamestate.dialog_text']
        except KeyError:
            # default info, in case of errors only
            vertex = self.visitor.current_vertex
            args = (vertex.name, vertex.description)
            return "%s - %s" % args

    def render_image(self):
        text = self.vertex_info_string
        text_rect = pygame.Rect((0, 0), self.rect.size)

        self.image = pygame.Surface(text_rect.size)
        self.image.fill(COLOR_KEY)

        draw_text(self.image, text, text_rect, self.font, self.FONT_COLOR, COLOR_KEY)

        self.image.set_colorkey(COLOR_KEY)
