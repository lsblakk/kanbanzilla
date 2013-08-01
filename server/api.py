from flask import Flask, request, make_response
import requests
import json
import uuid


app = Flask(__name__)

login_url = 'https://bugzilla.mozilla.org/index.cgi'
bugzilla_url = 'https://api-dev.bugzilla.mozilla.org/latest'

users = {}

@app.route('/api/board', defaults={'board_id':''})
@app.route('/api/board/<board_id>')
def board_endpoint(board_id):
  return 'this is the board endpoint'


@app.route('/api/logintest', methods=['GET'])
def logintest():
  # look up the person with their cookie
  print(users)
  cookie_token = str(request.cookies.get('token'))
  print(cookie_token)
  if cookie_token is not None:
    if users.has_key(cookie_token):
      user = users[cookie_token]
      return 'Welcome back {0}, your bugzilla cookies are, login: {1}, logincookie: {2}'.format(user['username'], user['Bugzilla_login'], user['Bugzilla_logincookie'])
    else:
      return 'Not the right cookie, sorry'
  else:
    return 'No cookie, sorry'


@app.route('/api/logout', methods=['POST'])
def logout():
  cookie_token = str(request.cookies.get('token'))
  response = make_response('logout')
  response.set_cookie('token', '', expires=0)
  response.set_cookie('username', '', expires=0)
  if cookie_token is not None:
    if users.has_key(cookie_token):
      users.pop(cookie_token, None)
  return response

@app.route('/api/login', methods=['POST'])
def login():
  login_payload = {
    'Bugzilla_login': request.json['login'],
    'Bugzilla_password': request.json['password'],
    'Bugzilla_remember': 'on',
    'GoAheadAndLogIn': 'Log in'
  }
  login_response = {}
  r = requests.post(login_url, data=login_payload)
  cookies = requests.utils.dict_from_cookiejar(r.cookies)
  if cookies.has_key('Bugzilla_login'):
    # set a cookie for the client application and use as a key into the memcached
    # to retrieve these two cookies to decorate api requests with.
    token = str(uuid.uuid4())
    users[token] = {
      'Bugzilla_login': cookies['Bugzilla_login'],
      'Bugzilla_logincookie': cookies['Bugzilla_logincookie'],
      'username': request.json['login']
    }
    login_response['result'] = 'success'
    login_response['token'] = token
    response = make_response(json.dumps(login_response))
    response.set_cookie('token', token)
    response.set_cookie('username', request.json['login'])
    return response
  else:
    print('login failed')
    login_response['result'] = 'failed'
    response = make_response(json.dumps(login_response))
    return response


def augment_with_auth(request_arguments, cookie_token):
  if cookie_token is not None:
    if users.has_key(cookie_token):
      request_arguments['userid'] = users[cookie_token]['Bugzilla_login']
      request_arguments['cookie'] = users[cookie_token]['Bugzilla_logincookie']
  return request_arguments


@app.route('/api/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_proxy(path):
  path = str(path)
  request_arguments = dict(request.args)
  cookie_token = str(request.cookies.get('token'))
  augment_with_auth(request_arguments, cookie_token)
  print(request_arguments)

  print(request.path)
  r = requests.request(request.method, bugzilla_url + '/{0}'.format(path), params=request_arguments, data=request.form)
  print(r.url)
  return r.text

@app.route('/', defaults={'path':''})
@app.route('/<path:path>')
def catch_all(path):
  return 'should be the index.html file, let angular handle the route - {0}'.format(path)

if __name__ == '__main__':
  app.debug = True
  app.run()