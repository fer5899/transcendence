import { initLoginSocket } from './login.js';
import { getCookieValue } from '../utils/jwtUtils.js';

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
                username: getCookieValue("username"),
                email : getCookieValue("email"),
                password : getCookieValue("password"),
            }),
        });

        const data = await response.json();

        if (response.ok) {
            window.showPopup(data.message);
            return true;
        } else {
            window.showPopup(data.message);
            return false;
        }
    } catch (error) {
        window.showPopup("Error reenviando el código");
    }
}

export async function verifyOtpRegister(code) {
    
    let url = null;

    try {
       if (getCookieValue("action") === "register"){
            url = "verify_email_otp_register";
        } else if (getCookieValue("action") === "login"){
            url = "verify_email_otp_login";
        } else {
            throw new Error("session Storage action not setted register/login");
        }
    
        const response = await fetch("/api/usr/" + url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                email: getCookieValue("email"),
                otp_token: code
            }),
        });

        const data = await response.json();

        if (response.ok && getCookieValue("action") === "login") {
            
           
            
            document.cookie = `accessToken=${data.access}; path=/; secure; SameSite=Lax`;
            document.cookie = `refreshToken=${data.refresh}; path=/; secure; SameSite=Lax`;
            initLoginSocket();
            window.location.hash = "#";
        } else if (response.ok && getCookieValue("action") === "register") {
            window.showPopup(data.message);
            window.location.hash = "#login";
        
        } else {
            window.showPopup(data.error);
        }
    } catch (error) {
        window.showPopup("Error de conexión.");
    }
}



export function init2FA() {

    // --- VARIABLES AND CONSTANTS ---

    
    let resendTimer;
    let resendInterval;
    const resendButton = document.getElementById("resend-button");
    const timerElement = document.getElementById("timer");
    const secondsElement = document.getElementById("seconds");

    const username =  getCookieValue("username");
    if (username) {
        document.getElementById("username").textContent = `@${username}`;
    }

    // --- DOM ELEMENTS ---

    const title = document.querySelector('.site-title');
    const codeContainer = document.getElementById("code-container");

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
            window.showPopup("Código reenviado");
            clearInterval(resendInterval);
            window.startResendTimer();
        }else{
            window.showPopup("Error reenviando el código");
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
        
        if (event.key === "Backspace" || event.key === "Delete") {
            input.value = "";
            input.style.background = "#222";
            event.preventDefault();
            if (index > 0) {
                inputs[index - 1].focus();
                inputs[index - 1].select();
            }
        } else if (event.key === "ArrowLeft" && index > 0) {
            inputs[index - 1].focus();
            inputs[index - 1].select();
            event.preventDefault();
        } else if (event.key === "ArrowRight" && index < inputs.length - 1) {
            inputs[index + 1].focus();
            inputs[index + 1].select();
            event.preventDefault();
        }
    };
    
    
    window.verifyCode = async function verifyCode() {
        const code = Array.from(document.querySelectorAll(".code-input"))
                          .map(input => input.value)
                          .join("");
    
        if (code.length === 6) {
            verifyOtpRegister(code);
        } else {
            window.showPopup("Por favor, ingresa los 6 dígitos del código.");
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

    window.eventManager.addEventListener(title, 'mouseenter', () => {
        title.classList.add('glitch');
        title.style.transform = 'translateY(-5px)';
    });

    window.eventManager.addEventListener(title, 'mouseleave', () => {
        title.classList.remove('glitch');
        title.style.transform = 'translateY(0)';
    });

    window.eventManager.addEventListener(codeContainer, "paste", (e) => {
        e.preventDefault();
        const inputs = document.querySelectorAll(".code-input");
        const pastedData = e.clipboardData.getData("text").replace(/\s+/g, '');
        let startIndex = Array.from(inputs).indexOf(document.activeElement);
        if (startIndex === -1) startIndex = 0;
        for (let i = 0; i < pastedData.length && startIndex < inputs.length; i++, startIndex++) {
            inputs[startIndex].value = pastedData[i];
            inputs[startIndex].style.background = "#16a085";
        }
        if (startIndex > 0 && startIndex <= inputs.length) {
            inputs[startIndex - 1].focus();
        }
    });


    // --- INITIALIZATION ---
    
    window.startResendTimer();
        
}
