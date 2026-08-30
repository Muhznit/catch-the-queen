#!/usr/bin/env python3
import pygame
import pygame_gui

EXT_CLI_EVENT = pygame.event.custom_type()
CLI_EVENT = pygame.event.custom_type()


def get_user_input_tuple():
    # Default keybinds, esdf. Don't knock it till you try it.
    # TODO: Read keybinds from a file, likely pygame.system.get_pref_path()
    key_up = pygame.K_e
    key_dn = pygame.K_d
    key_lf = pygame.K_s
    key_rt = pygame.K_f

    keys = pygame.key.get_pressed()
    x = int(keys[key_rt]) - int(keys[key_lf])
    y = int(keys[key_dn]) - int(keys[key_up])
    return x, y


WINDOW_WIDTH = 960
WINDOW_HEIGHT = 540


# TODO: Follow a strict template for loading assets
# /gui (kinda necessary)
# /bgm (music to listen to while loading)
# /sfx (sound effects),
# /gfx (particles)
# /static_images
# /filmstrips

class EngineState:
    def handle_event(self, event):
        pass

    def update(self, dt):
        pass

    def render(self, surface):
        pass

# TODO: For collision detection maybe make use of
# the second code snippet at https://www.pygame.org/wiki/QuadTree

class StartState(EngineState):
    def render(self, surface):
        font = pygame.font.SysFont("Courier New", 32)
        surface.fill(pygame.Color("#505050"))
        font_surf = font.render(
            "starting state", False,
            (255, 255, 255),
            (255,0,0)
        )
        surface.blit(font_surf, font_surf.get_rect())


class StopState(EngineState):
    def render(self, surface):
        font = pygame.font.SysFont("Courier New", 32)
        surface.fill(pygame.Color("#505050"))
        font_surf = font.render(
            "stop state", False,
            (255, 255, 255),
            (255,0,0)
        )
        surface.blit(font_surf, font_surf.get_rect())


class SplashState(EngineState):
    def __init__(self):
        self.fsm = None

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            return
        if event.type == pygame.KEYUP:
            self.fsm.push_state(StartState())

    def update(self, dt):
        keys = pygame.key.get_pressed()
        x, y = get_user_input_tuple()
        print(x, y)

    def render(self, surface):
        # TODO: DRY this up
        font = pygame.font.SysFont("Courier New", 32)
        surface.fill(pygame.Color("#505050"))
        font_surf = font.render(
            "splash state", False,
            (255, 255, 255),
            (255,0,0)
        )
        surface.blit(font_surf, font_surf.get_rect())


class StateMachine:
    def __init__(self):
        self._state_stack = []
        self._state = None

    def push_state(self, state):
        self._state_stack.append(state)

    def __iter__(self):
        while self._state_stack:
            self._state = self._state_stack[-1]
            self._state.fsm = self
            yield self._state

    def event_loop(self):
        quit_recieved = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit_recieved = True
                break

            if self._state:
                self._state.handle_event(event)
        return quit_recieved


    def update(self, dt):
        if self._state:
            self._state.update(dt)

    def render(self, surface):
        if self._state:
            self._state.render(surface)
            pygame.display.update()


class Engine:
    def __init__(self):
        self._state_machine = StateMachine()
        self._state_machine.push_state(SplashState())

    def run(self):
        clock = pygame.time.Clock()
        surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        for state in self._state_machine:
            dt = clock.tick(60) / 1000.0
            if self._state_machine.event_loop():
                break
            self._state_machine.update(dt)
            self._state_machine.render(surface)
        pygame.quit()


def main():
    numpass, numfail = pygame.init()
    print(f"Initialized pygame modules: {numpass=} {numfail=}")
    Engine().run()


if __name__ == "__main__":
    main()
