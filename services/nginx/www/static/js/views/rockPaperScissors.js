import { handleJwtToken } from './jwtValidator.js';
import { hasAccessToken } from '../utils/auth_management.js';

export async function renderRockPaperScissors() {
    const response = await fetch('static/html/rock_paper_scissors.html');
    const htmlContent = await response.text();
    return htmlContent;
}

export async function initRockPaperScissors() {

    // --- INITIALIZATION ---

    if (!hasAccessToken()) {
        window.sessionStorage.setItem("afterLoginRedirect", "#rock-paper-scissors");
        window.location.hash = "#login"
        return;
    }
    handleJwtToken();

    let rpsSocket = new WebSocket(`wss://${window.location.host}/ws/game/rock-paper-scissors/`);


    // --- VARIABLES AND CONSTANTS ---

    
    let leftPlayer = { id: null, username: null };
    let rightPlayer = { id: null, username: null };
    let requestedChoices = { leftPlayer: null, rightPlayer: null };
    let gameFinished = false;
    let popupShown = false;


    // --- DOM ELEMENTS ---

    const title = document.querySelector('.site-title');
    const timerValue = document.querySelector('#timer span');
    const leftPlayerUsername = document.querySelector('#leftPlayer .username');
    const rightPlayerUsername = document.querySelector('#rightPlayer .username');
    const popup = document.getElementById("result-popup");

    // --- FUNCTIONS ---

    window.choose = function choose(option, player) {
        requestedChoices[`${player}Player`] = option;
        if (requestedChoices.leftPlayer && requestedChoices.rightPlayer) {
            rpsSocket.send(JSON.stringify({
                type: 'choice_change',
                choices: requestedChoices,
            }));
        }
    }

    window.showPopupRPS = function showPopupRPS(message) {
        popup.textContent = message;
        popup.style.display = "block";
        popupShown = true;
    }

    window.hidePopup = function hidePopup() {
        popup.style.display = "none";
        popupShown = false;
    }

    window.freezeChoice = function freezeChoice(option, player) {
        document.querySelectorAll(`#${player}Player .choices button`).forEach(button => {
            if (button.getAttribute("data-choice") === option) {
                button.style.backgroundColor = "var(--primary-color)";
            } else {
                button.style.backgroundColor = "var(--btn-bg-color)";
            }
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

    rpsSocket.onmessage = function (event) {
        const data = JSON.parse(event.data);
        if (data.type === 'game_state_update') {
            timerValue.textContent = data.game_state.time_left;
            gameFinished = data.game_state.is_finished;
            freezeChoice(data.game_state.left_choice, 'left');
            freezeChoice(data.game_state.right_choice, 'right');

            if (data.game_state.is_finished && !popupShown) {
                if (data.game_state.winner_username !== "") {
                    window.showPopupRPS(`${data.game_state.winner_username} gana!`);
                    setTimeout(() => { window.location.hash = "#game" }, 2000);
                } else {
                    window.showPopupRPS("Empate!");
                }
            } else if (!data.game_state.is_finished && popupShown) {
                hidePopup();
            }

        } else if (data.type === 'initial_information') {
            timerValue.textContent = data.timer_start;
            leftPlayer.id = data.left_player_id;
            leftPlayer.username = data.left_player_username;
            requestedChoices.leftPlayer = data.left_player_choice;
            rightPlayer.id = data.right_player_id;
            rightPlayer.username = data.right_player_username;
            requestedChoices.rightPlayer = data.right_player_choice;
            leftPlayerUsername.textContent = data.left_player_username;
            rightPlayerUsername.textContent = data.right_player_username;
            freezeChoice(data.left_player_choice, 'left');
            freezeChoice(data.right_player_choice, 'right');
        } else if (data.type === 'error') {
            rpsSocket.close();
            window.showPopupRPS("Error de conexión", 2000);
            setTimeout(() => {
                window.location.hash = "#";
            }, 1000);
        }

    };

    window.eventManager.addEventListener(title, 'mouseenter', () => {
        title.classList.add('glitch');
        title.style.transform = 'translateY(-5px)';
    });

    window.eventManager.addEventListener(title, 'mouseleave', () => {
        title.classList.remove('glitch');
        title.style.transform = 'translateY(0)';
    });

    window.eventManager.addEventListener(document, 'keydown', (event) => {
        if (gameFinished) return;
        if (event.key === 'a') {
            choose('rock', 'left');
        }
        if (event.key === 's') {
            choose('paper', 'left');
        }
        if (event.key === 'd') {
            choose('scissors', 'left');
        }
        if (event.key === 'ArrowLeft') {
            choose('rock', 'right');
        }
        if (event.key === 'ArrowDown') {
            choose('paper', 'right');
        }
        if (event.key === 'ArrowRight') {
            choose('scissors', 'right');
        }
    });

    window.onhashchange = () => {
        rpsSocket.close();
    };
}



