from abc import ABC, abstractmethod
from logging import getLogger

from patchworkorange.core.adventuregraph import PreRequisiteList

logger = getLogger(__name__)


class Minigame(ABC):
    GAME_NAME = "UNDEFINED"

    def __init__(self):
        self.minigame_manager = None
        self.instant_win = False

    @abstractmethod
    def initialize(self, context):
        pass

    @abstractmethod
    def run(self, context):
        pass

# TODO: build PostRunAction factory


class PostRunAction:
    ACTION_NAME = "base-action"

    def __init__(self, action, keyword_args):
        assert(action == self.ACTION_NAME)
        self.action = action
        self.keyword_args = keyword_args
        self.pre_reqs = PreRequisiteList()

    def can_run(self, context):
        return self.pre_reqs.get_failing_pre_requisites(context) == 0


class RunMinigameAction(PostRunAction):
    ACTION_NAME = "run-mini-game"

    def __init__(self, action, keyword_args):
        super(RunMinigameAction, self).__init__(action, keyword_args)
        self.mini_game_name = keyword_args["mini-game-name"]
        self.mini_game_keyword_args = keyword_args["mini-game-keyword-args"]
        self.post_run_actions = keyword_args["post-run-actions"]


class SetContextValueAction(PostRunAction):
    ACTION_NAME = "set-context-value"

    def __init__(self, action, keyword_args):
        super(SetContextValueAction, self).__init__(action, keyword_args)
        for pra in keyword_args["post-run-actions"]:
            if pra["action"] == self.action:
                self.key = pra["context-key"]
                self.value = pra["context-value"]


class ExitGameAction(PostRunAction):
    ACTION_NAME = "exit-action"


class MinigameManager:
    WHITE = (255, 255, 255)

    def __init__(self, minigame_registry):
        self.minigame_registry = minigame_registry

    def run_minigame(self, game_name, game_context, post_run_actions=list(), **kwargs):
        minigame = self.minigame_registry[game_name](**kwargs)
        minigame.minigame_manager = self
        minigame.initialize(game_context)
        minigame.run(game_context)

        if post_run_actions:
            # this is technically recursive, try not to nest more than 3000
            # calls to run_minigame and blow the stack mmmkay?
            return self.handle_post_run_actions(post_run_actions, game_context)
        return []

    def handle_post_run_actions(self, post_run_actions, game_context):
        unhandled = list()
        for post_run_action in post_run_actions:
            if not post_run_action.pre_reqs.get_failing_pre_requisites(game_context):
                unhandled_action = self.handle_post_run_action(post_run_action, game_context)
                if unhandled_action is not None:
                    unhandled.append(unhandled_action)
        # return unhandled exceptions so they can be handled by some other class
        return unhandled

    def handle_post_run_action(self, post_run_action, game_context):
        if post_run_action.action == RunMinigameAction.ACTION_NAME:
            self.run_minigame(post_run_action.mini_game_name,
                              game_context,
                              post_run_actions=post_run_action.post_run_actions,
                              **post_run_action.mini_game_keyword_args)

        elif post_run_action.action == SetContextValueAction.ACTION_NAME:
            game_context[post_run_action.key] = post_run_action.value

        else:
            return post_run_action  # return unhandled actions


# This little bit of fuckery is important
# don't move this line or the registry won't find the minigames
from patchworkorange.minigames import *


class MinigameRegistry:

    def __init__(self):
        self.registry = dict()

    def locate_minigames(self):
        """Locate all minigames in the minigames sub-package and register them"""
        for subclass in Minigame.__subclasses__():
            self.registry[subclass.GAME_NAME] = subclass
            logger.debug("Registered minigame: \"%s\"" % subclass.GAME_NAME)

    def __getitem__(self, minigame_name):
        return self.registry[minigame_name]
