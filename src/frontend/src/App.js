import React from 'react';
import './App.css';
import { io } from "socket.io-client";
import axios from 'axios';

const intervalMilliseconds = 10000;
let endPoint = "https://localhost:3000";
let socket = io(endPoint, {
  autoConnect: false
});
let intervalId = null;


class App extends React.Component {

  constructor(props) {
    super(props);
    this.state = {
      username: '',
      password: '',
      authenticated: true,
      publishString: '',
      incomingMessages: ''
    };

    this.publishMessage = this.publishMessage.bind(this);
    this.handleInputChange = this.handleInputChange.bind(this);
    this.handleSubmit = this.handleSubmit.bind(this);
    this.logout = this.logout.bind(this);
  }

  handleInputChange(event) {
    const target = event.target;
    const value = target.value;
    const name = target.name;

    this.setState({
      [name]: value
    });
  }

  handleSubmit(event) {

    this.login();
    event.preventDefault();

  }

  componentDidMount() {

    this.check_authentication();

  }

  publishMessage() {
    const { publishString } = this.state;
    socket.emit('publish', publishString);
  }

  login() {
    const { username, password } = this.state;
    axios.post(endPoint + '/api/login', {
      "username": username,
      "password": password
    }).then(response => {
      this.setState({ authenticated: response.data.authenticated });
      this.start_socket();
    });
  }

  logout() {

    axios.get(endPoint + '/api/logout')
      .then(response => {
        this.setState({ authenticated: response.data.authenticated });
        this.close_socket();
      });
  }

  close_socket() {
    clearInterval(intervalId);
    socket.off();
    socket.disconnect();
  }

  start_socket() {

    socket.connect();

    intervalId = setInterval(() => {

      axios.get(endPoint + '/api/authenticated')
        .then(response => {
          this.setState({ authenticated: response.data.authenticated });
          const { authenticated } = this.state;
          if (!authenticated) {
            this.close_socket();
          }
        });

    }, intervalMilliseconds);

    socket.on('connect', () => {

    });

    socket.on('message', msg => {
      console.log(msg);
      const date = new Date();
      let dateString = date.toISOString();
      this.setState(prevState => ({ incomingMessages: prevState.incomingMessages.concat(`\n${dateString} - ${JSON.stringify(msg["payload"])}`) }))
    });

  }

  check_authentication() {

    axios.get(endPoint + '/api/authenticated')
      .then(response => {
        this.setState({ authenticated: response.data.authenticated });
        const { authenticated } = this.state;
        if (authenticated) {
          this.start_socket();
        }
      });
  }

  render() {
    const { authenticated } = this.state;
    return (
      <div className="App">
        <header className="App-header">
          {!authenticated && <form className="row row-cols-lg-auto g-3 align-items-center" onSubmit={this.handleSubmit}>
            <div className="col-12">
              <input id="username" name="username" placeholder="Username" type="text" className="form-control" value={this.state.username} onChange={this.handleInputChange} />
            </div>
            <div className="col-12">
              <input id="password" name="password" placeholder="Password" type="password" className="form-control" value={this.state.password} onChange={this.handleInputChange} />
            </div>
            <div className="col-12">
              <button type="submit" className="btn btn-primary">Login</button>
            </div>
          </form>}
          {authenticated &&
            <div>
              <div className="App-logout">
                <button className="btn btn-primary" onClick={this.logout}>Logout</button>
              </div>
              <br />
              <div className="mb-3">
                <label htmlFor="incoming_messages" className="form-label">Incoming messages from AWS IoT Core</label>
                <div id="incoming_messages_help" className="form-text">Subscribed to the topic AWS_IOT_THING_NAME/publish</div>
                <textarea disabled rows="5" className="form-control" id="incomingMessages" name="incomingMessages" aria-describedby="incoming_messages_help" value={this.state.incomingMessages} onChange={this.handleInputChange} />
              </div>
              <div className="mb-3">
                <label htmlFor="publish_string" className="form-label">Publish a message to AWS IoT Core</label>
                <div id="publishHelp" className="form-text">Published to the topic AWS_IOT_THING_NAME/subscribe</div>
                <input id="publishString" name="publishString" placeholder="String to publish" type="text" className="form-control" value={this.state.publishString} onChange={this.handleInputChange} />
              </div>
              <button className="btn btn-success" onClick={this.publishMessage}>Publish</button>
            </div>
          }

        </header>
      </div>
    );
  }
}

export default App;
