// static/js/spa-navigation.js

import { renderHome, initHome } from './views/home.js';
import { renderGame, initGame } from './views/game.js';
import { renderVersusWait, initVersusWait } from './views/versusWait.js';
import { renderTournamentRoom, initTournamentRoom } from './views/TournamentRoom.js';
import { renderTournamentsList, initTournamentsList } from './views/tournamentsList.js';
import { renderLogin, initLogin } from './views/Login.js';
import { renderRockPaperScissors, initRockPaperScissors } from './views/rockPaperScissors.js';
import { render2FA, init2FA } from './views/2FA.js';
import EventListenerManager from './utils/eventListenerManager.js';

/**
 * Container for possible routes of the SPA. Works as a pointer
 * of functions to render and initialize each section.
*/
const routes = {
    "/index": { render: renderHome, init: initHome },
    "/game": { render: renderGame, init: initGame },
    "/tournament/room/:id": { render: renderTournamentRoom, init: initTournamentRoom },
    "/versus-wait": { render: renderVersusWait, init: initVersusWait },
    "/tournaments-list": { render: renderTournamentsList, init: initTournamentsList },
    "/new-login": { render: renderLogin, init: initLogin },
    "/rock-paper-scissors": { render: renderRockPaperScissors, init: initRockPaperScissors },
    "/2FA": { render: render2FA, init: init2FA },
};

window.eventManager = new EventListenerManager();

function parseRoute(path) {
    
    path = path.startsWith("/") ? path : "/" + path;
    
    const routeKeys = Object.keys(routes);
    for (const key of routeKeys) {
        const paramMatch = key.match(/:([^\/]+)/);
        if (paramMatch) {
            console.log("paramMatch", paramMatch);
            const paramKey = paramMatch[1];
            const basePath = key.split("/:")[0]; 

            if (path.startsWith(basePath)) {            
                const paramValue = path.slice(basePath.length + 1);
                return { route: routes[key], params: { [paramKey]: paramValue } };
            } else {
                console.log("No match for path:", path);
            }
        }
    }
    return { route: routes[path], params: {} };
}

async function router() {
    const path = location.hash.slice(1) || "/index";
    const { route, params } = parseRoute(path);
    console.log("Ruta:", route, "Parámetros:", params);

    //Renders the HTML content of the route
    if (route) {
        document.getElementById("main-content").innerHTML = await route.render(params);
        window.eventManager.removeAllEventListeners();
        console.log("Event listeners removed");
        route.init(params);
    } else {
        document.getElementById("main-content").innerHTML = "<h2>404</h2><p>NOT FOUND</p>";
    }
}

window.addEventListener("hashchange", router);
window.addEventListener("load", router);
