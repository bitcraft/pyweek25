GAME_TITLE = "A Patchwork Orange"

import logging
from argparse import ArgumentParser

import pygame

from patchworkorange.core import resources
from patchworkorange.core.game import Game
from patchworkorange.core.minigamemanager import MinigameRegistry, MinigameManager
from patchworkorange.core.resources import get_data_asset

logger = logging.getLogger(__name__)


def main():
    pygame.mixer.pre_init(44100, -16, 2, 2048)
    pygame.init()
    size = (1280, 720)
    pygame.display.set_icon(pygame.image.load(resources.get_image_asset("icon.png")))
    pygame.display.set_caption(GAME_TITLE)
    pygame.display.set_mode(size)

    parser = ArgumentParser(prog="TBD")
    parser.add_argument("--minigame", help="Pass the name of a minigame to run instead of the full game.")
    parser.add_argument("--cutscenes", help="Show all the cutscenes in a file")
    parser.add_argument("--mgargs", help="--minigame needs to be set when using this.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)

    registry = MinigameRegistry()
    registry.locate_minigames()

    minigame_manager = MinigameManager(registry)

    if args.cutscenes:
        import yaml
        with open(get_data_asset(args.cutscenes)) as fp:
            data = yaml.load(fp)
        for scene in data:
            logger.debug("Loading scene \"%s\"" % scene)
            minigame_manager.run_minigame("Cutscene", {},
                                          scene_name=scene, scene_file_name=args.cutscenes)

    if args.mgargs is not None and args.minigame is None:
        logger.error("--mgargs set without --minigame being set. Can't set minigame arguments without setting the "
                     "minigame to run.")

    if args.minigame is not None:
        logger.debug("Loading minigame \"%s\"" % args.minigame)
        kwargs = mgargs_as_dict(args.mgargs) if args.mgargs is not None else {}
        minigame_manager.run_minigame(args.minigame, {}, **kwargs)
        logger.debug("Exiting...")
    else:
        logger.debug("Loading main game")
        # TODO: the initial game state should not be hard-coded...
        Game(minigame_manager, {"game-state": "wake-up-dialog"}).run()
        logger.debug("Exiting...")

    pygame.quit()


def mgargs_as_dict(minigame_args):
    minigame_args = minigame_args.replace("=", ",")
    minigame_args = minigame_args.split(",")

    return {minigame_args[i]: minigame_args[i + 1] for i in range(0, len(minigame_args), 2)}
