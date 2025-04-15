window.showPopup = function(message) {
    const popup = document.getElementById('popup-alert');
    const popupMessage = document.getElementById('popup-alert-message');
    
    popupMessage.textContent = message;  // Asigna el mensaje al popup
    
    // Muestra el popup
    popup.classList.remove('hide');
    popup.classList.add('show');
    
    // Después de 3 segundos, lo oculta
    setTimeout(() => {
        popup.classList.add('hide');
        opup.classList.remove('show');;
    }, 3000);  // El pop-up desaparecerá después de 3 segundos
}