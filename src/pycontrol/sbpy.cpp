/*
 *   Copyright (C) 2009 Gregory Haynes <greg@greghaynes.net>
 *
 *   This program is free software; you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation; either version 2 of the License, or
 *   (at your option) any later version.
 *
 *   This program is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *   GNU General Public License for more details.
 *
 *   You should have received a copy of the GNU General Public License
 *   along with this program; if not, write to the
 *   Free Software Foundation, Inc.,
 *   51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
 */

#include "sbpy.h"

#include <string>
#include <iostream>

namespace SbPy
{

#define SBPY_ERR(x) \
	if(!x) \
	{ \
		if(PyErr_Occurred()) \
			PyErr_Print(); \
		return false;\
	}

bool initPy(const char *pyscripts_path)
{
	PyObject *pFunc, *pArgs, *pValue, *triggerFunc, *pluginsModule, *eventsModule;
	
	std::string path;
	pluginsModule = PyImport_ImportModule("sbplugins");
	SBPY_ERR(pluginsModule)
	eventsModule = PyImport_ImportModule("sbevents");
	SBPY_ERR(eventsModule)
	pFunc = PyObject_GetAttrString(pluginsModule, "loadPlugins");
	SBPY_ERR(pFunc)
	if(!PyCallable_Check(pFunc))
	{
		fprintf(stderr, "Error: loadPlugins function could not be loaded.\n");
		return false;
	}
	pArgs = PyTuple_New(0);
	pValue = PyObject_CallObject(pFunc, pArgs);
	Py_DECREF(pArgs);
	Py_DECREF(pFunc);
	if(!pValue)
	{
		PyErr_Print();
		return false;
	}
	Py_DECREF(pValue);
	triggerFunc = PyObject_GetAttrString(eventsModule, "triggerEvent");
	SBPY_ERR(triggerFunc);
	if(!PyCallable_Check(triggerFunc))
	{
		fprintf(stderr, "Error: triggerEvent function could not be loaded.\n");
		return false;
	}
	Py_DECREF(triggerFunc);
	Py_DECREF(pluginsModule);
	Py_DECREF(eventsModule);
	
	return true;
}

void deinitPy()
{
	Py_Finalize();
}

bool triggerEvent(const char *name, std::vector<PyObject*> *args)
{
	if(!args)
		return true;
	PyObject *pArgs, *pArgsArgs, *pName, *pValue, *pFunc, *eventsModule;
	std::vector<PyObject*>::const_iterator itr;
	int i = 0;
	
	eventsModule = PyImport_ImportModule("sbevents");
	SBPY_ERR(eventsModule)
	pArgs = PyTuple_New(2);
	pName = PyString_FromString(name);
	SBPY_ERR(pName)
	PyTuple_SetItem(pArgs, 0, pName);
	if(args)
	{
		pArgsArgs = PyTuple_New(args->size());
		for(itr = args->begin(); itr != args->end(); itr++)
		{
			PyTuple_SetItem(pArgsArgs, i, *itr);
			i++;
		}
	}
	else
		pArgsArgs = PyTuple_New(0);
	PyTuple_SetItem(pArgs, 1, pArgsArgs);
	pFunc = PyObject_GetAttrString(eventsModule, "triggerEvent");
	SBPY_ERR(pFunc)
	pValue = PyObject_CallObject(pFunc, pArgs);
	Py_DECREF(pFunc);
	Py_DECREF(pName);
	Py_DECREF(pArgs);
	Py_DECREF(pArgsArgs);
	Py_DECREF(eventsModule);
	if(!pValue)
	{
		fprintf(stderr, "Error triggering event.\n");
		return false;
	}
	Py_DECREF(pValue);
	return true;
}

bool triggerEventInt(const char *name, int cn)
{
	std::vector<PyObject*> args;
	PyObject *pCn = PyInt_FromLong(cn);
	args.push_back(pCn);
	bool val = triggerEvent(name, &args);
	Py_DECREF(pCn);
	return val;
}

bool triggerEventIntString(const char *name, int cn, const char *text)
{
	std::vector<PyObject*> args;
	PyObject *pText = PyString_FromString(text);
	PyObject *pCn = PyInt_FromLong(cn);
	args.push_back(pText);
	args.push_back(pCn);
	bool val = triggerEvent(name, &args);
	Py_DECREF(pCn);
	return val;
}

#undef SBPY_ERR

}