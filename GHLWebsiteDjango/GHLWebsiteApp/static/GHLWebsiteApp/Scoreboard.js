import React from 'react';
import ReactDOM from 'react-dom/client'

class ESPN extends React.Component {
    render() {
      return (
          <ScoreBoard />
      );
    }
  }
  
  class ScoreBoard extends React.Component {
    render() {
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
      
      return (
        <div className="scoreboard__container">
          <Game
          time="2:32 - 2nd"
          drive="2nd & 10"
          yard="MIN 25"
          channel="NBC"
          away={{ name: "MIN", score: 14, logo: Teams.MIN }} 
          home={{ name: "DAL", score: 7, logo: Teams.DAL }}
          final={false}
        />
        <Game 
          away={{ name: "DET", score: 13, logo: Teams.DET }} 
          home={{ name: "CHI", score: 20, logo: Teams.CHI }}
          final={true}
        />
        <Game
          away={{ name: "WSH", score: 49, logo: Teams.WSH }} 
          home={{ name: "STL", score: 13, logo: Teams.STL }}
          final={true}
        />
        <Game
          away={{ name: "BUF", score: 16, logo: Teams.BUF }} 
          home={{ name: "CBJ", score: 19, logo: Teams.CBJ }}
          final={true}
        />
        <Game
          away={{ name: "ATL", score: 26, logo: Teams.ATL }} 
          home={{ name: "ATL", score: 9, logo: Teams.ATL }} 
          final={true}
        />
        <Game
          away={{ name: "NYI", score: 27, logo: Teams.NYI }} 
          home={{ name: "NYR", score: 34, logo: Teams.NYR }} 
          final={true}
        />
        <Game
          away={{ name: "UTA", score: 27, logo: Teams.UTA }} 
          home={{ name: "TBL", score: 30, logo: Teams.TBL }} 
          final={true}
        />
        <Game
          away={{ name: "COL", score: 32, logo: Teams.COL }} 
          home={{ name: "NSH", score: 35, logo: Teams.NSH }} 
          final={true}
        />
        <Game
          away={{ name: "FLA", score: 16, logo: Teams.FLA }} 
          home={{ name: "TOR", score: 12, logo: Teams.TOR }} 
          final={true}
        />
        <Game
          away={{ name: "CAR", score: 16, logo: Teams.CAR }} 
          home={{ name: "EDM", score: 24, logo: Teams.EDM }} 
          final={true}
        />
        <Game
          away={{ name: "SJS", score: 12, logo: Teams.SJS }} 
          home={{ name: "PIT", score: 17, logo: Teams.PIT }} 
          final={true}
        />
        </div>
      );
    }
  }
  
  class Game extends React.Component {
    constructor(props) {
      super(props);
      this.state = {
        time: this.props.time,
        drive: this.props.drive,
        yard: this.props.yard,
        channel: this.props.channel,
        away: {
          name: this.props.away.name,
          score: this.props.away.score,
          logo: this.props.away.logo
        },
        home: {
          name: this.props.home.name,
          score: this.props.home.score,
          logo: this.props.home.logo
        },
        final: this.props.final,
        winner: this.props.final && this.props.home.score > this.props.away.score ? this.props.home.name : this.props.away.name
      }
    }
   
    render() {
      const { time, drive, yard, away, home, final, winner, channel } = this.state;
      
      return (
        <div className="game__container">
          <div className="game__top-bar">
            <span className={`game__time ${time ? "in-progress" : ""}`}>{ time ? time : "Final" }</span>
            { final ? null : <span className="game__channel">{channel}</span> }
          </div>
          <div className="info-split">
            <div className="team__container">
              <div className="team">
                <img className="team__logo" src={away.logo} alt={`${away.name} team logo`} />
                <p className={`team__name ${!final ? "" : winner === home.name ? "losing-team" : ""}`}>{away.name}</p>
                <p className={`team__score ${!final ? "" : winner === home.name ? "losing-team" : ""}`}>{away.score}</p>
              </div>
              <div className="team">
                <img className="team__logo" src={home.logo} alt={`${away.name} team logo`} />
                <p className={`team__name ${!final ? "" : winner === away.name ? "losing-team" : ""}`}>{home.name}</p>
                <p className={`team__score ${!final ? "" : winner === away.name ? "losing-team" : ""}`}>{home.score}</p>
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
      );
    }
  }
  
  
  ReactDOM.render(<ESPN />, document.getElementById("fakescoreboard"));