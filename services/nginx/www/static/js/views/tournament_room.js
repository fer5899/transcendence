let socket = null;

export function renderTournamentRoom(tournamentId) {
    return `
        <div class="container">
            <h2>Sala del Torneo</h2>
            <p>ID del torneo: <span id="tournament-id">${tournamentId.id}</span></p>

            <!-- Lista dinámica de usuarios -->
            <div class="connected-users">
                <h3>Usuarios Conectados</h3>
                <ul id="user-list"></ul>
            </div>

            <!-- Árbol de clasificación -->
            <div class="tournament-tree">
                <div class="round round-1">
                    <div class="match" data-match="1">
                        <div class="player" data-player="1">jugador1dg</div>
                        <div class="player" data-player="2">jugador2dg</div>
                    </div>
                    <div class="match" data-match="2">
                        <div class="player" data-player="3">Jugador 3</div>
                        <div class="player" data-player="4">Jugador 4</div>
                    </div>
                    <div class="match" data-match="3">
                        <div class="player" data-player="5">Jugador 5</div>
                        <div class="player" data-player="6">Jugador 6</div>
                    </div>
                    <div class="match" data-match="4">
                        <div class="player" data-player="7">Jugador 7</div>
                        <div class="player" data-player="8">Jugador 8</div>
                    </div>
                </div>

                <div class="round round-2">
                    <div class="match" data-match="5">
                        <div class="player" data-player="9">Ganador 1</div>
                        <div class="player" data-player="10">Ganador 2</div>
                    </div>
                    <div class="match" data-match="6">
                        <div class="player" data-player="11">Ganador 3</div>
                        <div class="player" data-player="12">Ganador 4</div>
                    </div>
                </div>

                <div class="round final">
                    <div class="match" data-match="7">
                        <div class="player" data-player="13">Ganador 5</div>
                        <div class="player" data-player="14">Ganador 6</div>
                    </div>
                </div>

                <div class="champion">
                    <h3>Campeón</h3>
                    <div class="player" data-player="15">Pendiente...</div>
                </div>
            </div>
        </div>
    `;
}

export function initTournamentRoom(tournamentId) {
    if (socket === null) {
        socket = startTournamentWebSocket(tournamentId);
    }

    // simulateTournamentProgress();
}

function startTournamentWebSocket(tournamentId) {
    console.log('tournamentId>', tournamentId.id);
    const socket = new WebSocket(`wss://${window.location.host}/ws/room/${tournamentId.id}/`);

    socket.onopen = () => {
        console.log(`Conexión WebSocket para el torneo ${tournamentId.id} abierta`);
    };

    socket.onmessage = function (event) {
        const data = JSON.parse(event.data);
        console.log("Mensaje WebSocket del torneo:", data);

        if (data.type === "user_list" ) {
            updateUserList(data.user_list);
        }
        if (data.type === "start_tournament") {
            start_tournament();
        }
        if (data.type === "game_end") {
            update_tournament_tree(data);
        }
        //HERE WE CAN ADD MORE CONDITIONS TO UPDATE THE TOURNAMENT TREE
        //OR TO START THE TOURNAMENT.
    };

    socket.onclose = function (event) {
        console.log(`Conexión WebSocket para el torneo ${tournamentId.id} cerrada`, event);
    };

    socket.onerror = function (error) {
        console.error(`Error en WebSocket para el torneo ${tournamentId.id}:`, error);
    };

    return socket;
}



function updateUserList(userList) {
    const userListContainer = document.getElementById("user-list");

    if (!userListContainer) {
        console.error("Elemento de lista de usuarios no encontrado");
        return;
    }

    userListContainer.innerHTML = "";

    userList.forEach((user) => {
        const userElement = document.createElement("li");
        const [name, id] = user.split(":"); 
        userElement.textContent = name;
        userListContainer.appendChild(userElement);
    });
}

/*
    This function updates the tournament tree with the winner and loser of a match.
    It also determines the next match where the winner will play.
    (check at the back-end how the data is sent to the front-end!!)
    @param {Object} data - The data of the match result:
        - {number} match_id - The ID of the match
        - {string} winner - The name of the winner
        - {string} loser - The name of the loser
*/
function update_tournament_tree(data) {
    const { match_id, winner, loser } = data;
    console.log("updating tournament tree with:", data);
    // Encontrar el partido actual
    const currentMatch = document.querySelector(`.match[data-match="${match_id}"]`);
    if (!currentMatch) {
        console.error(`No se encontró el partido con ID ${match_id}`);
        return;
    }

    // Marcar al ganador y perdedor
    const players = currentMatch.querySelectorAll(".player");
    players.forEach(player => {
        if (player.textContent === winner) {
            player.classList.add("winner");
        } else if (player.textContent === loser) {
            player.classList.add("loser");
        }
    });

    // Determinar el siguiente partido
    const nextMatchId = Math.floor((match_id - 1) / 2) + 5;
    const nextMatch = document.querySelector(`.match[data-match="${nextMatchId}"]`);
    
    if (nextMatch) {
        // Encontrar un espacio disponible en el siguiente partido
        const nextPlayers = nextMatch.querySelectorAll(".player");
        for (let i = 0; i < nextPlayers.length; i++) {
            if (nextPlayers[i].textContent.includes("Ganador")) {
                nextPlayers[i].textContent = winner;
                break;
            }
        }
    }

    // Actualizar campeón si es la final
    if (match_id === 7) {
        const champion = document.querySelector(".champion .player");
        if (champion) {
            champion.textContent = winner;
        }
    }
}


function simulateTournamentProgress() {
    const matches = document.querySelectorAll(".match");

    matches.forEach((match, index) => {
        const players = match.querySelectorAll(".player");

        const winnerIndex = Math.floor(Math.random() * 2);
        const loserIndex = winnerIndex === 0 ? 1 : 0;

        players[winnerIndex].classList.add("winner");
        players[loserIndex].classList.add("loser");

        const nextMatch = document.querySelector(`.match[data-match="${Math.floor(index / 2) + 5}"]`);
        if (nextMatch) {
            const nextPlayerSlot = nextMatch.querySelector(`.player[data-player="${index + 9}"]`);
            if (nextPlayerSlot) {
                nextPlayerSlot.textContent = players[winnerIndex].textContent;
            }
        }
    });

    const finalWinner = document.querySelector(".final .player.winner");
    if (finalWinner) {
        const champion = document.querySelector(".champion .player");
        champion.textContent = finalWinner.textContent;
    }
}

function start_tournament() {
    alert("El torneo ha comenzado!");
}
