// static/js/views/2FA.js

import EventListenerManager from '../utils/eventListenerManager.js';

export async function render2FA() {
    const response = await fetch('static/html/2FA.html');
    const htmlContent = await response.text();
    return htmlContent;
}

export async function resendOtp() {
    try {
        const response = await fetch("/api/usr/resend_otp", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                //username: sessionStorage.getItem("username"),
                //password: sessionStorage.getItem("password"),
                email: sessionStorage.getItem("email"),
            }),
        });

        const data = await response.json();

        if (response.ok) {
            document.getElementById("registerResponseMessage").innerText = data.message;
            return true;
        } else {
            document.getElementById("registerResponseMessage").innerText = data.error || "Error desconocido";
            return false;
        }
    } catch (error) {
        console.error("Error en la solicitud:", error);
        document.getElementById("registerResponseMessage").innerText = "Error de conexión.";
    }
}

export async function verifyOtpRegister(code) {
    
    let url = null;
    try {
       if (sessionStorage.getItem("action") === "register"){
            url = "verify_email_otp_register";
        } else if (sessionStorage.getItem("action") === "login"){
            url = "verify_email_otp_login";
        } else {
            throw new Error("session Storage action not setted register/login");
        }
    
        const response = await fetch("/api/usr/" + url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                //username: sessionStorage.getItem("username"),
               // password: sessionStorage.getItem("password"), 
                email: sessionStorage.getItem("email"),
                otp_token: code
            }),
        });

        const data = await response.json();

        if (response.ok && sessionStorage.getItem("action") === "login") {
            document.getElementById("registerResponseMessage").innerText = data.message;
            console.log("obtenemos coookies oleee")
            document.cookie = `accessToken=${data.access}; path=/; secure; SameSite=Lax`;
            document.cookie = `refreshToken=${data.refresh}; path=/; secure; SameSite=Lax`;
            window.location.hash = "#";

        } else if (response.ok && sessionStorage.getItem("action") === "register") {
            document.getElementById("registerResponseMessage").innerText = data.message;
            window.location.hash = "#new-login";
        
        } else {
            document.getElementById("registerResponseMessage").innerText = data.error || "Error desconocido";
        }
    } catch (error) {
        console.error("Error en la solicitud:", error);
        document.getElementById("registerResponseMessage").innerText = "Error de conexión.";
    }
}



export function init2FA() {

    // --- VARIABLES AND CONSTANTS ---

    const eventManager = new EventListenerManager();
    let resendTimer;
    let resendInterval;
    const resendButton = document.getElementById("resend-button");
    const timerElement = document.getElementById("timer");
    const secondsElement = document.getElementById("seconds");

    const username = sessionStorage.getItem("username");
    if (username) {
        document.getElementById("username").textContent = `@${username}`;
    }

    // --- DOM ELEMENTS ---

    const title = document.querySelector('.site-title');

    // --- FUNCTIONS ---

    window.startResendTimer = function startResendTimer() {
        resendButton.disabled = true;
        resendTimer = 60;
        timerElement.textContent = resendTimer;
        timerElement.style.display = "inline";
        secondsElement.style.display = "inline";
        resendInterval = setInterval(() => {
            resendTimer--;
            timerElement.textContent = resendTimer;
            if (resendTimer <= 0) {
                clearInterval(resendInterval);
                resendButton.disabled = false;
                timerElement.style.display = "none";
                secondsElement.style.display = "none";
            }
        }, 1000);
    }
    
    window.resendCode = function resendCode() {
        if (resendOtp()) {
            alert("Código reenviado");
            clearInterval(resendInterval);
            startResendTimer();
        }else{
            alert("No se puede reenviar codigo");
        }
    }
    
    window.handleInput = function handleInput(input, index) {
        const inputs = document.querySelectorAll(".code-input");
        input.style.background = input.value ? "#16a085" : "#222";
        if (input.value.length === 1 && index < 5) {
            inputs[index + 1].focus();
        }
    }

    window.moveToPrev = function moveToPrev(event, input, index) {
        const inputs = document.querySelectorAll(".code-input");
        if (event.key === "Backspace") {
            if (input.value === "" && index > 0) {
                inputs[index - 1].focus();
            }
            input.style.background = input.value ? "#16a085" : "#222";
        }
    }

    window.verifyCode = async function verifyCode() { // ← Agregar async aquí
        const code = Array.from(document.querySelectorAll(".code-input"))
                          .map(input => input.value)
                          .join("");
    
        if (code.length === 6) {
            verifyOtpRegister(code);
        } else {
            alert("Por favor, ingresa los 6 dígitos del código.");
        }
    };
        
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

    eventManager.addEventListener(title, 'mouseenter', () => {
        title.classList.add('glitch');
        title.style.transform = 'translateY(-5px)';
    });

    eventManager.addEventListener(title, 'mouseleave', () => {
        title.classList.remove('glitch');
        title.style.transform = 'translateY(0)';
    });


    // --- INITIALIZATION ---
    
    window.startResendTimer();

    return () => eventManager.removeAllEventListeners();
        
}
