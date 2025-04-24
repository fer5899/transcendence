import { renderHome, initHome } from './views/home.js';
import { renderGame, initGame } from './views/game.js';
import { renderVersusWait, initVersusWait } from './views/versusWait.js';
import { renderTournamentRoom, initTournamentRoom } from './views/tournamentRoom.js';
import { renderTournamentsList, initTournamentsList } from './views/tournamentsList.js';
import { renderLogin, initLogin } from './views/login.js';
import { renderRockPaperScissors, initRockPaperScissors } from './views/rockPaperScissors.js';
import { render2FA, init2FA } from './views/2FA.js';
import { renderHistoryBlockchain, initHistoryBlockchain } from './views/blockchain.js';
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
    "/login": { render: renderLogin, init: initLogin },
    "/rock-paper-scissors": { render: renderRockPaperScissors, init: initRockPaperScissors },
    "/2FA": { render: render2FA, init: init2FA },
    "/blockchain-history": { render: renderHistoryBlockchain, init: initHistoryBlockchain },
};

window.eventManager = new EventListenerManager();

function parseRoute(path) {
    
    path = path.startsWith("/") ? path : "/" + path;
    
    const routeKeys = Object.keys(routes);
    for (const key of routeKeys) {
        const paramMatch = key.match(/:([^\/]+)/);
        if (paramMatch) {
            const paramKey = paramMatch[1];
            const basePath = key.split("/:")[0]; 

            if (path.startsWith(basePath)) {            
                const paramValue = path.slice(basePath.length + 1);
                return { route: routes[key], params: { [paramKey]: paramValue } };
            }
        }
    }
    return { route: routes[path], params: {} };
}

async function router() {
    const path = location.hash.slice(1) || "/index";
    const { route, params } = parseRoute(path);

    if (route) {
        document.getElementById("main-content").innerHTML = await route.render(params);
        window.eventManager.removeAllEventListeners();
        route.init(params);
    } else {
        document.getElementById("main-content").innerHTML = "<h2>404</h2><p>NOT FOUND</p>";
    }
}

window.addEventListener("hashchange", router);
window.addEventListener("load", router);
