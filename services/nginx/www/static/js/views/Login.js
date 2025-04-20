// static/js/views/login.js

import EventListenerManager from '../utils/eventListenerManager.js';
import { getDataUser } from '../utils/profile.js';

export async function renderLogin() {
    const response = await fetch('static/html/login.html');
    const htmlContent = await response.text();
    return htmlContent;
}

window.login_socket = null;
window.logged_users = [];

function initLoginSocket() {
    
    if (window.login_socket === null) {
        window.login_socket = new WebSocket(`wss://${window.location.host}/ws/login/`);
    }

    window.login_socket.onopen = function(event) {
    }

    window.login_socket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        console.log("login_socket message");
        console.log(data);
        
        if (data.type === "logged_users") {
            window.logged_users = data.logged_users;
        }
        const popup = document.getElementById("profilePopup");
        if (popup && popup.style.display === "flex") {
            const username = document.getElementById("profile-info-username")?.innerText;
            openProfilePopup(username);
        }
    }
    window.login_socket.onclose = function(event) {
        window.login_socket = null;
        console.log("login_socket close");
    }

    window.login_socket.onerror = function(event) {
        window.login_socket = null;
        console.log("login_socket error");
        console.log(event);
    }
}


export { initLoginSocket } ;

export function initLogin() {

    // --- VARIABLES AND CONSTANTS ---

    


    // --- DOM ELEMENTS ---

    const title = document.querySelector('.site-title');
    const registerButton = document.getElementById('register-btn');
    const loginButton = document.getElementById('login-btn');
    const registerResponseMessage = document.getElementById("register-response-message");
    const registerDataSection = document.getElementById("register-data-container");

    // --- FUNCTIONS ---

    window.toggleForm = function toggleForm() {

        let loginContainer = document.getElementById('login-container');
        let registerContainer = document.getElementById('register-container');

        if (loginContainer.style.display === 'none') {
            loginContainer.style.display = 'block';
            registerContainer.style.display = 'none';
           // qrSection.style.display = 'none';
        } else {
            loginContainer.style.display = 'none';
            registerContainer.style.display = 'block';
            //registerDataSection.style.display = 'block';//data contaniner register
            //qrSection.style.display = 'none';
        }
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
    
    async function registerUser() {
        const url = "/api/usr/register"
        const username = document.getElementById("reg-name").value;
        const email = document.getElementById("reg-email").value;
        const password = document.getElementById("reg-password").value;

        if (!username || !email || !password) {
            window.showPopup("Todos los campos son obligatorios.");
            //alert("Todos los campos son obligatorios.");
            return;
        }

        try {

            const response = await fetch(url, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username: username, password: password, email: email })
            });

            const data = await response.json();

            if(response.ok) {
                sessionStorage.setItem("action", "register");
                sessionStorage.setItem("username", username);
                sessionStorage.setItem("email", email);
                window.showPopup("Introduce el código recibido por correo");
                window.location.hash = "#2FA";
            } else{
                window.showPopup(data.email || data.username || data.error );}
                //registerResponseMessage.innerText = data.email || data.username || data.error || "Error desconocido. Inténtalo de nuevo.";}
        } catch (error) {
            console.error("Error en la solicitud:", error);
            window.showPopup("Hubo un problema con la conexion.");
            //alert("Hubo un problema con el registro.");
        }
    }

    async function loginUser() {
        const url = "/api/usr/login"
        const email = document.getElementById("login-email").value;
        const password = document.getElementById("login-password").value;
        
        if (!email || !password) {
            window.showPopup("Todos los campos son obligatorios.");
            //alert("Todos los campos son obligatorios.");
            return;
        }

        try {
            const response = await fetch(url, {
                method: "POST",
                headers: { "Content-Type": "application/json"},
                body: JSON.stringify({ email: email, password: password })
            });

            const data = await response.json();

            if (response.ok) {
                sessionStorage.setItem("action", "login");
                sessionStorage.setItem("email", email);
                sessionStorage.setItem("username", data.username);
                window.showPopup("Introduce el código recibido por correo");
                window.location.hash = "#2FA";
            } else {
                window.showPopup(data.error || data.username);
                //loginResponseMessage.innerText = data.error || data.username || "Error desconocido. Inténtalo de nuevo.";
            }
        } catch (error) {
            console.error("Error en la solicitud:", error);
            window.showPopup("Hubo un problema con la conexion.");
           // alert("Hubo un problema con el registro.");
        }
    }

    // --- EVENT LISTENERS ---

    window.eventManager.addEventListener(title, 'mouseenter', () => {
        title.classList.add('glitch');
        title.style.transform = 'translateY(-5px)';
    });

    window.eventManager.addEventListener(title, 'mouseleave', () => {
        title.classList.remove('glitch');
        title.style.transform = 'translateY(0)';
    });
    
    if (registerButton) {
        window.eventManager.addEventListener(registerButton, "click", registerUser);
    }

    if(loginButton) {
        window.eventManager.addEventListener(loginButton, "click", loginUser);
    }


    // --- INITIALIZATION ---
}
