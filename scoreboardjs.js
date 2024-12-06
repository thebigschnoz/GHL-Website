// JavaScript Document
class ESPN extends React.Component {
  render() {
    return (
      <main>
        <ScoreBoard />
        <Navigation />
      </main>
    );
  }
}

class ScoreBoard extends React.Component {
  render() {
    const Logo = "http://loodibee.com/wp-content/uploads/nfl-";
    const Teams = {
      ARI: `${Logo}arizona-cardinals-team-logo-2-768x768.png`,
      ATL: `${Logo}atlanta-falcons-team-logo-2-768x768.png`,
      BAL: `${Logo}baltimore-ravens-team-logo-2-768x768.png`,
      BUF: `${Logo}buffalo-bills-team-logo-2-768x768.png`,
      CAR: `${Logo}carolina-panthers-team-logo-2-768x768.png`,
      CHI: `${Logo}chicago-bears-team-logo-2-768x768.png`,
      CIN: `${Logo}cincinnati-bengals-team-logo-768x768.png`,
      CLE: `${Logo}cleveland-browns-team-logo-2-768x768.png`,
      DAL: `${Logo}dallas-cowboys-team-logo-2-768x768.png`,
      DET: `${Logo}detroit-lions-team-logo-2-768x768.png`,
      GB: `${Logo}green-bay-packers-team-logo-2-768x768.png`,
      IND: `${Logo}indianapolis-colts-team-logo-2-768x768.png`,
      KC: `${Logo}kansas-city-chiefs-team-logo-2-768x768.png`,
      LAR: `${Logo}los-angeles-rams-team-logo-2-768x768.png`,
      MIA: `${Logo}miami-dolphins-team-logo-2-768x768.png`,
      MIN: `${Logo}minnesota-vikings-team-logo-2-768x768.png`,
      NO: `${Logo}new-orleans-saints-team-logo-2-768x768.png`,
      NYG: `${Logo}new-york-giants-team-logo-2-768x768.png`,
      NYJ: `${Logo}new-york-jets-team-logo-768x768.png`,
      PIT: `${Logo}pittsburgh-steelers-team-logo-2-768x768.png`,
      TB: `${Logo}tampa-bay-buccaneers-team-logo-2-768x768.png`,
      TEN: `${Logo}tennessee-titans-team-logo-2-768x768.png`,
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
          away={{ name: "BAL", score: 49, logo: Teams.BAL }} 
          home={{ name: "CIN", score: 13, logo: Teams.CIN }}
          final={true}
        />
        <Game
          away={{ name: "BUF", score: 16, logo: Teams.BUF }} 
          home={{ name: "CLE", score: 19, logo: Teams.CLE }}
          final={true}
        />
        <Game
          away={{ name: "ATL", score: 26, logo: Teams.ATL }} 
          home={{ name: "NO", score: 9, logo: Teams.NO }} 
          final={true}
        />
        <Game
          away={{ name: "NYG", score: 27, logo: Teams.NYG }} 
          home={{ name: "NYJ", score: 34, logo: Teams.NYJ }} 
          final={true}
        />
        <Game
          away={{ name: "ARI", score: 27, logo: Teams.ARI }} 
          home={{ name: "TB", score: 30, logo: Teams.TB }} 
          final={true}
        />
        <Game
          away={{ name: "KC", score: 32, logo: Teams.KC }} 
          home={{ name: "TEN", score: 35, logo: Teams.TEN }} 
          final={true}
        />
        <Game
          away={{ name: "MIA", score: 16, logo: Teams.MIA }} 
          home={{ name: "IND", score: 12, logo: Teams.IND }} 
          final={true}
        />
        <Game
          away={{ name: "CAR", score: 16, logo: Teams.CAR }} 
          home={{ name: "GB", score: 24, logo: Teams.GB }} 
          final={true}
        />
        <Game
          away={{ name: "LAR", score: 12, logo: Teams.LAR }} 
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

class Navigation extends React.Component {  
  render() {
    const logo = "";
    
    return (
      <nav className="nav__container">
        <div className="nav__content">
          <div className="logo__container">
            <img src={logo} />
          </div>
          <ul className="nav__items">
            <li>NFL</li>
            <li>NHL</li>
            <li>NBA</li>
            <li>MLB</li>
            <li>NCAAF</li>
            <li>Soccer</li>
            <li>MMA</li>
          </ul>
        </div>
      </nav>
    );
  }
}

ReactDOM.render(<ESPN />, document.getElementById("sup"));