// static/js/views/home.js

import EventListenerManager from '../utils/eventListenerManager.js';

export async function renderHome() {
    const response = await fetch('static/html/home.html');
    const htmlContent = await response.text();
    return htmlContent;
}

export function initHome() {

    // --- VARIABLES AND CONSTANTS ---

    const eventManager = new EventListenerManager();

    const totalCards = 4;
    const angleStep = 360 / totalCards;
    let currentAngle = 0;
    let isDragging = false;
    let startX = 0;

    const players = [
        { username: "javiersa", avatar: "2.gif" },
        { username: "f-gomez", avatar: "3.gif" },
        { username: "vcered", avatar: "4.gif" },
        { username: "dgarizard", avatar: "5.gif" },
        { username: "messi", avatar: "1.gif" },
        { username: "cristiano", avatar: "3.gif" },
        { username: "neymar123", avatar: "2.gif" },
        { username: "lewandosk", avatar: "5.gif" },
    ];

    // --- DOM ELEMENTS ---

    const carousel = document.getElementById("carousel");
    const title = document.querySelector('.site-title');
    const tabButtons = document.querySelectorAll('.tab-btn');
    const histories = document.querySelectorAll('.history');

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
        const playerList = document.getElementById('playerList');

        searchIcon.style.display = 'none';
        searchBar.classList.add('active');
        searchBar.focus();
        playerList.style.display = 'block';
        updatePlayerList('');
    }

    window.updatePlayerList = function updatePlayerList(query) {
        const playerList = document.getElementById('playerList');
        playerList.innerHTML = '';

        const filteredPlayers = players.filter(player =>
            player.username.toLowerCase().includes(query.toLowerCase())
        ).slice(0, 5);

        filteredPlayers.forEach(player => {
            const li = document.createElement('li');
            li.classList.add('player-item');
            li.innerHTML = `<img src="${player.avatar}" alt="Avatar"> ${player.username}`;
            playerList.appendChild(li);
        });
    }

    window.openProfilePopup = function openProfilePopup() {
            document.getElementById('profilePopup').style.display = 'flex';
    }

    window.closeProfilePopup = function closeProfilePopup() {
        document.getElementById('profilePopup').style.display = 'none';
    }

    window.openSettingsPopup = function openSettingsPopup() {
        document.getElementById('settingsPopup').style.display = 'flex';
    }

    window.closeSettingsPopup = function closeSettingsPopup() {
        document.getElementById('settingsPopup').style.display = 'none';
    }

    window.toggleSettingsFields = function toggleSettingsFields() {
        let selectedOption = document.getElementById("settings-option").value;
        let fields = ["profile-pic-field", "username-field", "password-field", "otros-field"];

        fields.forEach(field => {
            document.getElementById(field).style.display = "none";
        });

        if (selectedOption !== "none") {
            document.getElementById(selectedOption + "-field").style.display = "block";
        }
    }
    
    window.viewGame = function viewGame() {
        console.log("Ver la partida nuevamente");
    }


    // --- EVENT LISTENERS ---

    eventManager.addEventListener(carousel, 'mousedown', (e) => {
        isDragging = true;
        startX = e.clientX;
    });

    eventManager.addEventListener(window, 'mouseup', () => {
        if (isDragging) {
            const rotation = Math.round(currentAngle / angleStep) * angleStep;
            currentAngle = rotation;
            carousel.style.transform = `rotateY(${currentAngle}deg)`;
        }
        isDragging = false;
    });

    eventManager.addEventListener(window, 'mousemove', (e) => {
        if (isDragging) {
            const dx = startX - e.clientX;
            currentAngle -= dx * 0.5;
            carousel.style.transform = `rotateY(${currentAngle}deg)`;
            startX = e.clientX;
        }
    });

    eventManager.addEventListener(window, 'keydown', (e) => {
        if (e.key === "ArrowLeft") {
            currentAngle += angleStep;
            carousel.style.transform = `rotateY(${currentAngle}deg)`;
        } else if (e.key === "ArrowRight") {
            currentAngle -= angleStep;
            carousel.style.transform = `rotateY(${currentAngle}deg)`;
        }
    });

    eventManager.addEventListener(document, "click", function () {
        const dropdownMenu = document.getElementById("dropdownMenu");
        dropdownMenu.style.display = "none";
    });

    eventManager.addEventListener(document.getElementById('searchBar'), 'input', function () {
        updatePlayerList(this.value);
    });

    eventManager.addEventListener(document, 'click', function (e) {
        const searchBar = document.getElementById('searchBar');
        const searchIcon = document.querySelector('.search-icon');
        const playerList = document.getElementById('playerList');

        if (!searchBar.contains(e.target) && !searchIcon.contains(e.target)) {
            searchBar.classList.remove('active');
            searchIcon.style.display = 'block';
            playerList.style.display = 'none';
        }
    });

    eventManager.addEventListener(document, 'keydown', function (e) {
        if (e.key === 'Escape') {
            const searchBar = document.getElementById('searchBar');
            const searchIcon = document.querySelector('.search-icon');
            const playerList = document.getElementById('playerList');

            searchBar.classList.remove('active');
            searchIcon.style.display = 'block';
            playerList.style.display = 'none';
        }
    });

    eventManager.addEventListener(document.getElementById('profilePopup'), 'click', function (event) {
        if (!event.target.closest('.profile-container')) {
            closeProfilePopup();
        }
    });

    eventManager.addEventListener(document.getElementById('settingsPopup'), 'click', function (event) {
        if (!event.target.closest('.settings-container')) {
            closeSettingsPopup();
        }
    });

    

    eventManager.addEventListener(title, 'mouseenter', () => {
        title.classList.add('glitch');
        title.style.transform = 'translateY(-5px)';
    });

    eventManager.addEventListener(title, 'mouseleave', () => {
        title.classList.remove('glitch');
        title.style.transform = 'translateY(0)';
    });

    

    tabButtons.forEach(button => {
        eventManager.addEventListener(button, 'click', () => {
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            histories.forEach(history => history.style.display = 'none');
            const target = button.getAttribute('data-tab');
            document.getElementById(target).style.display = 'block';
        });
    });

    return () => eventManager.removeAllEventListeners();
}
