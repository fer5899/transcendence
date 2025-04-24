// static/js/views/home.js
import { showPicture, updateUsername, updatePassword, updatePicture, uploadImage } from '../utils/settings.js';
import { addFriend, removeFriend, handleButtonFriend, goToPlayerProfile, getDataUser } from '../utils/profile.js';
import { checkActiveGame } from '../utils/autoReconnect.js';
import { hasAccessToken } from '../utils/auth_management.js';
import { handleJwtToken } from './jwtValidator.js';
import { initLoginSocket } from './login.js';
import { getCookieValue } from '../utils/jwtUtils.js';

export async function renderHome() {
    const response = await fetch('static/html/home.html');
    
    const htmlContent = await response.text();
    return htmlContent;
}

export async function initHome() {

    // --- VARIABLES AND CONSTANTS ---

    const totalCards = 4;
    const angleStep = 360 / totalCards;
    let currentAngle = 0;
    let isDragging = false;
    let startX = 0;

    let players = [
        { username: "javiersa", avatar: "../../media/2.gif" },
        { username: "f-gomez", avatar: "../../media/3.gif" },
        { username: "vcered", avatar: "../../media/4.gif" },
        { username: "dgarizard", avatar: "../../media/5.gif" },
        { username: "messi", avatar: "../../media/1.gif" },
        { username: "cristiano", avatar: "../../media/3.gif" },
        { username: "neymar123", avatar: "../../media/2.gif" },
        { username: "lewandosk", avatar: "../../media/5.gif" },
        { username: "javiersa", avatar: "../../media/2.gif" },
        { username: "f-gomez", avatar: "../../media/3.gif" },
        { username: "vcered", avatar: "../../media/4.gif" },
        { username: "dgarizard", avatar: "../../media/5.gif" },
        { username: "messi", avatar: "../../media/1.gif" },
        { username: "cristiano", avatar: "../../media/3.gif" },
        { username: "neymar123", avatar: "../../media/2.gif" },
        { username: "lewandosk", avatar: "../../media/5.gif" },
    ];

    // --- DOM ELEMENTS ---

    const carousel = document.getElementById("carousel");
    const title = document.querySelector('.site-title');
    const tabButtons = document.querySelectorAll('.tab-btn');
    const histories = document.querySelectorAll('.history');
    const profilePopup = document.getElementById('profilePopup');
    const settingsPopup = document.getElementById('settingsPopup');
    const settingsCurrentUsername = document.getElementById("current-username");
    const homeDiv = document.getElementsByClassName('home')[0];

    const profilePongGamesPlayedElement = document.getElementById("pong-played");
    const profilePongGamesWonElement = document.getElementById("pong-won");
    const profileRpsGamesPlayedElement = document.getElementById("rps-played");
    const profileRpsGamesWonElement = document.getElementById("rps-won");
    const profileTournamentsPlayedElement = document.getElementById("tournaments-played");
    const profileTournamentsWonElement = document.getElementById("tournaments-won");

    const profileTournamentHistoryElement = document.getElementById("tournament");
    const profileOnlineHistoryElement = document.getElementById("online");
    const profileLocalHistoryElement = document.getElementById("local");

    // --- FUNCTIONS ---

    window.toggleFullscreen = function toggleFullscreen() {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen();
        } else {
            if (document.exitFullscreen) {
                document.exitFullscreen();
            }
        }
    }

    window.toggleMenu = function toggleMenu(event) {
        event.stopPropagation();
        const dropdownMenu = document.getElementById("dropdownMenu");
        dropdownMenu.style.display = dropdownMenu.style.display === "block" ? "none" : "block";
    }

    window.buttonHold = function buttonHold(button, gameType) {
        button.style.boxShadow = `0 0 30px var(--hover-shadow-color)`;
        button.innerText = `${gameType}`;
    }

    window.buttonRelease = function buttonRelease(button, gameType) {
        button.style.boxShadow = `0 0 20px var(--shadow-color)`;
        button.innerText = `${gameType}`;
    }

    window.toggleSearch = function toggleSearch() {
        const searchIcon = document.querySelector('.search-icon');
        const searchBar = document.getElementById('searchBar');

        searchIcon.style.display = 'none';
        searchBar.classList.add('active');
        searchBar.focus();
        players = downloadPlayerList();
    }

    window.logout = function logout() {

        const url = "/api/usr/logout";
        fetch( url, {
            method: "GET",
            credentials: "include",
        })
        .then(response => {
            if (response.ok) {
                window.login_socket.close();
                document.cookie = "accessToken=0; Max-Age=0; path=/";
                document.cookie = "refreshToken=0; Max-Age=0; path=/";

                document.cookie = "action=0; Max-Age=0; path=/";
                document.cookie = "username=0; Max-Age=0; path=/";
                document.cookie = "email=0; Max-Age=0; path=/";
                document.cookie = "userId=0; Max-Age=0; path=/";

                window.showPopup("Sesión cerrada correctamente");
            } else {
                window.showPopup("Error al cerrar sesión");
            }
        })
        .catch(err => {
            window.showPopup("Error al cerrar sesión");
        })
        .finally(() => {
            window.location.hash = "#login";
        });
    };
    

    async function downloadPlayerList() {
        try {
            await handleJwtToken();
            const response = await fetch("/api/settings/playersList");
            if (!response.ok) {
                window.showPopup("Error al descargar la lista de jugadores");
                return;
            }
            players = await response.json();
            return players;
        } catch (error) {
            window.showPopup("Error al descargar la lista de jugadores");
        }
    }

    document.getElementById("searchBar").addEventListener("input", (event) => {

        const query = event.target.value.trim();
        if (query.length > 0) {
            updatePlayerList(query);
            document.getElementById('playerList').style.display = 'block';
        } else {
            document.getElementById('playerList').style.display = 'none';
        }
        
    });    
    
    window.updatePlayerList = function updatePlayerList(query) {
        const playerList = document.getElementById('playerList');
        playerList.innerHTML = '';
        
        const filteredPlayers = players.filter(player =>
            player.username.toLowerCase().startsWith(query.toLowerCase())
        );
        
        filteredPlayers.forEach(player => {
            const li = document.createElement('li');
            li.classList.add('player-item');
            li.innerHTML = `<img src="${player.profile_picture}" alt="Avatar"> ${player.username}`;
            
            li.addEventListener("click", () => {
                goToPlayerProfile(player.username);
            });
            playerList.appendChild(li);
        });
    }
    
    window.openProfilePopup = async function openProfilePopup(username) {
        
        const currentUserId = getCookieValue("userId");
        var btn = document.getElementById("add-friend-btn");
        
        const data = await getDataUser(username);
    
        const otherUserId = data.id;
        document.getElementById("profile-image-img").src = data.picture_url;
        document.getElementById("profile-info-username").innerHTML = data.username;
        updateStatus(currentUserId);
    
        if (otherUserId == currentUserId) {
            btn.style.display = "None";
        }else {
            handleButtonFriend(otherUserId, currentUserId);
            btn.style.display = "Block";
        }
        window.populateProfilePopup(username);
        profilePopup.style.display = 'flex';
    }
        
    window.closeProfilePopup = function closeProfilePopup() {
        profilePopup.style.display = 'none';
    }
        
    window.openSettingsPopup =  function openSettingsPopup() {
        let username = getCookieValue("username");
        let email = getCookieValue("email");

        document.getElementById('settingsPopup').style.display = 'flex';

        showPicture(email);
        settingsCurrentUsername.innerText = username;
    }

    window.closeSettingsPopup = function closeSettingsPopup() {
        settingsPopup.style.display = 'none';
    }
    
    window.toggleSettingsFields = function toggleSettingsFields() {
        let selectedOption = document.getElementById("settings-option").value;
        let fields = ["profile-pic-field", "username-field", "password-field"];
        
        fields.forEach(field => {
            document.getElementById(field).style.display = "none";
        });
        
        if (selectedOption !== "none") {
            document.getElementById(selectedOption + "-field").style.display = "block";
        }
    }
    
    window.createLocalGame = function createLocalGame(type) {
        checkActiveGame(document, homeDiv);
        fetch('/api/game/create/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ "type": type })
        })
        .then(response => {
            if (!response.ok) {
                window.showPopup("Error al crear el juego");
                return;
            }
            window.location.hash = "#rock-paper-scissors";
        })
        .catch(error => {
            window.showPopup("Error al crear el juego");
        });
    }
    
    window.checkOnlineStatus = function checkOnlineStatus(userId) {
        
        userId = String(userId);

        if (window.logged_users.includes(userId)) {
            return true;
        } else {
            return false; 
        }
    }


    window.toggleFriendStatus = async function toggleFriendStatus() {
        const currentUserId = getCookieValue("userId");
        const otherUsername = document.getElementById("profile-info-username").textContent.trim();
        const data = await getDataUser(otherUsername);
    
        const otherUserId = data.id;
        var btn = document.getElementById("add-friend-btn");

        if (btn.innerHTML === "Añadir Amigo"/* & !friends*/ ) {
            await addFriend(currentUserId, otherUserId);
            btn.innerHTML = "Amigo";
            btn.style.backgroundColor = "var(--primary-color)";
            btn.style.color = "white";
        } else if (btn.innerHTML === "Amigo" /*& friends*/ ) {
            await removeFriend(currentUserId, otherUserId)
            btn.innerHTML = "Añadir Amigo";
            btn.style.backgroundColor = "#f5f5f5";
            btn.style.color = "#333";
        }
    };

    window.populateProfilePopup = async function populateProfilePopup(username) {
        try {
            const userResponse = await fetch(`/api/usr/user/${username}`);
            const userData = await userResponse.json();

            if (!userData) {
                window.showPopup("Error al obtener los datos del usuario");
                return;
            }

            const user_id = userData.id;

            const statsResponse = await fetch(`/api/game/statistics/${user_id}/`);
            const statsData = await statsResponse.json();

            if (!statsData) {
                window.showPopup("Error al obtener las estadísticas del juego");
                return;
            }

            const tournamentResponse = await fetch(`/api/tournament/user/${user_id}/tournament-stats`);
            const tournamentData = await tournamentResponse.json();
            if (!tournamentData) {
                return;
            }

            const historyResponse = await fetch(`/api/game/history/${user_id}/`);
            const historyData = await historyResponse.json();

            if (!historyData) {
                window.showPopup("Error al obtener el historial de juegos");
                return;
            }

            profileTournamentsPlayedElement.innerText = tournamentData.tournaments_played_count || 0;
            profileTournamentsWonElement.innerText = tournamentData.tournaments_won_count || 0;
            profilePongGamesPlayedElement.innerText = statsData.online_matches_played || 0;
            profilePongGamesWonElement.innerText = statsData.online_pong_matches_won || 0;
            profileRpsGamesPlayedElement.innerText = statsData.online_matches_played || 0;
            profileRpsGamesWonElement.innerText = statsData.online_rps_matches_won || 0;

            profileTournamentHistoryElement.innerHTML = "";
            profileOnlineHistoryElement.innerHTML = "";
            profileLocalHistoryElement.innerHTML = "";

            if (historyData.tournament_matches && Object.keys(historyData.tournament_matches).length > 0) {
                for (const [tournamentId, tournamentMatches] of Object.entries(historyData.tournament_matches)) {
                    const response = await fetch(`/api/tournament/${tournamentId}/name`);
                    const tournamentName = await response.text();
                    const tournamentData = JSON.parse(tournamentName);
                    const tournamentElement = document.createElement('div');
                    tournamentElement.innerHTML = `<h3 style="text-align: center;">"${tournamentData.name}"</h3>`;
                    tournamentMatches.forEach(match => {
                        const matchElement = document.createElement('div');
                        matchElement.innerHTML = buildSingleMatchHistory(match);
                        tournamentElement.appendChild(matchElement);
                    });
                    profileTournamentHistoryElement.appendChild(tournamentElement);
                }
            } else {
                const noTournamentElement = document.createElement('div');
                noTournamentElement.innerHTML = `<h3 style="text-align: center;">No hay partidos de torneo</h3>`;
                profileTournamentHistoryElement.appendChild(noTournamentElement);
            }

            if (historyData.online_matches && Object.keys(historyData.online_matches).length > 0) {
                historyData.online_matches.forEach(match => {
                    const historyElement = document.createElement('div');
                    historyElement.innerHTML = buildSingleMatchHistory(match);
                    profileOnlineHistoryElement.appendChild(historyElement);
                });
            } else {
                const noOnlineElement = document.createElement('div');
                noOnlineElement.innerHTML = `<h3 style="text-align: center;">No hay partidos online</h3>`;
                profileOnlineHistoryElement.appendChild(noOnlineElement);
            }

            if (historyData.local_matches && Object.keys(historyData.local_matches).length > 0) {
                historyData.local_matches.forEach(match => {
                    const historyElement = document.createElement('div');
                    historyElement.innerHTML = buildSingleMatchHistory(match);
                    profileLocalHistoryElement.appendChild(historyElement);
                });
            } else {
                const noLocalElement = document.createElement('div');
                noLocalElement.innerHTML = `<h3 style="text-align: center;">No hay partidos locales</h3>`;
                profileLocalHistoryElement.appendChild(noLocalElement);
            }

        } catch (error) {
            window.showPopup("Error al obtener los datos del usuario");
        }
    }

    window.buildSingleMatchHistory = function buildSingleMatchHistory(match) {
        const rps_result_dictionary = {
            "rock": "🪨",
            "paper": "📄",
            "scissors": "✂️"
        }
        const left_player_result = match.pong.left_player_score > match.pong.right_player_score ? "winner" : "loser";
        const right_player_result = match.pong.left_player_score < match.pong.right_player_score ? "winner" : "loser";
        const start_date = new Date(match.rps.created_at);
        const start_date_string = start_date.toLocaleString('es-ES', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
        });
        const end_date = new Date(match.pong.finished_at);
        const duration_minutes = Math.floor((end_date - start_date) / 1000 / 60);
        const duration_seconds = Math.floor((end_date - start_date) / 1000);
        const duration_string = duration_minutes > 0 ? `${duration_minutes} min ${duration_seconds} seg` : `${duration_seconds} seg`;

        return `
            <div class="game">
                <p class="result">
                    <span class="${left_player_result}" style="font-size: 30px; width: 10%;">${match.pong.left_player_score}</span>
                    <span class="${left_player_result}"
                        style="display:flex; flex-direction:column; align-items:center;"><span>${match.pong.left_player_username}</span><span>${rps_result_dictionary[match.rps.left_player_choice]}</span></span>
                    <span style="width:10%">VS</span>
                    <span class="${right_player_result}"
                        style="display:flex; flex-direction:column; align-items:center;"><span>${match.pong.right_player_username}</span><span>${rps_result_dictionary[match.rps.right_player_choice]}</span></span>
                    <span class="${right_player_result}" style="font-size: 30px; width: 10%;">${match.pong.right_player_score}</span>
                </p>
                <p class="opponent"><b>Fecha:</b> ${start_date_string}</p>
                <p class="opponent"><b>Duración:</b> ${duration_string}</p>
            </div>
            `;
    }

    window.updateStatus = function updateStatus(userId) {
        var statusCircle = document.getElementById("status-circle");
        if (checkOnlineStatus(userId)) {
            statusCircle.style.backgroundColor = "green";
        } else {
            statusCircle.style.backgroundColor = "red";
        }
    }

    // --- EVENT LISTENERS ---

    document.querySelectorAll(".preset-img").forEach(img => {
        img.addEventListener("click", async () => {
            const src = img.src
            document.getElementById("current-profile-pic").src = src;
        });
    })

    
    document.getElementById("upload-profile-pic").addEventListener("change", function(event) {
        const file = event.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                document.getElementById("current-profile-pic").src = e.target.result;
            };
            reader.readAsDataURL(file);
        }
    });

    document.getElementById("save-btn-images-host").addEventListener("click", async () => {
        
        const src = document.getElementById("current-profile-pic").src;
        const allowedNames = ["default0.gif", "default1.gif", "default2.gif", "default3.gif", "default4.gif"];

        const isDefault = allowedNames.some(name => src.endsWith(name));

        if (isDefault) {
            let email = getCookieValue("email");
            updatePicture(email, src);
        } else {
            const fileInput = document.getElementById("upload-profile-pic");
            const username = getCookieValue("username");

            const file = fileInput.files[0];
            const formData = new FormData();
            
            if (!file) {
                window.showPopup("Por favor, selecciona una imagen.");
                return;
            }
            formData.append("profile_pic", file);
            formData.append("username", username);
            uploadImage(formData);
        }
    });

    document.getElementById("save-btn-name").addEventListener("click", async () => {
        const newUsername = document.getElementById("new-username").value;
        const email = getCookieValue("email");
        if (await updateUsername(email, newUsername)) {
            window.closeSettingsPopup();
            window.logout();
        }
    });

    document.getElementById("save-btn-password").addEventListener("click", () => {
        const oldPass = document.getElementById("old-password").value;
        const newPass1 = document.getElementById("new-password1").value;
        const newPass2 = document.getElementById("new-password2").value;
        const email = getCookieValue("email");

        updatePassword(email, oldPass, newPass1, newPass2);
    });


    window.eventManager.addEventListener(carousel, 'mousedown', (e) => {
        isDragging = true;
        startX = e.clientX;
    });

    window.eventManager.addEventListener(window, 'mouseup', () => {
        if (isDragging) {
            const rotation = Math.round(currentAngle / angleStep) * angleStep;
            currentAngle = rotation;
            carousel.style.transform = `rotateY(${currentAngle}deg)`;
        }
        isDragging = false;
    });

    window.eventManager.addEventListener(window, 'mousemove', (e) => {
        if (isDragging) {
            const dx = startX - e.clientX;
            currentAngle -= dx * 0.5;
            carousel.style.transform = `rotateY(${currentAngle}deg)`;
            startX = e.clientX;
        }
    });

    window.eventManager.addEventListener(window, 'keydown', (e) => {
        if (e.key === "ArrowLeft") {
            currentAngle += angleStep;
            carousel.style.transform = `rotateY(${currentAngle}deg)`;
        } else if (e.key === "ArrowRight") {
            currentAngle -= angleStep;
            carousel.style.transform = `rotateY(${currentAngle}deg)`;
        }
    });

    window.eventManager.addEventListener(document, "click", function () {
        const dropdownMenu = document.getElementById("dropdownMenu");
        dropdownMenu.style.display = "none";
    });

    window.eventManager.addEventListener(document.getElementById('searchBar'), 'input', function () {
        updatePlayerList(this.value);
    });

    window.eventManager.addEventListener(document, 'click', function (e) {
        const searchBar = document.getElementById('searchBar');
        const searchIcon = document.querySelector('.search-icon');
        const playerList = document.getElementById('playerList');

        if (!searchBar.contains(e.target) && !searchIcon.contains(e.target)) {
            searchBar.classList.remove('active');
            searchIcon.style.display = 'block';
            playerList.style.display = 'none';
        }
    });

    window.eventManager.addEventListener(document, 'keydown', function (e) {
        if (e.key === 'Escape') {
            const searchBar = document.getElementById('searchBar');
            const searchIcon = document.querySelector('.search-icon');
            const playerList = document.getElementById('playerList');

            searchBar.classList.remove('active');
            searchIcon.style.display = 'block';
            playerList.style.display = 'none';
        }
    });

    window.eventManager.addEventListener(document.getElementById('profilePopup'), 'click', function (event) {
        if (!event.target.closest('.profile-container')) {
            window.closeProfilePopup();
        }
    });

    window.eventManager.addEventListener(document.getElementById('settingsPopup'), 'click', function (event) {
        if (!event.target.closest('.settings-container')) {
            window.closeSettingsPopup();
        }
    });

    document.getElementById('add-friend-btn').addEventListener('click', function(event) {
        window.toggleFriendStatus();
    });

    

    window.eventManager.addEventListener(title, 'mouseenter', () => {
        title.classList.add('glitch');
        title.style.transform = 'translateY(-5px)';
    });

    window.eventManager.addEventListener(title, 'mouseleave', () => {
        title.classList.remove('glitch');
        title.style.transform = 'translateY(0)';
    });



    tabButtons.forEach(button => {
        window.eventManager.addEventListener(button, 'click', () => {
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            histories.forEach(history => history.style.display = 'none');
            const target = button.getAttribute('data-tab');
            document.getElementById(target).style.display = 'block';
        });
    });


    // --- INITIALIZATION ---

    if (!hasAccessToken()) {
        window.sessionStorage.setItem("afterLoginRedirect", "#");
        window.location.hash = "#login"
    }
    try {
        await handleJwtToken();
        initLoginSocket();
        await checkActiveGame(document, homeDiv);
    }
    catch (error) {
        showPopup("Sesión expirada, por favor vuelve a iniciar sesión");
        window.location.hash = "#login"
    }
}
