
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
    }

    window.login_socket.onerror = function(event) {
        window.login_socket = null;
    }
}


export { initLoginSocket } ;

export function initLogin() {

    // --- DOM ELEMENTS ---

    const title = document.querySelector('.site-title');
    const registerButton = document.getElementById('register-btn');
    const loginButton = document.getElementById('login-btn');

    // --- FUNCTIONS ---

    window.toggleForm = function toggleForm() {

        let loginContainer = document.getElementById('login-container');
        let registerContainer = document.getElementById('register-container');

        if (loginContainer.style.display === 'none') {
            loginContainer.style.display = 'block';
            registerContainer.style.display = 'none';
        } else {
            loginContainer.style.display = 'none';
            registerContainer.style.display = 'block';
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
            window.showPopup("Todos los campos son obligatorios");
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
                document.cookie = "action=register; path=/";
                document.cookie = `username=${encodeURIComponent(username)}; path=/`;
                document.cookie = `email=${encodeURIComponent(email)}; path=/`;
                window.showPopup("Introduce el código recibido por correo");
                window.location.hash = "#2FA";
            } else {
                window.showPopup(getFirstErrorMessage(data));
            }
        } catch (error) {
            window.showPopup("Error en el registro");
        }
    }

    function getFirstErrorMessage(response) {
        const errorMessages = Object.values(response);
        if (errorMessages.length > 0) {
            const firstError = errorMessages[0];
            if (Array.isArray(firstError)) {
                return firstError[0];
            } else {
                return firstError;
            }
        }
        return "Error";
    }

    async function loginUser() {
        const url = "/api/usr/login"
        const email = document.getElementById("login-email").value;
        const password = document.getElementById("login-password").value;
        
        if (!email || !password) {
            window.showPopup("Todos los campos son obligatorios");
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
                document.cookie = "action=login; path=/";
                document.cookie = `username=${encodeURIComponent(data.username)}; path=/`;
                document.cookie = `email=${encodeURIComponent(email)}; path=/`;
                document.cookie = `userId=${encodeURIComponent(data.userId)}; path=/`;
                window.showPopup("Introduce el código recibido por correo");
                window.location.hash = "#2FA";
            } else {
                window.showPopup(getFirstErrorMessage(data));
            }
        } catch (error) {
            window.showPopup("Error en el inicio de sesión");
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

}
