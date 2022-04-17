import pygame
import random
import math


class Player(pygame.sprite.Sprite):
    def __init__(self):
        # image used as blueprint for rotation
        self.static_image = pygame.image.load("images/flappy_bird.png").convert_alpha()
        self._image = self.static_image.copy()
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)
        self.y_boundary = None
        self.y_boundary_offset = 15

        self.time = 0
        self.gravity = 14
        self.jump_vel = -5.1

        self.rotation = 1
        self.min_rotation = -15
        self.max_rotation = 90

        self.tick_started = None
        self.is_jumping = False
        self.disable_jumping = False

        super().__init__()

    def update(self, events):
        if self.tick_started is None:
            self.tick_started = pygame.time.get_ticks()

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not self.disable_jumping:
                self.jump()

        self.impose_gravity()
        self.rect.clamp_ip(pygame.Rect((0, 0), (1200, self.y_boundary + self.y_boundary_offset)))

    def impose_gravity(self):  # v = gt + vi
        vel = self.gravity * self.time + self.jump_vel

        self.rect.move_ip(0, math.ceil(vel))
        self.time = (pygame.time.get_ticks() - self.tick_started) / 1000

        if math.ceil(vel) > 0:  # falling
            if self.rotation < self.max_rotation:
                self.rotation = min(self.max_rotation, self.rotation + math.ceil(vel) / 2.5)

                self.image = pygame.transform.rotate(self.static_image, -self.rotation)
                self.rect = self.image.get_rect(center=self.rect.center)
        else:
            if self.rotation > self.min_rotation:
                self.rotation = max(self.min_rotation, self.rotation - abs(math.ceil(vel * 2)))

                self.image = pygame.transform.rotate(self.static_image, -self.rotation)
                self.rect = self.image.get_rect(center=self.rect.center)

    def jump(self):
        self.tick_started = pygame.time.get_ticks()

    def reset_clock(self):
        self.tick_started = None

    def reset(self, topleft):
        self.reset_clock()
        self.image = self.static_image.copy()
        self.time = 0
        self.rotation = 1
        self.disable_jumping = False
        self.rect.topleft = topleft

    @property
    def image(self):
        return self._image

    @image.setter
    def image(self, value):
        self._image = value
        self.mask = pygame.mask.from_surface(self._image)


class PipeObstacle(pygame.sprite.Sprite):
    def __init__(self):
        self._image = None
        self.rect = None
        self.mask = None
        self.head_image = pygame.image.load("images/pipe_head.png").convert()
        self.body_image = pygame.image.load("images/pipe_body.png").convert()
        self.serial_num = 0

        super().__init__()

    def move(self, distance):
        self.rect.move_ip(-distance, 0)

        # if pipe is outside of screen, delete it
        if self.rect.right <= 0:
            self.kill()

    def change_height(self, height, add=False):
        """
        transforms `self.image` up to the specified height
        :param height: value that will be set or added to the height
        :param add: transforms the height by adding the value provided to the current height
        """
        # subtract head image height so the entire image height is the same as the body + head height
        height = max(self.head_image.get_height(), height)  # prevent a negative height
        body_image_width = self._body_image.get_width()
        added_body_image_height = self._body_image.get_height() + height - self._head_image.get_height()
        body_image_height = height - self._head_image.get_height()

        if add:
            self.body_image = pygame.transform.scale(self.body_image, (body_image_width, added_body_image_height))
        else:
            self.body_image = pygame.transform.scale(self.body_image, (body_image_width, body_image_height))

    @property
    def image(self):
        return self._image

    @image.setter
    def image(self, value):
        self._image = value
        self.rect = self._image.get_rect()
        self.mask = pygame.mask.from_surface(self._image)

    @property
    def body_image(self):
        return self._body_image

    @body_image.setter
    def body_image(self, value):
        """enable scaling of the body image of the pipe without scaling the head image"""
        self._body_image = value.convert()

        bg_size = (self._head_image.get_width(), self._body_image.get_height() + self._head_image.get_height())
        background = pygame.Surface(bg_size, pygame.SRCALPHA)

        body_image_pos = (
            math.ceil(background.get_rect().centerx - self._body_image.get_width() / 2), self._head_image.get_height())
        head_image_pos = (background.get_rect())

        background.blit(self._body_image, body_image_pos)
        background.blit(self._head_image, head_image_pos)

        self.image = background

    @property
    def head_image(self):
        return self._head_image

    @head_image.setter
    def head_image(self, value):
        self._head_image = value.convert()


class GroundObstacle(pygame.sprite.Sprite):
    def __init__(self):
        self.image = pygame.Surface((100, 100)).convert()  # moving ground will be blit onto this placeholder surface
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)
        self.moving_image = pygame.image.load("images/ground.png").convert()
        self.moving_image_rect = self.moving_image.get_rect()

        self._follow_up_moving_image = self.moving_image.copy()

        super().__init__()

    def move(self, distance):
        """
        move the surface while always keeping it on screen in a loop

        move the main image with a followup copy behind it, and when the main image is completely out of the screen,
        set its position behind the followup copy in a loop (blit all images onto the placeholder surface)
        """
        self.moving_image_rect.move_ip(-distance, 0)

        if self.moving_image_rect.right < self.rect.left:
            self.moving_image_rect.left = self.moving_image_rect.right

        follow_up_image_pos = (self.moving_image_rect.right, self.moving_image_rect.top)

        self.image.blit(self.moving_image, self.moving_image_rect)
        self.image.blit(self._follow_up_moving_image, follow_up_image_pos)


class GameManager:
    """
    Class for managing game function (forward movement of obstacles, managing difficulty, etc...)
    """

    def __init__(self, player, screen_width, screen_height):
        self.surface = pygame.Surface((screen_width, screen_height))
        self.rect = self.surface.get_rect()

        self.static_game_speed = 2  # the speed each obstacle moves in terms of time
        self.game_speed = self.static_game_speed  # pixels for each obstacle to move every frame
        self.game_fps = 120
        self.pipe_spawning_dist = 600  # distance between pipe spawns

        self.player = player
        self.ground = GroundObstacle()
        self.background = pygame.image.load("images/background.png").convert()
        self.title_image = pygame.image.load("images/flappy bird title.png").convert_alpha()
        self.title_rect = self.title_image.get_rect()
        self.starting_screen_button = Button(pygame.image.load("images/start_button.png").convert_alpha(),
                                             self.initiate_game)
        self.restart_game_button = Button(pygame.image.load("images/restart_game_button.png").convert_alpha(),
                                          self.restart_game)

        self.game_over_title = pygame.image.load("images/Game Over.png").convert_alpha()
        self.game_over_title_rect = self.game_over_title.get_rect()

        self.scoreboard_bg = pygame.image.load("images/scoreboard.png").convert_alpha()
        self.scoreboard = self.scoreboard_bg.copy()
        self.scoreboard_rect = self.scoreboard.get_rect()

        self.width = screen_width
        self.height = screen_height
        self.game_height = self.ground.rect.top  # y level where game objects should be placed on top of
        self.pipe_gap_width = 200
        self.min_pipe_height = 70  # keep over the height of the pipe head image itself
        self.previous_pipe_serial = 0
        self.current_pipe_serial = self.previous_pipe_serial

        self.obstacles = pygame.sprite.Group()  # includes `self.ground`
        self.player_starting_pos = (100, 400)
        self.player_max_idle_pos_y = 50
        self.player_min_idle_pos_y = 50
        self.player_idle_vel = 1

        self.pipe_height_offsets = 150, 300, 450
        self.far_pipe_h_offset = (*[x + self.min_pipe_height + self.pipe_gap_width for x in self.pipe_height_offsets],)
        self.short_pipe_h_offset = (*[x + self.min_pipe_height for x in self.pipe_height_offsets],)

        self.game_started = False  # True when game is on the starting screen
        self.game_ended = False  # when the game is on the scoreboard

        self.last_pipe_gap_pos = 0  # previous height of the top pipe
        self.distance_from_last_pipe = 0  # total distance the ground has moved since the last pipe
        self.first_pipe = ()  # the 2 pipes in font of player

        self.score_font = pygame.font.Font("arcade_game_font.ttf", 45)
        self._score = 0
        self.best_score = 0
        self.score_increase = 1
        self.score_text_colour = (255, 255, 255)
        self.score_text = self.score_font.render(str(self.score), False, self.score_text_colour).convert_alpha()
        self.score_pos = (10, 10)

        self.score_stat_colour = (181, 125, 58)
        self.final_score_txt = self.score_font.render(str(self.score), False, self.score_stat_colour)
        self.best_score_txt = self.score_font.render(str(self.best_score), False, self.score_stat_colour)
        self.final_score_txt_rect = self.final_score_txt.get_rect(centerx=438, top=67 + 10)
        self.best_score_txt_rect = self.best_score_txt.get_rect(centerx=448, top=168 + 10)
        self.rel_restart_button_pos = (25, 56)

        self.obstacles.add(self.ground)

    def setup_game(self):
        """positions the game objects and also scale certain objects"""
        self.background = pygame.transform.scale(
            self.background, (self.width, self.height - self.ground.image.get_height()))
        self.ground.moving_image = pygame.transform.scale(
            self.ground.moving_image, (self.width, self.ground.image.get_height()))
        self.ground.image = pygame.transform.scale(self.ground.image, self.ground.moving_image.get_size())
        self.ground._follow_up_moving_image = self.ground.moving_image.copy()

        self.title_image = pygame.transform.scale(
            self.title_image, (self.title_rect.width * 2, self.title_rect.height * 2))
        self.title_rect = self.title_image.get_rect(center=(self.width / 2, 150))
        self.game_over_title = pygame.transform.scale(
            self.game_over_title, (self.game_over_title_rect.width * 2, self.game_over_title_rect.height * 2))

        self.ground.rect.topleft = (0, self.background.get_height())
        self.ground.mask = pygame.mask.from_surface(self.ground.image)
        self.ground.moving_image_rect = self.ground.moving_image.get_rect()

        self.player.rect.topleft = self.player_starting_pos
        self.starting_screen_button.rect.center = (self.width / 2, self.height / 2)

        self.game_height = self.ground.rect.top
        self.player.y_boundary = self.game_height

    def update(self, events):
        """move obstacles, check for collisions, and move the player"""
        self.surface.blit(self.background, self.background.get_rect())

        self.obstacles.draw(self.surface)
        self.surface.blit(self.player.image, self.player.rect)

        if self.game_ended:  # update the overlays and stop the obstacles from moving
            self.initiate_game_over_screen(events)
        else:
            self.move_obstacles()

        if self.game_started:
            # allow player to move when game is over
            self.player.update(events)

        if self.game_started and not self.game_ended:
            self.loop_pipes()

            self.distance_from_last_pipe += self.game_speed
            self.surface.blit(self.score_text, self.score_pos)

            if pygame.sprite.spritecollide(self.player, self.obstacles, False, pygame.sprite.collide_mask):
                self.initiate_game_over_screen(events)
        elif not self.game_started:
            # display starting screen overlays and animate player idle animation
            self.starting_screen_button.update(events)

            self.surface.blit(self.title_image, self.title_rect)
            self.surface.blit(self.starting_screen_button.image, self.starting_screen_button.rect)

            self.player.rect.move_ip(0, self.player_idle_vel)
            if self.player.rect.y >= self.player_starting_pos[1] + self.player_max_idle_pos_y:
                self.player_idle_vel = -self.player_idle_vel
            elif self.player.rect.y <= self.player_starting_pos[1] - self.player_min_idle_pos_y:
                self.player_idle_vel = abs(self.player_idle_vel)

    def move_obstacles(self):
        """move the obstacles and increase score when passed"""
        for obstacle in self.obstacles:
            obstacle.move(self.game_speed)

            if type(obstacle) == PipeObstacle and obstacle.serial_num == self.current_pipe_serial:
                if self.player.rect.left > obstacle.rect.left:
                    self.current_pipe_serial += 1
                    self.score += self.score_increase

                    if self.pipe_spawning_dist > 375:
                        self.pipe_spawning_dist -= 0.225225225

    def add_pipes(self):
        """add two pipes top and bottom with a specified gap in between"""
        bottom_pipe = PipeObstacle()
        top_pipe = PipeObstacle()
        farthest_side = max(self.game_height, 0, key=lambda x: abs(x - self.last_pipe_gap_pos))

        if farthest_side == 0:
            top_pipe_height = farthest_side + random.randint(
                self.min_pipe_height, random.choices(self.short_pipe_h_offset, (2, 1.5, 1))[0])
        else:  # self.game_height
            top_pipe_height = farthest_side - random.randint(
                self.min_pipe_height + self.pipe_gap_width, random.choices(self.far_pipe_h_offset, (2, 1.5, 1))[0])

        self.last_pipe_gap_pos = top_pipe_height

        top_pipe.change_height(top_pipe_height)
        bottom_pipe.change_height(self.game_height - top_pipe_height - self.pipe_gap_width)

        top_pipe.image = pygame.transform.rotate(top_pipe.image, 180)
        top_pipe.rect.topleft = (self.width, 0)
        bottom_pipe.rect.bottomleft = (self.width, self.game_height)

        bottom_pipe.serial_num = self.previous_pipe_serial
        top_pipe.serial_num = self.previous_pipe_serial
        self.previous_pipe_serial += 1

        self.obstacles.add(top_pipe, bottom_pipe)

    def loop_pipes(self):
        """check if x distance has moved since the last pipe placement, and add new pipes"""
        if self.distance_from_last_pipe >= self.pipe_spawning_dist or self.distance_from_last_pipe == 0:
            self.distance_from_last_pipe = 0
            self.add_pipes()

    def initiate_game(self):
        """starts the game"""
        self.game_started = True
        self.distance_from_last_pipe = 0

    def restart_game(self):
        self.game_ended = False
        self.game_started = False
        self.player.reset(self.player_starting_pos)
        self.score = 0
        self.previous_pipe_serial = 0
        self.current_pipe_serial = self.previous_pipe_serial

        for obstacle in self.obstacles:
            if type(obstacle) == PipeObstacle:
                obstacle.kill()

    def initiate_game_over_screen(self, events):  # add scoreboard instead of going to start screen
        if not self.game_ended:  # fire only once
            self.best_score = self.score if self.score > self.best_score else self.best_score
            self.scoreboard = self.scoreboard_bg.copy()
            self.final_score_txt = self.score_font.render(str(self.score), False, self.score_stat_colour)
            self.best_score_txt = self.score_font.render(str(self.best_score), False, self.score_stat_colour)

            self.scoreboard.blit(self.final_score_txt, self.final_score_txt_rect)
            self.scoreboard.blit(self.best_score_txt, self.best_score_txt_rect)
            self.game_over_title_rect = self.game_over_title.get_rect(
                center=(self.title_rect.centerx, 0 - self.game_over_title.get_height() / 2))
            self.scoreboard_rect.topleft = (self.width / 2 - self.scoreboard_rect.width / 2, self.height)

        self.game_ended = True
        self.player.disable_jumping = True

        if self.game_over_title_rect.centery < 150:
            self.game_over_title_rect.move_ip(0, 10)

        if self.scoreboard_rect.centery > 450:
            self.scoreboard_rect.move_ip(0, -20)
            self.restart_game_button.rect.topleft = (self.scoreboard_rect.x + self.rel_restart_button_pos[0],
                                                     self.scoreboard_rect.y + self.rel_restart_button_pos[1])

        self.restart_game_button.update(events)

        if self.restart_game_button.pressed:
            self.scoreboard = self.scoreboard_bg.copy()

            self.scoreboard.blit(self.final_score_txt, self.final_score_txt_rect)
            self.scoreboard.blit(self.best_score_txt, self.best_score_txt_rect)

        self.surface.blit(self.game_over_title, self.game_over_title_rect)
        self.surface.blit(self.scoreboard, self.scoreboard_rect)
        self.surface.blit(self.restart_game_button.image, self.restart_game_button.rect)

    @property
    def score(self):
        return self._score

    @score.setter
    def score(self, value):
        self._score = value
        self.score_text = self.score_font.render(str(self.score), False, self.score_text_colour).convert_alpha()


class Button(pygame.sprite.Sprite):
    """
    Class for managing a button

    :param image: The surface of the button
    :param action: A function that the button will execute when it is pressed
    """

    def __init__(self, image, action):
        self.image = image
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)
        self.action = action
        self.pressed = False
        self.pressed_down_distance = 5  # `x` pixels that button will move down when pressed

        super().__init__()

    def update(self, events):
        """check if mouse has been pressed over the button and call `self.action()`"""
        mouse_pos = pygame.mouse.get_pos()
        mouse_pos_in_mask = (mouse_pos[0] - self.rect.x, mouse_pos[1] - self.rect.y)

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # check if the mouse pos is inside the image mask
                if self.rect.collidepoint(mouse_pos) and self.mask.get_at(mouse_pos_in_mask):
                    self.pressed = True
                    self.rect.move_ip(0, self.pressed_down_distance)

            elif event.type == pygame.MOUSEBUTTONUP and self.pressed:
                self.pressed = False
                self.rect.move_ip(0, -self.pressed_down_distance)

                if self.rect.collidepoint(mouse_pos) and self.mask.get_at(mouse_pos_in_mask):
                    self.action()


if __name__ == "__main__":  # v = gt + vi
    # Using @property decorator
    print(pygame.font.match_font(""))
    for font in pygame.font.get_fonts():
        if "" in font:
            print(font)
