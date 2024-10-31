ROOT = $(shell pwd)

all: up

build:
	docker compose -f ./srcs/docker-compose.yml build

up: build
	docker compose -f ./srcs/docker-compose.yml up -d

stop:
	docker compose -f ./srcs/docker-compose.yml stop

start:
	docker compose -f ./srcs/docker-compose.yml start

down:
	docker compose -f ./srcs/docker-compose.yml down

fclean:
	docker compose -f ./srcs/docker-compose.yml down -v --rmi all --remove-orphans
	docker system prune -a --volumes -f
	rm -rf $(DATA)

logs:
	
recompose: down up

re: fclean up


# GAME SERVICE ONLY

game-build:
	docker compose -f ./srcs/docker-compose-game.yml build

game-up: game-build
	docker compose -f ./srcs/docker-compose-game.yml up -d

game-stop:
	docker compose -f ./srcs/docker-compose-game.yml stop

game-start:
	docker compose -f ./srcs/docker-compose-game.yml start

game-down:
	docker compose -f ./srcs/docker-compose-game.yml down

game-fclean:
	docker compose -f ./srcs/docker-compose-game.yml down -v --rmi all --remove-orphans
	docker system prune -a --volumes -f
	
game-recompose: game-down game-up

game-re: game-fclean game-up
	

.PHONY: build up all stop start down fclean re
