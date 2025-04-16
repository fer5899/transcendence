ROOT = $(shell pwd)

all: up

build:
	docker compose -f ./docker-compose.yml build

up: build
	docker compose -f ./docker-compose.yml up

stop:
	docker compose -f ./docker-compose.yml stop

start:
	docker compose -f ./docker-compose.yml start

down:
	docker compose -f ./docker-compose.yml down

fclean:
	docker compose -f ./docker-compose.yml down -v --rmi all --remove-orphans
	docker system prune -a --volumes -f
	rm -rf $(DATA)

logs:
	
recompose: down up

re: fclean up

.PHONY: build up all stop start down fclean re
