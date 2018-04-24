from functools import partial

import pygame
from animation import Animation, Task, remove_animations_of

from patchworkorange.core.resources import get_image_asset, get_font_asset
from patchworkorange.core.supersprite import SuperSprite
from patchworkorange.core.ui import GraphicBox, draw_text


def load_image(filename):
    return pygame.image.load(get_image_asset(filename))


def load_font(name, size):
    return pygame.font.Font(get_font_asset(name), size)


class Clippie(SuperSprite):
    fg_color = 0, 0, 0
    bg_color = 255, 255, 255
    margins = 25, 55
    max_size = 900, 150

    def __init__(self, draw_group, animations, context):
        super(Clippie, self).__init__()
        image = load_image('border-clippie.png')
        self.border = GraphicBox(image, fill_tiles=True)
        self.callout = load_image('callout-clippie.png')
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.image = load_image('clippie1.png')
        self.context = context

        self._draw_group = draw_group

        self._message_queue = list()
        self._animations = animations
        self._animation_dict = dict()
        self._font = load_font('IHATCS__.TTF', 24)

    # HACK: hardcoding is bad
    def update(self, *args):
        super(Clippie, self).update(*args)

        if self.context['clippie_queue']:
            for i in self.context['clippie_queue']:
                self.queue_text(i)
        self.context['clippie_queue'] = list()

    @property
    def current_message(self):
        """Sprite that is currently being displayed"""
        try:
            return self._message_queue[0][1]
        except IndexError:
            return None

    @property
    def queued_text(self):
        """List of all text strings that are in the queue"""
        return [i[0] for i in self._message_queue]

    def queue_text(self, text, dismiss_after=5000, sound=None):
        """Queue some text to be displayed
        A unique sprite will be returned from this function.  That sprite
        can be passed to Advisor.dismiss() to remove that specific sprite.
        :param text: Text to be displayed
        :param sound: Sound to be played when message is shown
        :param dismiss_after: Number of milliseconds to show message,
                            Negative numbers will cause message to be displayed
                            until dismissed.
        :return: pygame.sprite.Sprite
        """
        sprite = self._render_message(text)

        self._message_queue.append((text, sprite, dismiss_after, sound))
        if len(self._message_queue) == 1:
            self.show_current()

        return sprite

    def push_text(self, text, dismiss_after=5000, sound=None):
        """Put text at top of stack.  Will be displayed right away
        A unique sprite will be returned from this function.  That sprite
        can be passed to Advisor.dismiss() to remove that specific sprite.
        :param text: Text to be displayed
        :param sound: Sound to be played when message is shown
        :param dismiss_after: Number of milliseconds to show message,
                            Negative numbers will cause message to be displayed
                            until dismissed.
        :return: pygame.sprite.Sprite
        """
        sprite = self._render_message(text)

        if self._message_queue:
            self.hide_current()

        self._message_queue.insert(0, (text, sprite, dismiss_after, sound))
        self.show_current()

        return sprite

    def dismiss(self, target=None):
        """Cause current displayed message to be dismissed
        If there are messages still in the queue, they will be
        displayed next.
        :param target: Specific message to be removed
        :return: None
        """
        if not self._message_queue:
            return

        current_sprite = self._message_queue[0][1]
        if target is None or target is current_sprite:
            self.hide_current()
            self._message_queue.pop(0)
            if self._message_queue:
                self.show_current()

        else:
            index = None
            for item in self._message_queue:
                if item[1] is target:
                    index = item
                    break

            if index is not None:
                self._message_queue.remove(index)

    def show_current(self, index=0):
        """Show the current message
        :return: None
        """
        text, sprite, dismiss_after, sound = self._message_queue[index]

        # remove old animations and animate the slide in
        remove_animations_of(sprite, self._animations)
        ani = self._animate_show_sprite(sprite)
        self._animations.add(ani)

        # add the sprite to the group that contains the advisor
        if sprite not in self._draw_group:
            sprite.add(self._draw_group)

        # play sound associated with the message
        # sound = prepare.SFX['misc_menu_4']
        # sound.set_volume(.2)
        # sound.play()

        # set timer to dismiss the sprite
        if dismiss_after:
            task = Task(partial(self.dismiss, sprite), dismiss_after)
            self._animations.add(task)

    def hide_current(self):
        """Hide the current message
        :return: None
        """
        sprite = self._message_queue[0][1]

        remove_animations_of(sprite, self._animations)
        ani = self._animate_hide_sprite(sprite)
        self._animations.add(ani)

        if sprite not in self._draw_group:
            sprite.add(self._draw_group)

    def empty(self):
        """Remove all message and dismiss the current one
        :return: None
        """
        if self._message_queue:
            self._message_queue = self._message_queue[:1]
            self.dismiss()

    def _animate_show_sprite(self, sprite):
        """Animate and show the sprite dropping down from advisor
        :param sprite: pygame.sprite.Sprite
        :return: None
        """
        ani = Animation(bottom=self.rect.top, round_values=True, duration=500,
                        transition='out_quint')
        ani.start(sprite.rect)
        self._animation_dict[sprite] = ani
        return ani

    def _animate_hide_sprite(self, sprite):
        """Animate and hide the sprite
        :param sprite: pygame.sprite.Sprite
        :return: None
        """

        def kill():
            del self._animation_dict[sprite]
            sprite.kill()

        ani = Animation(y=800, round_values=True,
                        duration=500, transition='out_quint')
        ani.callback = kill
        ani.start(sprite.rect)
        self._animation_dict[sprite] = ani
        return ani

    def _render_message(self, text):
        """Render the sprite that will drop down from the advisor
        :param text: Test to be rendered
        :return: pygame.sprite.Sprite
        """
        # first estimate how wide the text will be
        text_rect = pygame.Rect(self.margins, self.max_size)
        width, leftover_text = draw_text(None, text, text_rect, self._font)
        assert (leftover_text == '')

        # next make the sprite with the estimated rect size
        sprite = pygame.sprite.Sprite()
        sprite.rect = pygame.Rect((self.rect.left - width, self.rect.top),
                                  (width + self.margins[0] * 2, self.max_size[1]))

        sprite.image = pygame.Surface(sprite.rect.size, pygame.SRCALPHA)
        self.border.draw(sprite.image, sprite.image.get_rect())
        draw_text(sprite.image, text, text_rect, self._font,
                  self.fg_color, self.bg_color, True)

        return sprite
