from twisted.protocols.basic import LineReceiver
from twisted.internet import reactor, protocol
from twisted.internet.task import LoopingCall

from hypershade.config import config
from hyperserv.notices import serverNotice
from hyperserv.events import triggerServerEvent, eventHandler
from hypershade.util import ipLongToString

import sbserver
import time
import logging

class AuthRequest(object):
	def __init__(self, id, cn, name):
		self.id = id
		self.cn = cn
		self.name = name

class AuthError(Exception):
	pass

class ResponseHandler(object):
	def __init__(self, factory):
		self.key_handlers = {
			'succreg': self.succreg,
			'failreg': self.failreg,
			'succauth': self.succauth,
			'failauth': self.failauth,
			'chalauth': self.chalauth,
			'cleargbans': self.cleargbans,
			'addgban': self.addgban
			}
		self.auth_id_map = {}
		self.factory = factory
		self.last_auth_id = -1
		self.responses_needed = 0
	def handle(self, response):
		key = response.split(' ')[0]
		try:
			self.key_handlers[key](response[len(key)+1:])
		except KeyError:
			raise AuthError('Invalid response key: %s' % key)
		if self.responses_needed <= 0:
			self.responses_needed = 0
			# We are going to keep connections open
			#self.factory.client.transport.loseConnection()
	def succreg(self, args):
		self.responses_needed -= 1
		serverNotice('Master server registration successful')
		triggerServerEvent('master_registration_succeeded', ())
	def failreg(self, args):
		self.responses_needed -= 1
		serverNotice('Master server registration failed: %s' % args)
		triggerServerEvent('master_registration_failed', ())
	def cleargbans(self, args):
		triggerServerEvent('master_cleargbans', ())
	def addgban(self, args):
		triggerServerEvent('master_addgban', (args,))
	def pop_auth(self, auth_id):
		auth = self.auth_id_map[auth_id]
		del self.auth_id_map[auth_id]
		return auth
	def succauth(self, args):
		self.responses_needed -= 1
		auth_id = args.split(' ')[0]
		try:
			auth = self.pop_auth(int(auth_id))
		except KeyError:
			raise AuthError('Could not find matching auth request for given auth request id')
			return
		triggerServerEvent('player_auth_succeed', (auth.cn, auth.name))
	def failauth(self, args):
		self.responses_needed -= 1
		auth_id = args.split(' ')[0]
		try:
			self.pop_auth(int(auth_id))
		except KeyError:
			raise AuthError('Could not find matching auth request for given auth request id')
		triggerServerEvent('player_auth_fail', (auth.cn, auth.name))
	def chalauth(self, args):
		args = args.split(' ')
		auth_id = args[0]
		auth_challenge = args[1]
		try:
			auth_req = self.auth_id_map[int(auth_id)]
		except KeyError:
			raise AuthError('Could not find matching auth request for given auth request id')
		sbserver.authChallenge(auth_req.cn, auth_req.id, auth_challenge)
	def nextAuthId(self):
		self.last_auth_id += 1
		return self.last_auth_id

class MasterClient(LineReceiver):
	delimiter = '\n'
	def connectionMade(self):
		serverNotice('Connected to master server')
		self.factory.clientConnected(self)
	def connectionLost(self, reason):
		self.factory.clientDisconnected(self)
	def lineReceived(self, line):
		self.factory.response_handler.handle(line)

class MasterClientFactory(protocol.ClientFactory):
	protocol = MasterClient
	def __init__(self):
		self.response_handler = ResponseHandler(self)
		self.client = None
		self.send_buffer = []
	def clientConnected(self, client):
		if self.client != None:
			del self.client
		self.client = client
		for data in self.send_buffer:
			self.client.sendLine(data)
		del self.send_buffer[:]
	def clientDisconnected(self, client):
		self.client = None
		self.response_handler.auth_id_map.clear()
	def send(self, data):
		if self.client == None:
			ip = sbserver.ip()
			if ip != None:
				reactor.connectTCP(config['masterhost'], int(config['masterport']), self, 30, (sbserver.ip(), sbserver.port()))
			else:
				reactor.connectTCP(config['masterhost'], int(config['masterport']), self)
			self.send_buffer.append(data)
		else:
			self.client.sendLine(data)

factory = MasterClientFactory()

def registerServer():
	factory.response_handler.responses_needed += 1
	factory.send('regserv %i' % sbserver.port())

if config['masterregister']=="yes":
	registerRepeater = LoopingCall(registerServer)
	registerRepeater.start(int(config['masterregisterinterval']))

@eventHandler('player_auth_request')
def authRequest(cn, name):
	factory.response_handler.responses_needed += 1
	req = AuthRequest(factory.response_handler.nextAuthId(), cn, name)
	factory.response_handler.auth_id_map[req.id] = req
	factory.send('reqauth %i %s' % (req.id, req.name))

@eventHandler('player_auth_challenge_response')
def authChallengeResponse(cn, id, response):
	factory.send('confauth %i %s' % (id, response))

