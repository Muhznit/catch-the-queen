#!/usr/bin/env python3
import dataclasses
import math
import random

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

@dataclasses.dataclass(slots=True)
class BallSpawner:
    x: int
    y: int
    radius: float

    @property
    def pos(self):
        return pygame.math.Vector2(self.x, self.y)


@dataclasses.dataclass(slots=True)
class Ball:
    pos: pygame.math.Vector2 = dataclasses.field(default_factory=pygame.math.Vector2)
    vel: pygame.math.Vector2 = dataclasses.field(default_factory=pygame.math.Vector2)
    acc: pygame.math.Vector2 = dataclasses.field(default_factory=pygame.math.Vector2)


def update_basic_physics(dt, obj):
    obj.vel += obj.acc
    obj.pos += obj.vel
    obj.acc *= 0
    #obj.vel *= .9


def update_bounce_off_screen(dt, obj):
    future_pos = obj.pos + obj.vel + obj.acc
    if future_pos.x > WINDOW_WIDTH:
        old_x = obj.pos.x
        obj.pos.x = WINDOW_WIDTH
        obj.vel.x -= obj.pos.x - old_x
        obj.vel.x *= -1

    if future_pos.x < 0:
        old_x = obj.pos.x
        obj.pos.x = 0
        obj.vel.x -= obj.pos.x - old_x
        obj.vel.x *= -1

    if future_pos.y > WINDOW_HEIGHT:
        old_y = obj.pos.y
        obj.pos.y = WINDOW_HEIGHT
        obj.vel.y -= obj.pos.y - old_y
        obj.vel.y *= -1

    if future_pos.y < 0:
        old_y = obj.pos.y
        obj.pos.y = 0
        obj.vel.y -= obj.pos.y - old_y
        obj.vel.y *= -1


def update_wrap_around_screen(dt, obj):
    obj.pos.x = (WINDOW_WIDTH + obj.pos.x) % WINDOW_WIDTH
    obj.pos.y = (WINDOW_HEIGHT + obj.pos.y) % WINDOW_HEIGHT


def calc_cohesion_vectors(boids):
    midpoint = pygame.math.Vector2(0, 0)
    for boid in boids:
        midpoint += boid.pos

    midpoint /= len(boids)

    for boid in boids:
        direction = midpoint - boid.pos
        #direction.normalize_ip()
        yield direction


def calc_alignment_vectors(boids):
    heading = pygame.math.Vector2(0, 0)
    for boid in boids:
        heading += boid.vel
    heading /= len(boids)
    #heading.normalize_ip()

    for boid in boids:
        yield heading


def calc_separation_vectors(boids):
    min_distance = 64
    for boid in boids:
        heading = pygame.math.Vector2(0, 0)
        for other_boid in boids:
            distance = boid.pos.distance_to(other_boid.pos)

            pos_diff = boid.pos - other_boid.pos
            if 0 < pos_diff.length() < min_distance:
                heading += pos_diff * (min_distance / distance)
        yield heading


def render_ball_spawner(surface, color, instance):
    pygame.draw.circle(surface, color, (instance.x, instance.y), instance.radius)


def render_crosshair(surface, color, center, radius):
    pygame.draw.line(
        surface, color,
        (center.x, center.y - radius),
        (center.x, center.y + radius)
    )
    pygame.draw.line(
        surface, color,
        (center.x - radius, center.y),
        (center.x + radius, center.y)
    )


# Application States: States that the whole app can be in.
class StartState(EngineState):
    def __init__(self):
        self.home_zone = BallSpawner(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2, 64)
        self.cursor = self.home_zone.pos
        self.balls = list()
        for _ in range(32):
            ball = Ball(self.home_zone.pos)
            ball.acc.x = random.randint(1, 8) * random.choice([-1, 1])
            ball.acc.y = random.randint(1, 8) * random.choice([-1, 1])
            ball.pos.x = ball.pos.x + math.cos(_ / 16 * 2 * math.pi) * 64
            ball.pos.y = ball.pos.y + math.sin(_ / 16 * 2 * math.pi) * 64
            self.balls.append(ball)

    def update(self, dt):
        x, y = get_user_input_tuple()

        self.cursor.update(pygame.mouse.get_pos())

        for ball in self.balls:
            update_basic_physics(dt, ball)
            update_bounce_off_screen(dt, ball)
            #update_wrap_around_screen(dt, ball)

        m1, m2, m3 = pygame.mouse.get_pressed()
        cohesions = tuple(calc_cohesion_vectors(self.balls))
        separations = tuple(calc_separation_vectors(self.balls))
        alignments = tuple(calc_alignment_vectors(self.balls))
        for i, ball in enumerate(self.balls):
            ball.acc += cohesions[i] + separations[i] + alignments[i]
            ball.acc.normalize_ip()
            ball.acc -= ball.vel

    def render(self, surface):
        surface.fill(pygame.Color("#505050"))

        render_ball_spawner(surface, "#FF0000", self.home_zone)

        radius = 8.0
        render_crosshair(surface, "#FFFFFF", self.cursor, radius)

        for ball in self.balls:
            pygame.draw.circle(surface, "#800000", ball.pos, radius)
        font = pygame.font.SysFont("Courier New", 32)
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
