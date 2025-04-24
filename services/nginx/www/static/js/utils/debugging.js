window.showPopup = function(message, timeout = 5000) {
    const popup = document.getElementById('popup-alert');
    const popupMessage = document.getElementById('popup-alert-message');
    if (window.popupTimeoutId) {
        clearTimeout(window.popupTimeoutId);
    }
    
    popupMessage.textContent = message;
    
    popup.classList.remove('hide');
    popup.classList.add('show');
    
    window.popupTimeoutId = setTimeout(() => {
        popup.classList.add('hide');
        popup.classList.remove('show');
        window.popupTimeoutId = null;
    }, timeout);
}