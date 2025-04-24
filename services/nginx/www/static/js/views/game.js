import { handleJwtToken } from './jwtValidator.js';
import { hasAccessToken } from '../utils/auth_management.js';

export async function renderGame() {
    const response = await fetch('static/html/game.html');
    const htmlContent = await response.text();
    return htmlContent;
}

export async function initGame() {


    // --- INITIALIZATION ---

    if (!hasAccessToken()) {
        window.sessionStorage.setItem("afterLoginRedirect", "#game");
        window.location.hash = "#login"
        return;
    }
    handleJwtToken();

    let pongSocket = new WebSocket(`wss://${window.location.host}/ws/game/pong/`);


    // --- DOM ELEMENTS ---

    const title = document.querySelector('.site-title');
    const canvas = document.getElementById('pong-canvas');
    const context = canvas.getContext('2d');
    const leftUsernameSpan = document.getElementById('left-username');
    const rightUsernameSpan = document.getElementById('right-username');
    const leftScoreSpan = document.getElementById('left-score');
    const rightScoreSpan = document.getElementById('right-score');
    const popup = document.getElementById('result-popup');


    // --- VARIABLES AND CONSTANTS ---

    

    const maxCanvasHeightToWindow = 0.5;
    const maxCanvasWidthToWindow = 0.5;

    let fieldHeightProportion;
    let fieldWidthProportion;
    let ballRadiusProportion;
    let paddleRadiusProportion;
    let paddleOffsetProportion;

    let fieldHeight;
    let fieldWidth;
    let ballRadius;
    let paddleRadius;
    let paddleOffset;

    let angleInRadians;
    let fps;

    let ball = { x: canvas.height / 2, y: canvas.height / 2 }
    let leftPaddleY;
    let rightPaddleY;
    let startCountdown;

    let tournamentId;

    let keys = {
        w: false,
        s: false,
        arrowUp: false,
        arrowDown: false,
    };

    let popupShown = false;


    // --- FUNCTIONS ---

    window.eventManager.addEventListener(document, 'keydown', (event) => {
        const keysToPrevent = ['ArrowUp', 'ArrowDown', 'w', 's'];
        if (keysToPrevent.includes(event.key)) {
            event.preventDefault();
        }
    
        if (event.key === 'w') {
            keys.w = true;
        } else if (event.key === 's') {
            keys.s = true;
        }
        if (event.key === 'ArrowUp') {
            keys.arrowUp = true;
        } else if (event.key === 'ArrowDown') {
            keys.arrowDown = true;
        }
    });

    window.drawEverything = function drawEverything() {
        context.fillStyle = 'black';
        context.fillRect(0, 0, canvas.width, canvas.height);

        context.shadowBlur = 15;
        context.shadowColor = '#16a085';

        context.fillStyle = '#1abc9c';
        context.beginPath();
        context.arc(-paddleOffset, leftPaddleY, paddleRadius * 0.96, 0, Math.PI * 2, true);
        context.fill();

        context.beginPath();
        context.arc(canvas.width + paddleOffset, rightPaddleY, paddleRadius * 0.96, 0, Math.PI * 2, true);
        context.fill();

        context.beginPath();
        context.arc(ball.x, ball.y, ballRadius, 0, Math.PI * 2, true);
        context.fill();

        context.shadowBlur = 0;
        context.shadowColor = 'transparent';
    }

    window.gameLoop = function gameLoop() {
        let keysPressed = [];

        if (keys.w) {
            keysPressed.push('w');
        } else if (keys.s) {
            keysPressed.push('s');
        }
        if (keys.arrowUp) {
            keysPressed.push('arrowUp');
        } else if (keys.arrowDown) {
            keysPressed.push('arrowDown');
        }

        if (keysPressed.length > 0 && pongSocket.readyState === WebSocket.OPEN) {
            pongSocket.send(JSON.stringify({
                type: 'paddle_move',
                keys: keysPressed,
            }));
        }

        setTimeout(gameLoop, 1000 / fps);
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

    window.showPopupPong = function showPopupPong(message) {
        popup.textContent = message;
        popup.style.display = "block";
        popupShown = true;
    }

    window.hidePopup = function hidePopup() {
        popup.style.display = "none";
        popupShown = false;
    }


    // --- EVENT LISTENERS ---

    pongSocket.onmessage = function (event) {
        const data = JSON.parse(event.data);

        if (data.type === 'game_state_update') {
            leftPaddleY = data.game_state.left.paddle_y * fieldHeight;
            rightPaddleY = data.game_state.right.paddle_y * fieldHeight;
            ball.x = data.game_state.ball.x * fieldHeight;
            ball.y = data.game_state.ball.y * fieldHeight;
            leftScoreSpan.innerText = data.game_state.left.score;
            rightScoreSpan.innerText = data.game_state.right.score;
            startCountdown = data.game_state.start_countdown;
            drawEverything();

            if (data.game_state.start_countdown !== 0) {
                window.showPopupPong(`Comenzando en ${startCountdown}`);
            }
            if (data.game_state.is_finished && !popupShown) {
                window.showPopupPong(`${data.game_state.winner_username} gana!`);
                setTimeout(() => {
                    if (tournamentId > 0) {
                        window.location.hash = `#tournament/room/${tournamentId}`;
                    } else {
                        window.location.hash = "#"
                    }
                }, 800);
            } else if (!data.game_state.is_finished && popupShown && startCountdown === 0) {
                hidePopup();
            }

        } else if (data.type === 'initial_information') {
            leftUsernameSpan.innerText = data.left_player_username;
            rightUsernameSpan.innerText = data.right_player_username;

            fieldHeightProportion = data.field_height;
            fieldWidthProportion = data.field_width;
            ballRadiusProportion = data.ball_radius;
            paddleRadiusProportion = data.paddle_radius;
            paddleOffsetProportion = data.paddle_offset;

            fieldHeight = fieldHeightProportion * maxCanvasHeightToWindow * window.innerHeight;
            fieldWidth = fieldWidthProportion * fieldHeight;
            if (fieldWidth > maxCanvasWidthToWindow * window.innerWidth) {
                fieldWidth = maxCanvasWidthToWindow * window.innerWidth;
                fieldHeight = fieldWidth / fieldWidthProportion;
            }

            ballRadius = ballRadiusProportion * fieldHeight;
            paddleOffset = paddleOffsetProportion * fieldHeight;
            paddleRadius = paddleRadiusProportion * fieldHeight;
            fps = data.fps;
            angleInRadians = data.paddle_edge_angle_radians;

            tournamentId = data.tournament_id;

            canvas.setAttribute('height', fieldHeight);
            canvas.setAttribute('width', fieldWidth);

            gameLoop();
        }

    };

    window.eventManager.addEventListener(document, 'keydown', (event) => {
        if (event.key === 'w') {
            keys.w = true;
        } else if (event.key === 's') {
            keys.s = true;
        }
        if (event.key === 'ArrowUp') {
            keys.arrowUp = true;
        } else if (event.key === 'ArrowDown') {
            keys.arrowDown = true;
        }
    });

    window.eventManager.addEventListener(document, 'keyup', (event) => {
        if (event.key === 'w') {
            keys.w = false;
        } else if (event.key === 's') {
            keys.s = false;
        }
        if (event.key === 'ArrowUp') {
            keys.arrowUp = false;
        } else if (event.key === 'ArrowDown') {
            keys.arrowDown = false;
        }
    });

    window.eventManager.addEventListener(window, 'blur', () => {
        keys.w = false;
        keys.s = false;
        keys.arrowUp = false;
        keys.arrowDown = false;
    });

    window.eventManager.addEventListener(window, 'resize', () => {
        fieldHeight = fieldHeightProportion * maxCanvasHeightToWindow * window.innerHeight;
        fieldWidth = fieldWidthProportion * fieldHeight;
        if (fieldWidth > maxCanvasWidthToWindow * window.innerWidth) {
            fieldWidth = maxCanvasWidthToWindow * window.innerWidth;
            fieldHeight = fieldWidth / fieldWidthProportion;
        }

        ballRadius = ballRadiusProportion * fieldHeight;
        paddleOffset = paddleOffsetProportion * fieldHeight;
        paddleRadius = paddleRadiusProportion * fieldHeight;

        canvas.setAttribute('height', fieldHeight);
        canvas.setAttribute('width', fieldWidth);
        drawEverything();
    })

    window.eventManager.addEventListener(title, 'mouseenter', () => {
        title.classList.add('glitch');
        title.style.transform = 'translateY(-5px)';
    });

    window.eventManager.addEventListener(title, 'mouseleave', () => {
        title.classList.remove('glitch');
        title.style.transform = 'translateY(0)';
    });

    window.onhashchange = () => {
        pongSocket.close();
    };

}
