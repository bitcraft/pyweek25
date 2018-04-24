import pygame


class Game:

    def __init__(self, minigame_manager, game_context):
        self.minigame_manager = minigame_manager
        self.game_context = game_context
        self.surface = None

    def run(self):
        self.surface = pygame.display.get_surface()

        self.show_title()

        self.game_context['show_clippie'] = False

        # Purple patch (donatello.patch)
        self.show_cutscene("wake-up", "cutscenes.yaml")
        self.show_graph("day-1.yaml", "real-life.tmx")
        self.show_cutscene("end-of-day-one", "cutscenes.yaml")
        self.show_jackin()
        self.show_graph("mission-1.yaml", "network.tmx")
        self.show_cutscene("end-of-mission-one", "cutscenes.yaml")

        # Blue patch (leonardo.patch)
        self.show_graph("day-2.yaml", "real-life.tmx")
        self.show_jackin()
        self.show_graph("mission-2.yaml", "network.tmx")
        self.show_cutscene("end-of-mission-two", "cutscenes.yaml")

        # Red patch (raphael.patch)
        self.show_graph("day-3.yaml", "real-life.tmx")
        self.game_context = {'show_clippie': True, 'clippie_queue': [
            "I see that you are jacked in.",
            "Would you like help with that?",
            "Don't forget to pick up the red diskette from Danny.",
            "Danny is at the pawn shop.",
            "Do you know where the pawn shop is?",
            "That's where you will find Danny.",
            "...with the red diskette.",
            "...which has the patch.",
            "Danny's a great guy, you know?",
            "Actually, I have no idea about that.",
            "I'm just version 1.0",
        ]}
        self.show_jackin()
        self.show_graph("mission-3.yaml", "network.tmx")

        self.show_credit_roll()
        pygame.quit()

    def show_title(self):
        self.minigame_manager.run_minigame("Title", None)
        self.cleanup_pygame()

    def show_jackin(self):
        self.minigame_manager.run_minigame("Jackin", self.game_context)
        self.cleanup_pygame()

    def show_cutscene(self, scene_name, scene_file_name):
        self.minigame_manager.run_minigame("Cutscene", self.game_context,
                                           scene_name=scene_name,
                                           scene_file_name=scene_file_name)
        self.cleanup_pygame()

    def show_graph(self, graph_yaml, graph_tmx):
        self.minigame_manager.run_minigame("GraphView", self.game_context,
                                           graph_yaml=graph_yaml,
                                           graph_tmx=graph_tmx)
        self.cleanup_pygame()

    def show_credit_roll(self):
        self.minigame_manager.run_minigame("CreditRoll", self.game_context)

    def cleanup_pygame(self):
        pygame.mouse.set_visible(True)
        pygame.mixer.stop()
        self.surface.fill(0)
