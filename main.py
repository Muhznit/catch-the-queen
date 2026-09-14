#!/usr/bin/env python3
import asyncio
import dataclasses
import math
import time

import pygame

numpass, numfail = pygame.init()
WINDOW_WIDTH = 640
WINDOW_HEIGHT = 480
MAIN_CLOCK = pygame.time.Clock()
MAIN_SURFACE = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))

QUEEN_COLLIDE_EVENT = pygame.event.custom_type()
DRONE_COLLIDE_EVENT = pygame.event.custom_type()
TIME_UP_EVENT = pygame.event.custom_type()


FLASH_FREQUENCY_HZ = 3

if False:
    # Pygbag did not like this AT ALL.
    class LazyLoadedFont:
        def __init__(self, font_callable, *args, **kwargs):
            self._font_callable = font_callable
            expected_callables = (pygame.font.Font, pygame.font.SysFont)
            if not isinstance(self._font_callable, pygame.font.Font):
                if not callable(self._font_callable):
                    exc_msg = f"{font_callable} is not callable"
                    raise Exception(exc_msg)
            self._args = args
            self._kwargs = kwargs

        def __get__(self, obj, objtype=None):
            self._font = self._font_callable(*self._args, **self._kwargs)
            return self._font

    class Fonts:
        FONT_COURIER_NEW = LazyLoadedFont(pygame.font.SysFont, "Courier New", 32)
        FONT_ICOIN = LazyLoadedFont(pygame.font.Font, "assets/PressStart2P.ttf", 16)

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


BOID_SIZE = 24
BOID_MAX_SPEED = 16
def generate_butterfly(diameter=BOID_SIZE):
    color = "#00FFFF"
    size = (diameter, diameter)
    return pygame.image.load_sized_svg("assets/butterfly.svg", size)


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
    radius: int = BOID_SIZE // 2


def update_basic_physics(dt, obj):
    obj.vel += obj.acc
    obj.pos += obj.vel
    obj.acc *= 0
    if obj.vel.length() > 0:
        obj.vel = min(obj.vel, obj.vel.normalize() * BOID_MAX_SPEED,
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
    min_distance = (BOID_SIZE * 2 + BOID_MAX_SPEED)
    for boid in boids:
        heading = pygame.math.Vector2(0, 0)
        for other_boid in boids:

            pos_diff = boid.pos - other_boid.pos
            if 0 < pos_diff.length() < min_distance:
                direction_away = pos_diff.normalize()
                heading += direction_away * (BOID_MAX_SPEED - pos_diff.length())
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


def boid_to_sprite_image(boid, base_image):
    angle = -(boid.vel.angle + 90)
    rotated = pygame.transform.rotate(base_image, angle)
    return rotated

def render_boid(surface, color, boid, image=None):
    if not image:
        pygame.draw.circle(surface, color, boid.pos, boid.radius, 1)
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
    else:
        butterfly_surface = boid_to_sprite_image(boid, image)
        tint = pygame.Surface(butterfly_surface.get_size())
        tint.fill(color)
        butterfly_surface.blit(tint, special_flags=pygame.BLEND_RGB_MULT)
        surface.blit(
            butterfly_surface,
            butterfly_surface.get_rect(center=boid.pos)
        )


class Flasher(pygame.sprite.Sprite):
    def __init__(self, text, color, pos):
        pygame.sprite.Sprite.__init__(self)
        # TODO: Use interpolation to make color transitions.
        font = pygame.font.Font("assets/PressStart2P.ttf", 16)
        colors = [color, "#FFFFFF"]
        self.surfaces = []
        for i in range(2):
            font_surf = font.render(text, False, colors[i])
            self.surfaces.append(font_surf)
        self.rect = self.surfaces[0].get_rect(center=(pos.x, pos.y))
        self.lifespan = 0

    def update(self, dt):
        self.lifespan += dt
        self.rect.y -= 1

    @property
    def image(self):
        idx = int(self.lifespan * FLASH_FREQUENCY_HZ) % 2
        return self.surfaces[idx]


# Application States: States that the whole app can be in.
class StartState(EngineState):
    def __init__(self):
        self.fsm = None
        window_center = pygame.math.Vector2(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2)
        self.home_zone = BoidSpawner(window_center.copy(), WINDOW_HEIGHT / 2)
        self.cursor = pygame.math.Vector2()
        self.evil_cursor = pygame.math.Vector2()
        self.boids = list()
        boid_count = 2
        self.spawn_frequency = 2
        self.spawner_countdown = self.spawn_frequency
        for _ in range(boid_count):
            boid = Boid(self.home_zone.pos.copy())
            boid.pos.x = boid.pos.x + math.cos(_ / boid_count * 2 * math.pi) * 64
            boid.pos.y = boid.pos.y + math.sin(_ / boid_count * 2 * math.pi) * 64
            self.boids.append(boid)

        self.flasher_sprites = pygame.sprite.Group()
        self.duration = 0
        self.max_duration = 30
        self.catch_times = []
        self.hits = 0
        self.collision_eligible = set()
        self.overlapping = set()
        self.butterfly_img = generate_butterfly()

        #pygame.event.set_grab(True)
        pygame.mouse.set_visible(False)

    @property
    def score(self):
        return len(self.catch_times) - self.hits

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            return
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.add_boid()


        if event.type == QUEEN_COLLIDE_EVENT:
            self.catch_times.append(self.duration)
            sprite = Flasher("+1", "green", event.pos)
            sprite.add(self.flasher_sprites)
            #self.add_boid()

        if event.type == DRONE_COLLIDE_EVENT:
            self.hits += 1
            sprite = Flasher("-1", "red", event.pos)
            sprite.add(self.flasher_sprites)

        if event.type == TIME_UP_EVENT:
            score_summary = {
                "catches": len(self.catch_times),
                "hits": self.hits
            }
            pygame.event.set_grab(False)
            pygame.mouse.set_visible(True)
            stop_state = StopState()
            stop_state.score_summary = score_summary
            stop_state.fsm = self.fsm
            self.fsm.push_state(stop_state)

    def add_boid(self):
        boid = Boid(self.home_zone.pos.copy())
        self.boids.append(boid)

    def update(self, dt):
        self.duration += dt
        if self.duration >= self.max_duration:
            evt = pygame.event.Event(TIME_UP_EVENT)
            pygame.event.post(evt)

        t = self.duration / self.max_duration
        expected_boids = pygame.math.lerp(1, 10, t)
        if len(self.boids) < expected_boids:
            self.add_boid()

        x, y = get_user_input_tuple()
        mouse_pos = pygame.math.Vector2(pygame.mouse.get_pos())
        self.cursor.update(mouse_pos)

        self.evil_cursor.update(
            (self.cursor.x + WINDOW_WIDTH / 2) % WINDOW_WIDTH,
            (self.cursor.y + WINDOW_HEIGHT /2) % WINDOW_HEIGHT
        )

        n = pygame.math.Vector2(mouse_pos.x, 0)
        e = pygame.math.Vector2(WINDOW_WIDTH, mouse_pos.y)
        s = pygame.math.Vector2(mouse_pos.x, WINDOW_HEIGHT)
        w = pygame.math.Vector2(0, mouse_pos.y)
        farthest_edge = max([n, e, s, w], key=lambda _: (mouse_pos - _).length())

        self.home_zone.pos.update(farthest_edge)

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
            if boid.pos.distance_to(mouse_pos) < boid.radius:
                if i in self.overlapping:
                    continue
                if i == 0:
                    evt = pygame.event.Event(QUEEN_COLLIDE_EVENT, {"pos": mouse_pos})
                    pygame.event.post(evt)
                else:
                    evt = pygame.event.Event(DRONE_COLLIDE_EVENT, {"pos": mouse_pos})
                    pygame.event.post(evt)
                self.overlapping.add(i)
            else:
                self.overlapping.discard(i)

        self.flasher_sprites.update(dt)
        for flasher in self.flasher_sprites:
            if flasher.lifespan > 1:
                flasher.kill()
                del flasher

    def render(self, surface):
        surface.fill(pygame.Color("#000000"))

        if False:
            # Disabled because rendering the spawner is just distracting.
            t = max(0, self.spawner_countdown / self.spawn_frequency)
            color = pygame.Color.from_hsva(0, 0, (1 - t) ** 2 * 100, 100)
            render_boid_spawner(surface, color, t, self.home_zone)

        radius = 8.0
        render_crosshair(surface, "#FFFFFF", self.cursor, radius)
        #render_crosshair(surface, "#FFFFFF", self.evil_cursor, radius)

        chaser_color = "#808080"
        for i, boid in enumerate(self.boids):
            #mod_idx = i % 6
            #color = pygame.Color.from_hsva(mod_idx / 6 * 360, 100, 100, 100)
            color = "gold"
            if i != 0:
                color = chaser_color
            render_boid(surface, color, boid, self.butterfly_img)

        self.flasher_sprites.draw(surface)
        font = pygame.font.Font("assets/PressStart2P.ttf", 16)
        text = (
            f"Catch the gold one. Avoid the gray ones.\n"
            f"Score: {self.score}\n"
            f"Time: {self.max_duration - self.duration:.2f}"
        )
        font_surf = font.render(text, False, "#FFFFFF")
        surface.blit(font_surf, font_surf.get_rect())


class StopState(EngineState):
    def __init__(self):
        self.fsm = None
        self.score_summary = None
        self.duration = 0

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.fsm.push_state(SplashState())

    def update(self, dt):
        self.duration += dt

    def render(self, surface):
        font = pygame.font.Font("assets/PressStart2P.ttf", 24)
        surface.fill(pygame.Color("#000000"))
        text_blurbs = [
            "Final score",
            "Catches: {catches}".format(**self.score_summary),
            "Hits: {hits}\n".format(**self.score_summary),
            "Click to retry."
        ]
        if False:
            end_idx = pygame.math.lerp(1, len(text_blurbs), self.duration / 3)
            end_idx = int(end_idx)
        end_idx = len(text_blurbs)
        text = "\n".join(text_blurbs[:end_idx])
        font_surf = font.render(text, False, "#FFFFFF")
        surface.blit(font_surf, font_surf.get_rect())


class SplashState(EngineState):
    def __init__(self):
        self.fsm = None
        self.butterfly_img = generate_butterfly(256)
        self.boid = Boid((WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2))
        self.boid.radius = 128
        self.zoo = pygame.sprite.Group()
        self.duration = 0

    def handle_event(self, event):
        if  event.type == pygame.MOUSEBUTTONDOWN:
            state = StartState()
            state.fsm = self.fsm
            self.fsm.push_state(state)

    def update(self, dt):

        self.duration += dt
        self.boid.vel.x = math.cos(self.duration * math.pi) * 64
        self.boid.vel.y = math.sin(self.duration * math.pi) * 64
        keys = pygame.key.get_pressed()
        x, y = get_user_input_tuple()

    def render(self, surface):
        # TODO: DRY this up
        font = pygame.font.Font("assets/PressStart2P.ttf", 24)
        surface.fill(pygame.Color("#000000"))
        text = "Catch the Queen!\n"
        text += "by Muhznit\n\n"
        text += "Click to start"
        font_surf = font.render(text, False, "#FFFFFF")

        render_boid(surface, "gold", self.boid, self.butterfly_img)
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
            pass

    def render(self, surface):
        if self._state:
            self._state.render(surface)
            pass


class Engine:
    def __init__(self):
        self._state_machine = StateMachine()
        self._state_machine.push_state(None)

    def run(self):
        for state in self._state_machine:
            dt = MAIN_CLOCK.tick(60) / 1000.0
            if self._state_machine.event_loop():
                break
            self._state_machine.update(dt)
            self._state_machine.render(MAIN_SURFACE)
            pygame.display.update()

async def main():
    print(f"Initialized pygame modules: {numpass=} {numfail=}")
    state_machine = StateMachine()
    state_machine.push_state(SplashState())
    for state in state_machine:
        #Engine().run()
        dt = MAIN_CLOCK.tick(60) / 1000.0
        if state_machine.event_loop():
            break
        state_machine.update(dt)
        state_machine.render(MAIN_SURFACE)
        pygame.display.update()
        await asyncio.sleep(0)
    pygame.quit()


asyncio.run(main())
