import sbevents, sbserver, sbtools, pygeoip
from ConfigParser import ConfigParser
import string

db = pygeoip.Database('geoip/GeoIP.dat')
conf = ConfigParser()
conf.read('geoip/plugin.conf')
template = sbtools.green('$user') + ' has connected from ' + sbtools.orange('$country')

if conf.has_option('Config', 'template'):
	template = string.Template(conf.get('Config', 'template'))
else:
	template = string.Template(template)
del conf

def getCountry(ip): 
	 return db.lookup(sbtools.ipLongToString(ip)).country

def announce(cn):
	msg = template.substitute(user=sbserver.playerName(cn), country=getCountry(sbserver.playerIpLong(cn)))
	sbserver.message(msg)

def init():
	sbevents.registerEventHandler("player_active", announce)

init()