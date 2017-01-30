var api_key;

function messageReceived(text, id, channel)
{
    var data = JSON.parse(window.atob(text));
    api_key = data["api_key"];
	// Do more things with the API data that was received
}

var pushstream = new PushStream
(
	{
      host: window.location.hostname,
      port: window.location.port,
      modes: "longpolling",
      tagArgument: 'tag',
      timeArgument: 'time',
      timeout: 30000,
      messagesPublishedAfter: 5,
      urlPrefixLongpolling: '/api/v1/push.subscribe_longpoll'
     }
);

pushstream.onmessage = messageReceived;
pushstream.addChannel(shibboleth_login_token_id);
pushstream.connect();