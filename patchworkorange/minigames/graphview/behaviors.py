"""
Here we implement activations and post run actions that are specific
to the graph view minigame

Activations are run when a vertex is activated by the visitor

PostRunActions are run by the game manager when a minigame exits

"""
from patchworkorange.core.adventuregraph import Activation, PreRequisiteList
from patchworkorange.core.minigamemanager import PostRunAction, ExitGameAction, SetContextValueAction, RunMinigameAction


class ReplaceActivationAction(PostRunAction):
    """Swap out the activation on a vertex"""

    def __init__(self, command, keyword_args):
        assert (command == "replace-activation-action")
        super(ReplaceActivationAction, self).__init__(command, keyword_args)
        self.pre_reqs = PreRequisiteList()
        for pre_req in keyword_args["vertex-pre-requisites"]:
            self.pre_reqs.append(pre_req["key"], pre_req["value"], pre_req["hint"])
        self.command = keyword_args["activation-command"]
        self.keyword_args = keyword_args["activation-keyword-args"]


class ShowClippieTextAction(PostRunAction):

    def ___init__(self, command, keyword_args):
        super(ShowClippieTextAction, self).__init__(command, keyword_args)
        self.clippie_image_name = keyword_args["clippie-image-name"]
        self.text = keyword_args["clippie-text"]


class RunMinigameActivation(Activation):
    POST_GAME_ACTION_MAP = {
        ExitGameAction.ACTION_NAME: ExitGameAction,
        SetContextValueAction.ACTION_NAME: SetContextValueAction,
        RunMinigameAction.ACTION_NAME: RunMinigameAction
    }

    def __init__(self, command, keyword_args):
        super(RunMinigameActivation, self).__init__(command, keyword_args)
        self.mini_game_name = keyword_args["mini-game-name"]
        self.mini_game_keyword_args = keyword_args["mini-game-keyword-args"] if "mini-game-keyword-args" in keyword_args else None
        self.pre_reqs = PreRequisiteList()
        self.post_run_actions = list(self.read_post_game_actions(keyword_args))

    def read_post_game_actions(self, keyword_args):
        if "post-run-actions" in keyword_args:
            for post_run_action in keyword_args["post-run-actions"]:
                action = self.POST_GAME_ACTION_MAP[post_run_action["action"]](post_run_action["action"], keyword_args)
                if "pre-requisites" in post_run_action:
                    for pre_req in post_run_action["pre-requisites"]:
                        self.pre_reqs.append(pre_req["key"], pre_req["value"], pre_req["hint"])
                yield action


# TODO: probably not useful as long as a vertex can only conside a single activation
class ReplaceActivationActivation(Activation):

    def __init__(self, command, keyword_args):
        super(ReplaceActivationActivation, self).__init__(command, keyword_args)
        self.pre_reqs = PreRequisiteList()
        for pre_req in keyword_args["vertex-pre-requisites"]:
            self.pre_reqs.append(pre_req["key"], pre_req["value"], pre_req["hint"])
        self.command = keyword_args["activation-command"]
        self.keyword_args = keyword_args["activation-keyword-args"]


class ShowClippieTextActivation(Activation):

    def __init__(self, command, keyword_args):
        super(ShowClippieTextActivation, self).__init__(command, keyword_args)
        self.clippie_image_name = keyword_args["clippie-image-name"]
        self.text = keyword_args["clippie-text"]
