import pygame
import sprites

SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 900
running = True

pygame.init()

clock = pygame.time.Clock()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

ADD_PIPE = pygame.event.Event(pygame.event.custom_type())

pygame.display.set_caption("flappy bird")
pygame.key.set_repeat(500, 50)

player = sprites.Player()
game = sprites.GameManager(player, SCREEN_WIDTH, SCREEN_HEIGHT)

game.setup_game()

max_fps = 120

while running:
    events = pygame.event.get()

    for event in events:
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_f:
                pygame.event.post(ADD_PIPE)

        if event.type == ADD_PIPE.type and game.game_started:
            game.add_pipes()

    game.update(events)
    screen.blit(game.surface, game.rect)

    clock.tick(max_fps)
    game.game_speed = round(game.game_fps / min(clock.get_fps(), game.game_fps) if clock.get_fps() > 0
                            else game.game_fps) * game.static_game_speed
    pygame.display.flip()
    # print(round(clock.get_fps()), game.game_speed, game.static_game_speed)

