// static/js/views/tournaments_list.js

import { handleJwtToken } from './jwtValidator.js';

export async function renderTournamentsList() {
    const response = await fetch('static/html/tournaments_list.html');
    const htmlContent = await response.text();
    return htmlContent;
}

let global_socket = null;
export function initTournamentsList() {
      
    // --- DOM ELEMENTS ---
    
    
    const gameLists = document.querySelectorAll('.game-list');
    const title = document.querySelector('.site-title');
    let availableContainer = document.getElementById('available-games');
    
    // --- FUNCTIONS ---

    /**
     * Thisfunction sends a POST request to create a tournament. 
     * if the tournament is created successfully, it shows a success message.
     * The backend will send a message to the WebSocket to update the tournament list.
     * @param {} event 
     */
    async function createTournament(event) {
        event.preventDefault();
    
        const tournamentName = document.getElementById("tournament-name").value;
    
        if (tournamentName) {
            try {
                await handleJwtToken();
                const response = await fetch('/api/tournament/create', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ name: tournamentName }),
                });
    
                if (response.ok) {
                    window.showPopup("Torneo creado exitosamente!", 2000);
                } else {
                    const errorData = await response.json();
                    console.warn("Error creating tournament:", errorData);
                    window.showPopup("Error al crear el torneo, intenta con otro nombre.", 2000);
                }
            } catch (error) {
                window.showPopup("Error de conexión. Inténtelo más tarde", 2000);
            }
        }
    }

    async function loadTournaments() {
        availableContainer.innerHTML = "";

        try {
            await handleJwtToken();
            const [tournamentResponse, playerCountsResponse] = await Promise.all([
                fetch('/api/tournament/list'),
                fetch('/api/tournament/player_counts')
            ]);

            if (!tournamentResponse.ok || !playerCountsResponse.ok) {
                window.showPopup("Error al cargar los torneos, inténtalo más tarde", 3000);
                return;
            }

            const tournaments = await tournamentResponse.json();
            const playerCounts = await playerCountsResponse.json();

            tournaments.forEach(tournament => {
                const gameItem = createGameItem({
                
                    id: tournament.id,
                    name: tournament.name,
                    date: tournament.created_at,
                    users: playerCounts[tournament.id] || 0
                }, 'available');
                const joinButton = gameItem.querySelector('.btn');
                joinButton.addEventListener('click', async (e) => {
                    const button = e.currentTarget;
                    if (button.disabled) return;
                    button.disabled = true;
                    await joinTournament(tournament.id, tournament.name);
                });
                
                availableContainer.appendChild(gameItem);
            });

            if (tournaments.length === 0) {
                document.getElementById('no-tournaments').style.display = 'block';
            } else {
                document.getElementById('no-tournaments').style.display = 'none';
            }
            

            if (global_socket === null) {
                global_socket = startGlobalWebSocket();
            }
        } catch (error) {
            window.showPopup("Error de conexión. Inténtelo más tarde", 2000);
        }
    }

    window.createGameItem = function createGameItem(game, type) {
        const gameItem = document.createElement('div');
        gameItem.classList.add('game-item');

        gameItem.innerHTML = `
            <div class="game-info" id="tournament-${game.id}">
                <div class="game-name">${game.name}</div>
                <div class="badge game-meta">Usuarios conectados: ${game.users}</div>
                <div class="game-meta">Fecha de creación: ${game.date}</div>
            </div>
            <button class="btn">${type === 'available' ? 'Unirse' : 'Visualizar'}</button>
        `;
        return gameItem;
    }

    window.displayGames = function displayGames() {
        const availableContainer = document.getElementById('available-games');

        availableGames.forEach(game => {
            const gameItem = createGameItem(game, 'available');
            availableContainer.appendChild(gameItem);
        });

    }

    async function joinTournament(tournamentId, tournamentName) {
        try {
            await handleJwtToken();
            const response = await fetch(`/api/tournament/${tournamentId}/join`, {
                method: 'POST',
            });

            if (response.ok) {
                window.showPopup(`Te has unido al torneo ${tournamentName}`, 3000);
                sessionStorage.setItem("tournamentName", tournamentName);
                setTimeout(() => {
                    location.hash = `tournament/room/${tournamentId}`;
                }, 700);
            } else {
                window.showPopup(`Error al unirse al torneo ${tournamentName}`, 3000);
            }
        } catch (error) {;
            window.showPopup("Error de conexión.No se pudo unir al torneo", 3000);
        }
    }

    function startGlobalWebSocket() {
        handleJwtToken().then(() => {
            const ws = new WebSocket(`wss://${window.location.host}/ws/global_tournament_counter/`);
            if (!ws) {
                window.showPopup("Error de conexión, inténtelo más tarde", 2000);
                return;
            }
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                const tournament = document.querySelector(`#tournament-${data.tournament_id}`);
                
                if (data.type == "user_count_update") {
                    if (tournament) {
                        const userCountContainer = tournament.querySelector('.badge');
                        if (userCountContainer) {
                            userCountContainer.textContent = `Usuarios conectados: ${data.user_count}`;
                        }
                    }
                    
                }
                else if (data.type == "tournament_created") {
                    const newTournament = {
                        id: data.tournament_id,
                        name: data.tournament_name,
                        date: data.created_at,
                        users: 0
                    };
                    const gameItem = createGameItem(newTournament, 'available');
                    const joinButton = gameItem.querySelector('.btn');
                    joinButton.addEventListener('click', async (e) => {
                        const button = e.currentTarget;
                        if (button.disabled) return;
                        button.disabled = true;
                        await joinTournament(newTournament.id, newTournament.name);
                    });
                    gameItem.classList.add('animate-in');

                    let listContainer = document.getElementById('available-games');
                    listContainer.appendChild(gameItem);
                    
                    let notournament = document.getElementById('no-tournaments').style.display = 'none';
                    
                }
            };

            ws.onclose = () => window.showPopup("Hasta pronto!", 5000);
            ws.onerror = (error) => {
                window.showPopup("Error de conexión, inténtelo más tarde", 2000);
            };
            return ws;
        });
    }

    window.toggleFullscreen = function toggleFullscreen() {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen();
        } else {
            if (document.exitFullscreen) {
                document.exitFullscreen();
            }
        }
    }


    // --- EVENT LISTENERS ---

    gameLists.forEach(gameList => {
        let isMouseDown = false;
        let startX;
        let scrollLeft;

        window.eventManager.addEventListener(gameList, 'mousedown', (e) => {
            isMouseDown = true;
            startX = e.pageX - gameList.offsetLeft;
            scrollLeft = gameList.scrollLeft;
            gameList.style.cursor = 'grabbing';
        });

        window.eventManager.addEventListener(gameList, 'mouseleave', () => {
            isMouseDown = false;
            gameList.style.cursor = 'grab';
        });

        window.eventManager.addEventListener(gameList, 'mouseup', () => {
            isMouseDown = false;
            gameList.style.cursor = 'grab';
        });

        window.eventManager.addEventListener(gameList, 'mousemove', (e) => {
            if (!isMouseDown) return;
            e.preventDefault();
            const x = e.pageX - gameList.offsetLeft;
            const walk = (x - startX) * 3; // Controlar la velocidad del desplazamiento
            gameList.scrollLeft = scrollLeft - walk;
        });
    });

    window.eventManager.addEventListener(title, 'mouseenter', () => {
        title.classList.add('glitch');
        title.style.transform = 'translateY(-5px)';
    });

    window.eventManager.addEventListener(title, 'mouseleave', () => {
        title.classList.remove('glitch');
        title.style.transform = 'translateY(0)';
    });

    // --- INITIALIZATION ---
    loadTournaments();
    const createForm = document.getElementById("create-tournament-form");
    createForm.addEventListener("submit", createTournament);
    // displayGames();
}


