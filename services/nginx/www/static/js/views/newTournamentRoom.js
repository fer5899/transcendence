// static/js/views/new_tournament_room.js

import EventListenerManager from '../utils/eventListenerManager.js';

export async function renderNewTournamentRoom() {
    const response = await fetch('static/html/new_tournament_room.html');
    const htmlContent = await response.text();
    return htmlContent;
}

let room_socket = null;
let isHistoryBack = false;
export function initNewTournamentRoom(tournamentId) {
    if (room_socket === null) {
        room_socket = startTournamentWebSocket(tournamentId);
    }
    const startButton = document.getElementById("start-tournament-btn");
    let tournamentName = sessionStorage.getItem("tournamentName") 
    if (startButton) {
        startButton.addEventListener("click", () => {
            if (startButton.disabled) return;
            startButton.disabled = true;
            sendWebSocketMessage("start_tournament", { tournament_id: tournamentId.id });
        });
    }
    if (tournamentName) {
        const tournamentNameElement = document.getElementById("text-to-copy");
        tournamentNameElement.textContent = tournamentName;
    }

    restoreTournamentTree();
    // --- EVENT LISTENERS ---

    const title = document.querySelector('.site-title');
    window.eventManager.addEventListener(title, 'mouseenter', () => {
        title.classList.add('glitch');
        title.style.transform = 'translateY(-5px)';
    });

    window.eventManager.addEventListener(title, 'mouseleave', () => {
        title.classList.remove('glitch');
        title.style.transform = 'translateY(0)';
    });

    window.exitGame = function exitGame() {
        window.location.hash = '#';
    }

    // --- INITIALIZATION ---

    return () => window.eventManager.removeAllEventListeners();
}

//SOCKET MANAGEMENT
/**
 * This function checks if the username is in the new round.
 * If it is, it redirects the user to the game #rock-paper-scissors.
 * @param {*} data 
 */
function checkNewRound(new_round, myUser) {
    const isUserInRound = new_round.some(match => {
        const left = match.players.left.username;
        const right = match.players.right.username;
        return left === myUser || right === myUser;
    });
    if (isUserInRound) {
        return true;
    } else {
        return false;
    }
}

function startTournamentWebSocket(tournamentId) {
    console.log('tournamentId>', tournamentId.id);
    const room_socket = new WebSocket(`wss://${window.location.host}/ws/room/${tournamentId.id}/`);

    room_socket.onopen = () => {
        console.log(`Conexión WebSocket para el torneo ${tournamentId.id} abierta`);
    };

    room_socket.onmessage = function (event) {
        const data = JSON.parse(event.data);
        console.log("Mensaje WebSocket del torneo:", data);
        
        if (data.type === "user_list" ) {
            updateUserList(data.user_list);
        }
        if (data.type === "start_tournament") {
            start_tournament(data);
            setTimeout(() => {
                window.location.hash = '#rock-paper-scissors'; 
            }, 1500);
        }
        if (data.type === "game_end") {
            setTimeout(() => {
                update_tournament_tree(data);
            }, 500);
        }
        if (data.type === "new_round") {
                //check if my user is in the new round so i can be redirected to the game
                console.log("%cNew round data:", "color: blue", data);
                const roundId = Number(data.round_id) - 1;
                console.log("%cMy ROUND STARTING:", "color: red", roundId);
                console.log("%cROUND IS:", "color: green", data.new_round);
                const myUser = data.username;
                //check if myUser is in data.new_round
                if  (checkNewRound(data.new_round, myUser)) {
                    console.log("%cMy user is in the new round:", "color: green", myUser);
                    setTimeout(() => {
                        window.location.hash = '#rock-paper-scissors';
                    }
                    , 4000);
                }
        }
        //HERE WE CAN ADD MORE CONDITIONS TO UPDATE THE TOURNAMENT TREE
        //OR TO START THE TOURNAMENT.
    };

    room_socket.onclose = function (event) {
        console.log(`Conexión WebSocket para el torneo ${tournamentId.id} cerrada`, event);
    };

    room_socket.onerror = function (error) {
        console.error(`Error en WebSocket para el torneo ${tournamentId.id}:`, error);
    };

    return room_socket;
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

    sessionStorage.setItem("user_list", JSON.stringify(userList));
}

function sendWebSocketMessage(type, data) {
    if (room_socket && room_socket.readyState === WebSocket.OPEN) {
        console.log("Enviando mensaje WebSocket:", { type, ...data });
        room_socket.send(JSON.stringify({ type, ...data }));
    } else {
        console.error("WebSocket no está conectado.");
    }
}

function start_tournament(data) {
    showPopup("Torneo Iniciado! prepárate para jugar!", 4000);
    
    
    const parsedTournamentTree = {};
    for (const key in data.tournament_tree) {
        parsedTournamentTree[key] = JSON.parse(data.tournament_tree[key]);
    }

    console.log("Árbol del torneo:", parsedTournamentTree);

    sessionStorage.setItem("tournament_tree", JSON.stringify(data.tournament_tree));

    parsedTournamentTree.round_1.forEach((match) => {
        const matchElement = document.querySelector(`.match[data-match="${match.tree_id}"]`);
        if (matchElement) {
            const players = matchElement.querySelectorAll(".player");
            if (players.length >= 2) {
                players[0].textContent = match.players.left.username;
                players[1].textContent = match.players.right.username;
            }
        }
    });
}


function update_tournament_tree(data) {

    const { match_id, winner, loser } = data;
    console.log("Updating tournament tree:", data);

    const currentMatch = document.querySelectorAll(`.match[data-match="${match_id}"]`);
    if (!currentMatch) {
        console.error(`No se encontró el partido con ID ${match_id}`);
        return;
    }
    console.log("%cCurrent Match:", "color:blue", currentMatch);
    console.log("%cWinner:", "color:green", winner);
    console.log("%cLoser:", "color:red", loser);
    console.log("%cMatch ID:", "color:purple", match_id);

    let isMaquina = false;
    currentMatch.forEach((match) => {
        const players = match.querySelectorAll(".player");
        players.forEach(player => {
            if (winner == loser && isMaquina == false) {
                player.classList.add("winner");
                isMaquina = true;
            }
            else if (loser == winner && isMaquina == true) {
                player.classList.add("loser");
                isMaquina = false;
            }
            else if (player.textContent === winner) {
                player.classList.add("winner");
            } else if (player.textContent === loser) {
                player.classList.add("loser");
            }
        });
    }
    );
   
    const nextMatch = getNextMatch(match_id);
    if (nextMatch) {
        updateNextMatch(nextMatch, winner, match_id);
    }

   
    if (isFinalMatch(match_id)) {
        updateChampion(winner);
    }
    sessionStorage.setItem("tournament_tree", JSON.stringify(data.tournament_tree));
}

/**
 * 
 * @param {*} currentMatchId 
 * @returns Returns the next match element of the html tree.
 */
function getNextMatch(currentMatchId) {
    const nextMatchId = Math.floor((currentMatchId - 1) / 2) + 5;
    return document.querySelector(`.match[data-match="${nextMatchId}"]`);
}


function updateNextMatch(nextMatch, winner, currentMatchId) {
    const targetPlayer = document.querySelector(`.player[data-player="winner-${currentMatchId}"]`);
    if (targetPlayer) {
        targetPlayer.textContent = winner;  
    } else {
        console.error(`No se encontró un jugador con data-player="winner-${currentMatchId}" en el siguiente partido.`);
    }
}

function isFinalMatch(matchId) {
    return Number(matchId) === 7;
}

function updateChampion(winner) {
    console.log("El campeón es:", winner);
    const champion = document.querySelector(".champion .player");
    const trophyIcon = document.querySelector('.new-tournament-room .screen .icon');
    if (champion) {
        champion.classList.add("championship");
        champion.textContent = winner;

        if (trophyIcon) {
            trophyIcon.style.color = 'gold';  
            trophyIcon.style.textShadow = '0 0 10px gold'; 
        }

    }
}

/**
 * * This function is called when the user navigates back in history.
 * It checks if the URL contains '#tournament' or '#game' or '#rock-paper-scissors'.
 * If not, it closes the WebSocket connection and clears the tournament tree.
 */
window.addEventListener('hashchange', function(event) {
    // Verificar si la URL contiene '#tournament' o '#game'
    console.log('URL:', window.location.hash);
    if (!window.location.hash.includes('tournament/room') && !window.location.hash.includes('game') && !window.location.hash.includes('rock-paper-scissors')) {
        closeWebSocket();
        clearTournamentTree(); 
    }
});

function closeWebSocket() {
    if (room_socket) {
        console.log('Cerrando WebSocket de sala de torneo...');
        room_socket.close();  
        room_socket = null;  
    }
}

function clearTournamentTree() {
    sessionStorage.removeItem('tournament_tree');  // Borra el árbol del torneo guardado en sessionStorage
    console.log('Datos del torneo eliminados de sessionStorage');
}


function restoreTournamentTree() {
    
    const savedTree = sessionStorage.getItem("tournament_tree");
    const userList = sessionStorage.getItem("user_list");

    if (userList) {
        updateUserList(JSON.parse(userList));
    }
    if (savedTree) {
        const parsedTournamentTree = {};
        const rawTree = JSON.parse(savedTree);
        
        for (const key in rawTree) {
            parsedTournamentTree[key] = JSON.parse(rawTree[key]);
        }
        
        console.log("Restaurando árbol desde localStorage:", parsedTournamentTree);
        for (const roundKey in parsedTournamentTree) {
            const roundMatches = parsedTournamentTree[roundKey];
        
            roundMatches.forEach((match) => {
                const { tree_id, players, winner, loser } = match;
                const treeIdStr = String(tree_id);
                const participants = Object.values(players).filter(p => p && p.username);
                
                
                if (treeIdStr === "7") {
                    let isMaquina = false;
                    participants.forEach((participant) => {
                        const username = participant.username;
                        let isWinner = false;
                        let isLoser = false;
                        let originTree = null;
                        
                        if (match.status != "pending") {
                            isWinner = username === winner.username;
                            isLoser = username === loser.username;
                            console.log("%cisMaquina:", "color:blue", isMaquina);
                        }
                        
                        const originTreeId = Object.keys(players).find(
                            key => players[key]?.username === username
                        );

                        if (originTreeId === "left") {
                            originTree = "5";
                        } else if (originTreeId === "right") {
                            originTree = "6";
                        }
                        console.log("%cisMaquina:", "color:red", isMaquina);

                        if (isWinner && isLoser) {
                            
                            if(isMaquina == true) {
                                originTree = "6";
                            }else if (isMaquina == false) {
                                originTree = "5";
                            }
                        }   
        
                        if (originTree) {
                            const playerSlot = document.querySelector(`.player[data-player="winner-${originTree}"]`);
                            if (playerSlot) {
                                playerSlot.textContent = username;
                                playerSlot.classList.remove("winner", "loser");
                                if (isWinner == isLoser && isMaquina == false && isLoser == true) { 
                                    playerSlot.classList.add("winner");
                                    isMaquina = true;
                                }
                                else if (isLoser) playerSlot.classList.add("loser");
                                else if (isWinner) playerSlot.classList.add("winner");
                            }
                        }
                        
                        if (isWinner) {
                            const championDiv = document.querySelector('.player[data-player="champion"]');
                            if (championDiv) {
                                championDiv.textContent = username;
                                championDiv.classList.add("championship");
                            }
                            const trophyIcon = document.querySelector('.new-tournament-room .screen .icon');
                            if (trophyIcon) {
                                trophyIcon.style.color = 'gold';  
                                trophyIcon.style.textShadow = '0 0 10px gold'; 
                            }
                        }
                    });
        
                    return; 
                }
                
                const matchElements = document.querySelectorAll(`.match[data-match="${treeIdStr}"]`);
        
                matchElements.forEach((matchElement) => {
                    const playerDivs = Array.from(matchElement.querySelectorAll(".player"));
                    
                    playerDivs.forEach(div => div.classList.remove("winner", "loser"));
        
                    let isMaquina = false;
                    participants.forEach((participant) => {
                        const username = participant.username;
                        const availableDiv = playerDivs.find(div => {
                            const classList = Array.from(div.classList);
                            return (
                                classList.includes("player") 
                            );
                        });
                        //checkpoint
                        if (availableDiv) {
                            availableDiv.textContent = username;

                            if ( match.status != "pending" && winner.username === loser.username && isMaquina == false ) {
                                availableDiv.classList.add("winner");
                                isMaquina = true;
                                updateNextMatch(matchElement, winner.username, treeIdStr);
                            }
                            else if  (match.status != "pending" && winner.username === loser.username && isMaquina == true ) {
                                availableDiv.classList.add("loser");
                                isMaquina = false;
                                updateNextMatch(matchElement, winner.username, treeIdStr);                                
                            }
                            else if (winner) {
                                if (username === winner.username) availableDiv.classList.add("winner");
                                else if (username === loser.username) availableDiv.classList.add("loser");
                                updateNextMatch(matchElement, winner.username, treeIdStr);
                            }
                             
                            const idx = playerDivs.indexOf(availableDiv);
                            if (idx > -1) playerDivs.splice(idx, 1);
                        }
                    });
                });
            });
        }
        
    }
}
