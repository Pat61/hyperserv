from hypershade.database import database
import datetime

def checkForExpired(function):
	def newfunction(*args):
		results=function(*args)
		if len(results)>0 and type(results[0]) is not tuple:
			ban=results
			if expired(ban):
				del bandatabase[ban[0]]
				raise KeyError("No such ban: %s" % (ban[0]))
			return formatExpiration(ban)
		else:
			def checkExpired(ban):
				if expired(ban):
					del bandatabase[ban[0]]
					return False
				else:
					return True
			return map(formatExpiration,filter(checkExpired,results))
	return newfunction

def expired(ban):
	if ban[1] is None:
		#permanent ban
		return False
	return ban[1]<datetime.datetime.utcnow()

class BanDatabase():
	def __iter__(self):
		for user in self.items():
			yield user[0]
	
	@checkForExpired
	def items(self):
		database.query('SELECT * FROM `bans` ORDER BY `bans`.`expires` DESC')
		return tuple(database.cursor.fetchall())
	
	@checkForExpired
	def __getitem__(self,name):
		database.query('SELECT * FROM `bans` WHERE `id` = "%s" ORDER BY `bans`.`expires` DESC LIMIT 1' % (name))
		
		if database.cursor.rowcount==0:
			raise KeyError("No such ban: %s" % (name))
		
		return database.cursor.fetchone()
	
	def __setitem__(self,name,values):
		try:
			del self[name]
		except:
			pass
		database.query('INSERT INTO `bans` VALUES ("%s","%s","%s")' % (name,values[0],values[1]))
	
	def __delitem__(self,name):
		database.query('DELETE FROM `bans` WHERE `id` = "%s"' % (name))
	
	def cleargbans(self):
		database.query('DELETE FROM `bans` WHERE `reason` = "gban"')
	
	def __repr__(self):
		return repr(self.items())
	
	@checkForExpired
	def search(self,names):
		if type(names) is str:
			#probably a mistake, only one is wanted
			return (self[names],)
		string = ' OR '.join(map(lambda name: '`id` = "%s"' % name,names))
		database.query('SELECT * FROM `bans` WHERE %s ORDER BY `bans`.`expires` DESC' % (string))
		return tuple(database.cursor.fetchall())

def formatExpiration(time):
	if type(time) is tuple:
		return (time[0],formatExpiration(time[1]),time[2])
	if time==None:
		return "permanently"
	return time.strftime("till %b %d %I:%M%p")

bandatabase=BanDatabase()
