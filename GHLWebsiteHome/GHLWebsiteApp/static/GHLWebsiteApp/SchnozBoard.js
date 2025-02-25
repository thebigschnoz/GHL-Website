function getGames(){

};

document.addEventListener('DOMContentLoaded', function(){
    const scoreboard = document.getElementById("fakescoreboard");
    const Logo = "http://loodibee.com/wp-content/uploads/nhl-";
        const Teams = {
            ANA: `${Logo}anaheim-ducks-logo.png`,
            BOS: `${Logo}boston-bruins-logo.png`,
            BUF: `${Logo}buffalo-sabres-logo.png`,
            CAR: `${Logo}carolina-hurricanes-logo.png`,
            CBJ: `${Logo}columbus-blue-jackets-logo.png`,
            CGY: `${Logo}calgary-flames-logo.png`,
            CHI: `${Logo}chicago-blackhawks-logo.png`,
            COL: `${Logo}colorado-avalanche-logo.png`,
            DAL: `${Logo}dallas-stars-logo.png`,
            DET: `${Logo}detroit-red-wings-logo.png`,
            EDM: `${Logo}edmonton-oilers-logo.png`,
            FLA: `${Logo}florida-panthers-logo.png`,
            LAK: `${Logo}los-angeles-kings-logo.png`,
            MIN: `${Logo}minnesota-wild-logo.png`,
            MTL: `${Logo}montreal-canadiens-logo.png`,
            NJD: `${Logo}new-jersey-devils-logo.png`,
            NSH: `${Logo}nashville-predators-logo.png`,
            NYI: `${Logo}new-york-islanders-logo.png`,
            NYR: `${Logo}new-york-rangers-logo.png`,
            OTT: `${Logo}ottawa-senators-logo.png`,
            PHI: `${Logo}philadelphia-flyers-logo.png`,
            PIT: `${Logo}pittsburgh-penguins-logo.png`,
            SEA: `${Logo}seattle-kraken-logo.png`,
            SJS: `${Logo}san-jose-sharks-logo.png`,
            STL: `${Logo}st-louis-blues-logo.png`,
            TBL: `${Logo}tampa-bay-lightning-logo.png`,
            TOR: `${Logo}toronto-maple-leafs-logo.png`,
            UTA: `https://loodibee.com/wp-content/uploads/NHL-Utah-Hockey-Club-Logo.png`,
            VAN: `${Logo}vancouver-canucks-logo.png`,
            VGK: `${Logo}vegas-golden-knights-logo.png`,
            WPG: `${Logo}winnipeg-jets-logo.png`,
            WSH: `${Logo}washington-capitals-logo.png`,
            ATL: `https://loodibee.com/wp-content/uploads/Atlanta-Thrashers-Logo-1999-2011.png`,
      }

    fetch("/gameapi/")
    .then(response => response.json())
    .then(data => {
        console.log(data);
    });
    for (let block in data){
        scoreboard.innerHTML = `
            <div className="game__container">
                <div className="game__top-bar">
                    <span className=game__time></span>
                </div>
                <div className="info-split">
                    <div className="team__container">
                    <div className="team">
                        <img className="team__logo" src=${away.logo} alt={${away.name} team logo} />
                        <p className=team__name ${!final ? "" : winner === home.name ? "losing-team" : ""}>{away.name}</p>
                        <p className=team__score ${!final ? "" : winner === home.name ? "losing-team" : ""}>{away.score}</p>
                    </div>
                    <div className="team">
                        <img className="team__logo" src=${home.logo} alt={${away.name} team logo} />
                        <p className={team__name ${!final ? "" : winner === away.name ? "losing-team" : ""}}>{home.name}</p>
                        <p className={team__score ${!final ? "" : winner === away.name ? "losing-team" : ""}}>{home.score}</p>
                    </div>
                    </div>
                    { final ? null :
                    <div className="game__in-progress">
                    <span>
                        { drive }<br/>
                        { yard }
                    </span>
                    </div> }
                </div>
            </div>
            `;
    }
});