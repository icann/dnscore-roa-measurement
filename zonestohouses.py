#!/usr/bin/env python3
'''
Copyright (c) 2020, Internet Corporation for Assigned Names and Numbers
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the <organization> nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''

import json
import sys

# normalize (string)
#
# Purpose: Used to smooth over suspected typos in IANA Tech Operator names.
#
# string : name as it appears in the root database's Tech Operator
# return : altered string

def normalize (string):
	return string.replace ('-','').replace('  ',' ').replace(',','').upper()

# get_DNShouse (houses, names)
#
# Purpose: Selects the house element in the list "houses" corresponding to any name in the list of names
#
# What if names has a list of names that each match different houses? (Don't know.)
#
# houses: list of class DNShouse objects
# names: a list of names
#
# returns the class DNSHouse object corresponding to what is in names, even if a new has to be created

def get_DNShouse (houses, names):
	found=False
	for obj in houses:
		for name in names:
			if name in obj.title:
				found=True
				break
		if found:
			break
	if not found:
		obj=DNShouse(names)
		houses.append (obj)
	for name in names:
		obj.title.add(name)
	return obj
#end def get_DNShouse (name):

#
# class DNShouse:
#
# Purpose: data structure presenting a house by name (title) and sets of zones falling into categories
#
# categories are gTLD, ccTLD, revMap, and so on.

class DNShouse:
	def __init__ (self, title):
		self.title = set()
		for name in title:
			self.title.add (name)
		self.zonesbycat=dict()
	#end def __init__ (self, title):
#end class DNShouse:

# buildhouses
#
# Purpose: given a list (dict) of zones, segment them into houses based on common fingerprints
#
# The fingerprint use is a common SOA rname field and IANA Tech contact
#
# Each zone can have one of each, but sets of zones with a common RNAME may have many IANA Tech's and vice versa.
# For the most part, collecting all zones with the same RNAME and IANA Tech yields distinct sets, but in some
# cases "houses" are wedded together when a zone is in tranistion from operator to operator.
#
# This logic is not foolproof.  An operator may decide to isolate some zones from other and this cannot defeat
# that effort.  It's tempting to add some "known bridges" but that is subjective and won't stand the test of time.
#
#
# zones : a dict of zones indicating their house-information
#
# returns a dict of houses

def buildhouses (zones):
	houses=list()
	zonesbyrname=dict()
	# itc stands for iana technical contact
	itcbyrname=dict()
	# rname means the name in the zone's SOA RR, second field
	rnamebyitc=dict()
	# arcs - imaginary curved lines between itc and rname
	arcs=dict()
	# hmmm, for a zone, its itc and rname values
	zonecolors=dict()

	for zone in zones.keys():
		zoneobj=zones[zone]

		othercategories='arpa, enum, IETFSpecialUse, sub-enum, tTLD'
		if zoneobj['category'] in othercategories: #=='IETFSpecialUse':
			continue

		if zoneobj['status']!='ACTIVE': # turns out there are inactive ACTIVE zones, but they drop out elsewhere
			continue

		rname=zoneobj['RNAME-field'].lower()
		itc=normalize(zoneobj['IANA-registry-tech'])

		if rname=='rnamenotavailable':
			continue

		if rname not in zonesbyrname.keys():
			zonesbyrname[rname]=set()
		if rname not in itcbyrname.keys():
			itcbyrname[rname]=set()
		if itc not in rnamebyitc.keys():
			rnamebyitc[itc]=set()

		zonesbyrname[rname].add(zone)
		if itc!='UNSET':
			itcbyrname[rname].add(itc)
		rnamebyitc[itc].add(rname)

		if itc!='UNSET':
			if (rname,itc) not in arcs.keys():
				arcs[(rname,itc)]=set()
			arcs[(rname,itc)].add(zone)

		zonecolors[zone]=dict()
		zonecolors[zone]['rname']=rname
		zonecolors[zone]['itc']=itc
		zonecolors[zone]['cat']=zoneobj['category']

	for itc in rnamebyitc.keys():
		if itc=='UNSET':
			continue
		for rname in itcbyrname.keys():
			try:
				if (rname,itc) in arcs.keys():
					if len (arcs[(rname,itc)]) == 1 and len (rnamebyitc[itc]) > 1 and len (itcbyrname[rname]) > 1:
						for zone in arcs[(rname,itc)]:
							itclist=list(itcbyrname[rname])
							if itc!=itclist[0]:
								zonecolors[zone]['itc']=itclist[0]
							else:
								zonecolors[zone]['itc']=itclist[1]
			except:
				pass

	for zone in zonecolors.keys():
		if zonecolors[zone]['itc']=='UNSET':
			dnshouseobj=get_DNShouse(houses,[zonecolors[zone]['rname']])
		else:
			dnshouseobj=get_DNShouse(houses,[zonecolors[zone]['rname'],zonecolors[zone]['itc']])

		if zonecolors[zone]['cat'] not in dnshouseobj.zonesbycat.keys():
			dnshouseobj.zonesbycat[zonecolors[zone]['cat']]=set()
		dnshouseobj.zonesbycat[zonecolors[zone]['cat']].add (zone)

	return houses
#end buildhouses

# getobject (url)
#
# Purpose : do a web-fetch of url
#
# url : string
# returns the text at the URL

def getobject (url):
	try:
		response = requests.get(url)
		response.raise_for_status()
	except BaseException as e:
		print (f'Failed to load {url}')
		print (f'Exception {e}')
		sys.exit()
	return response.text
#end def getobject

# read_maps
#
# Purpose : read the DNS Core Census files (once called maps)
#
# returns dicts of zones, nameservers, addresses and the date of the data (assuming all are the same date)

def read_maps ():
	urlbase='https://observatory.research.icann.org/core-mapping/'
	zonestructure=json.loads(getobject(f'{urlbase}allzones.json'))
	zonedate=zonestructure['Mapping-Work-Started'][0:10]
	zones=zonestructure['CoreZones']
	nameservers=json.loads(getobject(f'{urlbase}allnameservers.json'))['CoreNameservers']
	addresses=json.loads(getobject(f'{urlbase}alladdresses.json'))['CoreAddresses']
	return zones, nameservers, addresses, zonedate
#end def read_maps

if __name__ == '__main__':
	# the main here is for unit testing, it spits out (stdout) the DNS houses

	import requests

	zones,nameservers,addresses,workingdate=read_maps()

	all_houses=buildhouses (zones)

	housetable=list()
	for house in all_houses:
		try:
			gtldzones=len(house.zonesbycat['gTLD'])
		except:
			gtldzones=0
		try:
			subgtldzones=len(house.zonesbycat['sub-gTLD'])
		except:
			subgtldzones=0
	
		try:
			cctldzones=len(house.zonesbycat['ccTLD'])
		except:
			cctldzones=0
		try:
			subcctldzones=len(house.zonesbycat['sub-ccTLD'])
		except:
			subcctldzones=0
	
		try:
			revmapzones=len(house.zonesbycat['revMap'])
		except:
			revmapzones=0
		try:
			subrevmapzones=len(house.zonesbycat['sub-revMap'])
		except:
			subrevmapzones=0
	
		totalzones=gtldzones+cctldzones+revmapzones
		allzones=totalzones+subgtldzones+subcctldzones+subrevmapzones
	
		title=list()
		for item in house.title:
			if item == item.lower():
				title.append(item)
	
		housetable.append (f'{totalzones:5} {allzones:5} {gtldzones:5} {cctldzones:5} {revmapzones:5} {"R-"+"/".join(title)}')
	
	for tab in sorted(housetable, reverse=True):
		print (tab)
#end if __name__ == '__main__':
