#!/usr/bin/env python3
import dataclasses
import io
import math
import statistics

import pygame
import pygame_gui

BOID_CAUGHT_EVENT = pygame.event.custom_type()
CLI_EVENT = pygame.event.custom_type()

WINDOW_WIDTH = 960
WINDOW_HEIGHT = 540
FLASH_FREQUENCY_HZ = 10

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


def generate_butterfly():
    color = "#00FFFF"
    surface = pygame.Surface((32, 32))
    with open("assets/butterfly.svg", "r") as f:
        svg_data = f.read()
        scale_factor = .5
        svg_data = svg_data.replace('width="32"', 'width="8"')
        svg_data = svg_data.replace('height="32"', 'height="8"')
        svg_data = svg_data.replace('#ff0000', '#00ff00')
        svg_data_bytes = io.BytesIO(svg_data.encode("utf-8"))
        return pygame.image.load(svg_data_bytes, "svg")


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
class BoidSpawner:
    pos: pygame.math.Vector2 = dataclasses.field(default_factory=pygame.math.Vector2)
    radius: float = 64

@dataclasses.dataclass(slots=True)
class Boid:
    pos: pygame.math.Vector2 = dataclasses.field(default_factory=pygame.math.Vector2)
    vel: pygame.math.Vector2 = dataclasses.field(default_factory=pygame.math.Vector2)
    acc: pygame.math.Vector2 = dataclasses.field(default_factory=pygame.math.Vector2)


def update_basic_physics(dt, obj):
    obj.vel += obj.acc
    obj.pos += obj.vel
    obj.acc *= 0
    if obj.vel.length() > 0:
        obj.vel = min(obj.vel, obj.vel.normalize() * 32,
                      key=pygame.math.Vector2.magnitude)


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
    min_distance = 32
    for boid in boids:
        heading = pygame.math.Vector2(0, 0)
        for other_boid in boids:

            pos_diff = boid.pos - other_boid.pos
            if 0 < pos_diff.length() < min_distance:
                direction_away = pos_diff.normalize()
                # TODO: direction_away and pos_diff are interchangableish.
                # The former produces a gaurantee that collisions are avoided
                # like actual boids, but pos_diff yields constantly-moving
                # "swarms".
                heading += pos_diff * (min_distance - pos_diff.length()) * min_distance
        yield heading / len(boids)


def render_boid_spawner(surface, color, t, instance):
    radius = instance.radius * t

    pygame.draw.circle(surface, color, (instance.pos.x, instance.pos.y),
                       radius, 1)


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

def render_boid(surface, color, boid):
    heading = boid.vel
    if heading.length():
        heading = heading.normalize() * 4
    tip = boid.pos + heading
    rt_tip = boid.pos + heading.rotate(120)
    lf_tip = boid.pos + heading.rotate(-120)
    tail = boid.pos - boid.vel
    pygame.draw.line(surface, color, tip, rt_tip)
    pygame.draw.line(surface, color, tip, lf_tip)
    pygame.draw.line(surface, color, boid.pos, tail)


class BoidCaughtSprite(pygame.sprite.Sprite):
    def __init__(self, pos):
        pygame.sprite.Sprite.__init__(self)
        font = pygame.font.Font("assets/ICOIN.FON", 32)
        colors = ["white", (255, 0, 0)]
        self.surfaces = []
        for i in range(2):
            font_surf = font.render(
                "CATCH!", False,
                colors[i]
            )
            self.surfaces.append(font_surf)
        self.rect = self.surfaces[0].get_rect(center=(pos.x, pos.y))
        self.lifespan = 0

    def update(self, dt):
        self.lifespan += dt
        self.rect.y -= 1
        if self.lifespan >= 180:
            kill()

    @property
    def image(self):
        idx = int(self.lifespan * FLASH_FREQUENCY_HZ) % 2
        return self.surfaces[idx]



# Application States: States that the whole app can be in.
class StartState(EngineState):
    def __init__(self):
        window_center = pygame.math.Vector2(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2)
        self.home_zone = BoidSpawner(window_center.copy(), WINDOW_HEIGHT / 2)
        self.cursor = pygame.math.Vector2()
        self.evil_cursor = pygame.math.Vector2()
        self.boids = list()
        boid_count = 2
        self.spawn_frequency = 2
        self.spawner_countdown = self.spawn_frequency
        self.score = 0
        for _ in range(boid_count):
            boid = Boid(self.home_zone.pos.copy())
            boid.pos.x = boid.pos.x + math.cos(_ / boid_count * 2 * math.pi) * 64
            boid.pos.y = boid.pos.y + math.sin(_ / boid_count * 2 * math.pi) * 64
            self.boids.append(boid)

        self.flasher_sprites = pygame.sprite.Group()

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            return
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.add_boid()
        if event.type == BOID_CAUGHT_EVENT:
            self.score += 1
            sprite = BoidCaughtSprite(event.pos)
            sprite.add(self.flasher_sprites)

    def add_boid(self):
        boid = Boid(self.home_zone.pos.copy())
        self.boids.append(boid)

    def update(self, dt):
        x, y = get_user_input_tuple()
        mouse_pos = pygame.math.Vector2(pygame.mouse.get_pos())
        self.cursor.update(mouse_pos)

        self.evil_cursor.update(
            (self.cursor.x + WINDOW_WIDTH / 2) % WINDOW_WIDTH,
            (self.cursor.y + WINDOW_HEIGHT /2) % WINDOW_HEIGHT
        )

        self.spawner_countdown -= dt
        if self.spawner_countdown <= 0:
            self.add_boid()
            n = pygame.math.Vector2(mouse_pos.x, 0)
            e = pygame.math.Vector2(WINDOW_WIDTH, mouse_pos.y)
            s = pygame.math.Vector2(mouse_pos.x, WINDOW_HEIGHT)
            w = pygame.math.Vector2(0, mouse_pos.y)
            nearest = min([n, e, s, w], key=lambda _: (mouse_pos - _).length())

            self.home_zone.pos.update(nearest)
            self.spawner_countdown = self.spawn_frequency

        cohesions = tuple(calc_cohesion_vectors(self.boids))
        separations = tuple(calc_separation_vectors(self.boids))
        alignments = tuple(calc_alignment_vectors(self.boids))
        for i, boid in enumerate(self.boids):
            boid.acc += cohesions[i] + separations[i] + alignments[i]
            boid.acc -= boid.vel
            match i == 0:
                case False:
                    boid.acc += self.cursor - boid.pos
                case True:
                    boid.acc += self.evil_cursor - boid.pos
            if boid.acc.length() > 1:
                boid.acc.scale_to_length(1)

        for i, boid in enumerate(self.boids):
            update_basic_physics(dt, boid)
            update_bounce_off_screen(dt, boid)
            #update_wrap_around_screen(dt, boid)
            if i == 0 and boid.pos.distance_to(mouse_pos) < 8:
                evt = pygame.event.Event(BOID_CAUGHT_EVENT, {"pos": mouse_pos})
                pygame.event.post(evt)

        self.flasher_sprites.update(dt)
        for flasher in self.flasher_sprites:
            if flasher.lifespan > 1:
                flasher.kill()
                del flasher

    def render(self, surface):
        surface.fill(pygame.Color("#000000"))

        t = max(0, self.spawner_countdown / self.spawn_frequency)
        color = pygame.Color.from_hsva(0, 0, (1 - t) ** 2 * 100, 100)
        render_boid_spawner(surface, color, t, self.home_zone)

        radius = 8.0
        render_crosshair(surface, "#FFFFFF", self.cursor, radius)
        #render_crosshair(surface, "#FFFFFF", self.evil_cursor, radius)

        for i, boid in enumerate(self.boids):
            mod_idx = i % 6
            color = pygame.Color.from_hsva(mod_idx / 6 * 360, 100, 100, 100)
            render_boid(surface, color, boid)

        self.flasher_sprites.draw(surface)
        font = pygame.font.Font("assets/ICOIN.FON", 32)
        font_surf = font.render(
            f"starting state. {self.score=}", False,
            (255, 255, 255),
            (255,0,0)
        )
        surface.blit(font_surf, font_surf.get_rect())


class StopState(EngineState):
    def render(self, surface):
        font = pygame.font.SysFont("Courier New", 32)
        surface.fill(pygame.Color("#000000"))
        font_surf = font.render(
            "stop state", False,
            (255, 255, 255),
            (255,0,0)
        )
        surface.blit(font_surf, font_surf.get_rect())


class SplashState(EngineState):
    def __init__(self):
        self.fsm = None
        self.butterfly_img = generate_butterfly()
        self.zoo = pygame.sprite.Group()

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            return
        if event.type == pygame.KEYUP:
            self.fsm.push_state(StartState())

    def update(self, dt):
        keys = pygame.key.get_pressed()
        x, y = get_user_input_tuple()

    def render(self, surface):
        # TODO: DRY this up
        font = pygame.font.SysFont("Courier New", 32)
        surface.fill(pygame.Color("#000000"))
        font_surf = font.render(
            "splash state", False,
            (255, 255, 255),
            (255,0,0)
        )
        surface.blit(font_surf, font_surf.get_rect())
        #surface.blit(self.butterfly_img, self.butterfly_img.get_rect())


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
