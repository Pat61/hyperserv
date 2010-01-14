import sbserver
from ConfigParser import NoOptionError
from xsbs.settings import PluginConfig
from xsbs.events import registerServerEventHandler
from xsbs.timers import addTimer
from xsbs.colors import red, green, colordict
from xsbs.ui import info, error
from xsbs.commands import commandHandler, UsageError
from xsbs.players import clientCount
from xsbs.game import currentMap
from UserPrivilege.userpriv import masterRequired, adminRequired
import irc
import string
import logging

config = PluginConfig('ircbot')
enable = config.getOption('Config', 'enable', 'no') == 'yes'
channel = config.getOption('Config', 'channel', '#xsbs-newserver')
servername = config.getOption('Config', 'servername', 'irc.gamesurge.net')
nickname = config.getOption('Config', 'nickname', 'xsbs-newbot')
port = int(config.getOption('Config', 'port', '6667'))
part_message = config.getOption('Config', 'part_message', 'XSBS - eXtensible SauerBraten Server')
msg_gw = config.getOption('Abilities', 'message_gateway', 'yes') == 'yes'
irc_msg_temp = config.getOption('Templates', 'irc_message', '${white}(${blue}IRC${white}) ${red}${name}${white}: ${message}')
status_message = config.getOption('Templates', 'status_message', '${num_clients} clients on map ${map_name}')
try:
	ipaddress = config.getOption('Config', 'ipaddress', None, False)
except NoOptionError:
	ipaddress = None

# This decode is borrowed from Phenny, under same license as irc.py
def decode(bytes): 
	try: text = bytes.decode('utf-8')
	except UnicodeDecodeError: 
		try: text = bytes.decode('iso-8859-1')
		except UnicodeDecodeError: 
			text = bytes.decode('cp1252')
	return text

class Bot(irc.Bot):
	def __init__(self, nick, name, channel):
		irc.Bot.__init__(self, nick, name, (channel,))
		self.event_handlers = { '251': self.handle_mode,
			'PRIVMSG': self.handle_privmsg,
			'433': self.handle_nick_in_use }
		self.command_handlers = { 'status': self.cmd_status }
		self.connect_complete = False
		self.is_connecting = False
	def run(self, host, port):
		if self.is_connecting or self.connect_complete:
			return
		self.is_connecting = True
		irc.Bot.run(self, host, port)
	def close(self):
		logging.info('Closed')
		self.is_connecting = False
		self.connect_complete = False
		irc.Bot.close(self)
	def handle_connect(self):
		if self.verbose: 
			logging.info('Connected')
		irc.Bot.handle_connect(self)
	def handle_close(self):
		irc.Bot.handle_close(self)
	def dispatch(self, origin, args):
		bytes, event, args = args[0], args[1], args[2:]
		text = decode(bytes)
		try:
			self.event_handlers[event](origin, event, args, bytes)
		except KeyError:
			pass
	def handle_mode(self, origin, event, args, bytes):
		if not self.connect_complete:
			self.handle_complete_connect()
	def handle_privmsg(self, origin, event, args, bytes):
		if args[0] in self.channels:
			if bytes[0] in '.!#@':
				cmd_args = bytes.split(' ', 1)
				try:
					self.handle_command(args[0], origin, cmd_args[0][1:], cmd_args[1])
				except IndexError:
					self.handle_command(args[0], origin, cmd_args[0][1:], '')
			else:
				sbserver.message(irc_msg_temp.substitute(colordict, name=origin.nick, message=bytes))
	def handle_nick_in_use(self, origin, event, args, bytes):
		logging.error('Nickname already in use')
	def handle_command(self, channel, origin, command, bytes):
		try:
			self.command_handlers[command](channel, origin, command, bytes)
		except KeyError:
			pass
	def handle_complete_connect(self):
		self.is_connecting = False
		self.connect_complete = True
		for chan in self.channels:
			self.write(('JOIN', chan))
	def cmd_status(self, channel, origin, command, bytes):
		self.msg(channel, status_message.substitute(colordict, num_clients=str(clientCount()), map_name=currentMap()))
	def broadcast(self, message):
		if not self.connect_complete:
			return
		for chan in self.channels:
			self.msg(chan, message)

irc_msg_temp = string.Template(irc_msg_temp)
status_message = string.Template(status_message)

bot = Bot(nickname, 'xsbs', channel)
if enable:
	bot.run(servername, port)

@commandHandler('ircbot')
@adminRequired
def ircbotCmd(cn, args):
	if args == 'enable':
		bot.run(servername, port)
	elif args == 'disable':
		bot.close()
	else:
		raise UsageError('enable/disable')

event_abilities = {
	'player_active': ('player_connect', lambda x: bot.broadcast(
		'\x032CONNECT\x03        %s (\x037 %i \x03)' % (sbserver.playerName(x), x))),
	'player_disconnect': ('player_disconnect', lambda x: bot.broadcast(
		'\x032DISCONNECT\x03     %s (\x037 %i \x03)' % (sbserver.playerName(x), x))),
	'message': ('player_message', lambda x, y: bot.broadcast(
		'\x033MESSAGE\x03        %s (\x037 %i \x03): %s' % (sbserver.playerName(x), x, y))),
	'map_change': ('map_changed', lambda x, y: bot.broadcast(
		'\x038MAP CHANGE\x03     %s (%s)' % (x, sbserver.modeName(y)))),
	'gain_admin': ('player_claimed_admin', lambda x: bot.broadcast(
		'\x036CLAIM ADMIN\x03    %s (\x037 %i \x03)' % (sbserver.playerName(x), x))),
	'gain_master': ('player_claimed_master', lambda x: bot.broadcast(
		'\x036CLAIM MASTER\x03   %s (\x037 %i \x03)' % (sbserver.playerName(x), x))),
	'auth': ('player_auth_succeed', lambda x, y: bot.broadcast(
		'\x036AUTH\x03           %s (\x037 %i \x03) as %s@sauerbraten.org' % (sbserver.playerName(x), x, y))),
	'relinquish_admin': ('player_released_admin', lambda x: bot.broadcast(
		'\x036RELINQ ADMIN\x03   %s (\x037 %i \x03)' % (sbserver.playerName(x), x))),
	'relinquish_master': ('player_released_master', lambda x: bot.broadcast(
		'\x036RELINQ MASTER\x03  %s (\x037 %i \x03)' % (sbserver.playerName(x), x))),
}

for key in event_abilities.keys():
	if config.getOption('Abilities', key, 'no') == 'yes':
		ev = event_abilities[key]
		registerServerEventHandler(ev[0], ev[1])
del config

