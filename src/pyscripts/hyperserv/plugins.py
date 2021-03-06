import os, sys

import hypershade

import hyperserv.notices
import hyperserv.clientcommands
import hyperserv.servercommands
import hyperserv.ingame

import editing

class PluginManager(object):
	def __init__(self, plugins_path='plugins'):
		self.plugins_path = plugins_path
		self.plugin_modules = []
	def loadPlugins(self):
		files = os.listdir(self.plugins_path)
		for file in files:
			if file[0] != '.':
				self.plugin_modules.append(__import__(os.path.basename(self.plugins_path) + '.' + os.path.splitext(file)[0]))

pm = PluginManager()
pm.loadPlugins()
#setup_all()
#create_all()
