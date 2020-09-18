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
import ipaddress
import datetime
import os
import requests
import zonestohouses # another file in the same directory
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D

# Purpose: Measure ROA deployment for routes leading to nameservers for zones in the DNS Core
#
# Results: Plots of "yes/no" for various groupings of routes (IPv4 v IPv6), and zones (gTLDs v ccTLDs)
# plus JSON and CSV files

def executablefileanddirectory ():
	# will place results direcory in same place as executable
	finalslash=sys.argv[0].rfind('/')
	if finalslash > -1:
		wd=sys.argv[0][:finalslash+1]
		ex=sys.argv[0][finalslash+1:]
	else:
		wd='./'
		ex=sys.argv[0]
	return ex,wd
#end def executablefileanddirectory

def getobject (url):
	# a simple cover for requests
	try:
		response = requests.get(url)
		response.raise_for_status()
	except:
		if os.isatty (sys.stdin.fileno()):
			print (f'Failed to load {url}')
		sys.exit()
	return response.text
#end def getobject

def read_maps ():
	# access to the DNS Core Census (in alpha)
	urlbase='https://observatory.research.icann.org/core-mapping/'
	zonestructure=json.loads(getobject(f'{urlbase}allzones.json'))
	zonedate=zonestructure['Mapping-Work-Started'][0:10]
	zones=zonestructure['CoreZones']
	nameservers=json.loads(getobject(f'{urlbase}allnameservers.json'))['CoreNameservers']
	addresses=json.loads(getobject(f'{urlbase}alladdresses.json'))['CoreAddresses']
	return zones, nameservers, addresses, zonedate
#end def read_maps

def roacoverage (addressFamilyList=None, zoneCategoryList=None, zoneList=None, rnameList=None):
	# counts roa coverage based on selected criteria
	zoneset=set() # set of zones matching criteria
	tldset=set() # set of tlds (zones: gTLD, ccTLD, and RIR reverse map) matching criteria
	addressset=set() # set of addresses matching criteria
	nameserverset=set() # set of nameservers matching criteria (with nameserver being whats in the NS record)
	setofyes=set() # set of route origins with ROA matching criteria
	setofno=set() # set of route origins without ROA matching criteria
	pctZoneList=list() # pct for a matching zone
	pctTLDList=list() # pct for a matcing zone that is a tld

	for zone in zones.keys():
		# per zone sets of yes and no
		zonesetofyes=set()
		zonesetofno=set()

		#criteria kick-out code
		if zoneList is not None:
			if zone not in zoneList:
				continue
		zoneobj=zones[zone]
		if zoneCategoryList is not None:
			if zoneobj['category'] not in zoneCategoryList:
				continue
		if rnameList is not None:
			if zoneobj['RNAME-field'] not in rnameList:
				continue
		for ns in zoneobj['authnameservers']:
			nsobj=nameservers[ns]
			for addr in nsobj["authaddresses"]:
				addrobj=addresses[addr]
				if addressFamilyList is not None:
					if type(ipaddress.ip_network(addr)) not in addressFamilyList:
						continue
				# do the counting
				zoneset.add(zone)
				if zoneobj['category'] in 'ccTLD gTLD revMap'.split():
					tldset.add(zone)
				nameserverset.add(ns)
				addressset.add(addr)
				for ro in addrobj["Route-Originations"]:
					ro_str=f'{ro["Route-Origin-Prefix"]}-{ro["Route-Origin-AutNum"]}'
					if ro["Route-Origin-HasROA"]:
						setofyes.add(ro_str)
						zonesetofyes.add(ro_str)
					else:
						setofno.add(ro_str)
						zonesetofno.add(ro_str)
				#end for ro in addrobj["Route-Originations"]:
			#end for addr in nsobj["authaddresses"]:
		#end for ns in zoneobj['authnameservers']:

		if len(zonesetofyes)+len(zonesetofno) > 0:
			pct=int(100*len(zonesetofyes)/(len(zonesetofyes)+len(zonesetofno)))
			pctZoneList.append (pct)
			if zoneobj['category'] in 'ccTLD gTLD revMap'.split():
				pctTLDList.append (pct)
		#end if len(zonesetofyes)+len(zonesetofno) > 0:
	#end for zone in zones.keys():

	return (len(setofyes), len(setofno), len(zoneset), len(tldset), len (nameserverset), len (addressset), pctZoneList, pctTLDList)
#def roacoverage (addressFamilyList=None,zoneCategoryList=None,zoneList=None, rnameList=None)

def drawpiechart (ax, title, yesno, statBox):
	# generic piechart
	# ax is an axes
	# title is the text to see at the top
	# yesno is a tuple from the result of roacoverage
	# statsBox is a boolean : display stats or not?

	# create a string that shows the data date ('made on...')
	piedate = datetime.datetime.strptime(datadate,'%Y-%m-%d').strftime('%d %b %Y')

	# these pie charts will have two values "yes" and "no"

	total=yesno[0]+yesno[1]
	if total == 0:
		plt.txt (0.,0.,'Nothing to Chart',va='center')
		return
	yespct=100.*yesno[0]/total
	if yespct > 0.0:
		labels=[f'{yespct:.4}%-ROA']
	else:
		labels=['']
	nopct=100.*yesno[1]/total
	if nopct > 0.0:
		labels.append(f'{nopct:.4}%-NoROA')
	else:
		labels.append('')

	# set up the pie slices (only two, ever)
	sizes = f'{yesno[0]} {yesno[1]}'.split()
	colors = ['green', 'red']
	ax.set_xlim (-1.5,1.5)
	ax.set_ylim (-1.5,1.5)
	ax.set_title (title)
	ax.pie(sizes,labels=labels, colors=colors, startangle=90, labeldistance=0.4, textprops={'color':'white','fontweight':'bold'})
	ax.legend (loc='lower center')
	ax.text (0.,1.05,f'{piedate}',fontsize='9',ha='center')
	if statBox:
		plt.text (1.25,.5,f'Zones: {yesno[2]}')
		plt.text (1.25,.25,f'TLDs: {yesno[3]}')
		plt.text (1.25,.0,f'Nameservers: {yesno[4]}')
		plt.text (1.25,-.25,f'Addresses: {yesno[5]}')
		plt.text (1.25,-.5,f'RouteOrigins: {yesno[0]+yesno[1]}')
	#end if statBox
#def drawpiechart (ax, title, yesno, statBox)

def drawhistogramchart(ax, title, yesno):
	# draws the base histogramchart


	ax.set_xlabel("Percentage of Zone's Route Origins with ROA")
	ax.set_ylabel('Fraction of Population')
	ax.set_title(title)
	# Zone is -2; TLD is -1
	bins=[x for x in range(0,101)]
	n,bins,patches=ax.hist(yesno[-2],bins=bins, density=True, histtype='step', cumulative=True,linewidth=7,color='blue', label='All Zones')
	patches[0].set_xy(patches[0].get_xy()[:-1])

	n,bins,patches=ax.hist(yesno[-1],bins=bins, density=True, histtype='step', cumulative=True,linewidth=3,color='red', label='TLD Zones')
	patches[0].set_xy(patches[0].get_xy()[:-1])

	#changes legend from box to line : instead of show legend as hollow rectangles


	handles, labels = ax.get_legend_handles_labels()
	new_handles = [Line2D([], [], c=h.get_edgecolor()) for h in handles]
	ax.legend(handles=new_handles, labels=labels, loc='upper left')

	# add a grid to the plot
	ax.grid(b=True, color='silver', linestyle='--', linewidth=1,axis='y')
	bottom,top=ax.get_ylim()
	ax.set_ylim(bottom-.1,top)
	left,right=ax.get_xlim()

	# the 'made on' date
	piedate = datetime.datetime.strptime(datadate,'%Y-%m-%d').strftime('%d %b %Y')
	# add the made on date line
	ax.text (left+3,bottom-.075,f'on {piedate}',fontsize='9')
#end def drawhistogramchart(ax, title, yesno):

def chartall (plotfile):
	# generates charts and histograms for the 'all' categories

	fig,ax = plt.subplots (1,1, constrained_layout=True)
	yesno=roacoverage(zoneCategoryList='ccTLD gTLD revMap sub-ccTLD sub-gTLD'.split())
	drawpiechart (ax,'DNS Core', yesno, True)
	plt.savefig (plotfile)
	plt.clf()

	fig,ax = plt.subplots (1,1, constrained_layout=True)
	plt.style.use('ggplot') # still not doing it
	drawhistogramchart (ax,'DNS Core',yesno)
	plt.savefig (plotfile.replace ('.png','-histogram.png'))
	plt.clf()
#def chartall (plotfile):

def chartv4v6 (plotfile):
	# draw the charts for IPv4 and IPv6
	# originally this was supposed to be a side-by-side dual pie, but I gave up trying to size it
	# sigh, it's complicated...
	for addressfamilylist,charttitle in [([ipaddress.IPv4Network],'IPv4'),([ipaddress.IPv6Network],'IPv6')]:
		fig,ax = plt.subplots (1,1, constrained_layout=True)
		yesno=roacoverage(addressFamilyList=addressfamilylist)
		drawpiechart (ax,charttitle, yesno, False)
		plt.savefig (plotfile.replace('.png',f'-{charttitle}.png'))
		plt.clf()
	#end for addressfamilylist,charttitle in [([ipaddress.IPv4Network],'IPv4'),([ipaddress.IPv6Network],'IPv6')]:
#def chartv4v6 (plotfile):

def chartcats (plotfile):
	# draw pie charts for the three categories (cc/g/revmap)
	for zonecategorylist,charttitle in [('ccTLD sub-ccTLD'.split(),'ccTLD'),('gTLD sub-gTLD'.split(),'gTLD'),('revMap'.split(),'reverse map')]:
		fig,ax = plt.subplots (1,1, constrained_layout=True)
		yesno=roacoverage(zoneCategoryList=zonecategorylist)
		drawpiechart (ax,charttitle, yesno, False)
		plt.savefig (plotfile.replace('.png',f'-{charttitle}.png'))
		plt.clf()
	#end for zonecategorylist,charttitle in [('ccTLD sub-ccTLD'.split(),'ccTLD')...
#def chartcats (plotfile):

def chartRIRs (plotfile):
	# generate the pie charts for each RIR
	for rnamelist,charttitle in [ (['dns-admin.afrinic.net.'],'AFRINIC'), (['read-txt-record-of-zone-first-dns-admin.apnic.net.'],'APNIC'), (['dns.ripe.net.'],'RIPE'), (['hostmaster.lacnic.net.'],'LACNIC'), (['dns-ops.arin.net.'],'ARIN')]:
		fig,ax = plt.subplots (1,1, constrained_layout=True)
		yesno=roacoverage(rnameList=rnamelist)
		drawpiechart (ax,charttitle, yesno, False)
		plt.savefig (plotfile.replace('.png',f'-{charttitle}.png'))
		plt.clf()
	#end for rnamelist,charttitle in [ (['dns-admin.afrinic.net.'],'AFRINIC')...
#end def chartRIRs (plotfile):

def house_title (house,short=False):
	# "pretty prints" a name for a house
	if short:
		upperitems=0
		loweritems=0
		for item in house.title:
			if item == item.lower():
				loweritems+=1
			else:
				upperitems+=1
		if loweritems <= 2:
			titlelist=list()
			for item in house.title:
				if item == item.lower():
					titlelist.append(item)
			return '/'.join (titlelist)
		else:
			for item in house.title:
				if item == item.upper():
					return item # not going to 'edit' it anymore
			#end for item in house.title:
			if item.find(')')==-1:
				return item
			return '...'+item[item.find('('):item.find(')')+1]+'...'

	else:
		return '/'.join(sorted(house.title))
#end def house_title

def make_dnsop_table (zones):
	# builds tables for DNS (House) Operators (pipe-delim, json, suitable for charting)
	housereports=list()
	housedetailedreports=list()
	housedicts=dict()

	for house in dnshouses:
		# the house structure is divided into the categories of zones (g/cc/revMap/etc)
		zonesinhouse=set()
		tldsinhouse=set()
		for cat in house.zonesbycat.keys():
			for z in house.zonesbycat[cat]:
				zonesinhouse.add (z)
			if cat in 'ccTLD gTLD revMap'.split():
				for z in house.zonesbycat[cat]:
					tldsinhouse.add (z)
		#end for cat in house.zonesbycat.keys():
		# tldsinhouse and zonesinhouse are sets of all the elements regardless of category

		# get the tuple for the currenthouse
		yesno=roacoverage (zoneList=zonesinhouse)

		housedict=dict()

		# put the tuple into this structure (an artefact of how the code evolved)
		housedict['yes']=yesno[0]
		housedict['no']=yesno[1]
		housedict['zonecount']=len(zonesinhouse)
		housedict['tldcount']=len(tldsinhouse)
		housedict['NScount']=yesno[4]
		housedict['ADDRcount']=yesno[5]
		housedict['total']=housedict['yes']+housedict['no']
		if housedict['total']==0:
			housedict['pct']='NaN'
		else:
			housedict['pct']=100.*housedict['yes']/housedict['total']
		try:
			housedict['ccTLDcount']=len(house.zonesbycat['ccTLD'])
		except:
			housedict['ccTLDcount']=0
		try:
			housedict['gTLDcount']=len(house.zonesbycat['gTLD']) # 'c'
		except:
			housedict['gTLDcount']=0
		try:
			housedict['revMapcount']=len(house.zonesbycat['revMap']) # 'd'
		except:
			housedict['revMapcount']=0

		# assemble the data structure that is passed to the plotting routines
		housedicts[house_title(house)]=housedict

		# generate two Pipe-delimited tables, for older code and presentations
		# housereports is what appeared in old slides
		# housedetailedreports is what I would put into JSON files when distributing the who table

		if housedict['pct']!='NaN':
			housedetailedreports.append(f"{housedict['tldcount']:6}|{housedict['ccTLDcount']:6}|{housedict['gTLDcount']:6}|{housedict['revMapcount']:6}|{housedict['zonecount']:6}|{housedict['NScount']:6}|{housedict['ADDRcount']:6}|{housedict['total']:6}|{housedict['yes']:6}|{housedict['pct']:5.1f}%|{house_title(house,short=True)}")
			housereports.append(f"{housedict['tldcount']:6}|{housedict['ccTLDcount']:6}|{housedict['gTLDcount']:6}|{housedict['revMapcount']:6}|{housedict['pct']:5.1f}%|{house_title(house,short=True)}")
		else:
			if os.isatty (sys.stdin.fileno()):
				print (f'no routes for {house_title(house,short=True)}')

	tabledetailedlines=f'{"TLDs":6}|{"ccTLDs":6}|{"gTLDs":6}|{"revMap":6}|{"NSRR":6}|{"AddrRR":6}|{"RteOri":6}|{"ROAs":6}|{"Cover":6}|{"House":6}'
	tabledetailedlines+='\n'
	for nextline in sorted(housedetailedreports,reverse=True):
		tabledetailedlines+=nextline
		tabledetailedlines+='\n'

	tablelines=f'{"TLDs":6}|{"ccTLDs":6}|{"gTLDs":6}|{"revMap":6}|{"Cover":6}|{"House":6}'
	tablelines+='\n'
	for nextline in sorted(housereports,reverse=True):
		tablelines+=nextline
		tablelines+='\n'

	return tablelines,tabledetailedlines,housedicts
#end make_dnsop_table

def chartHouses (plotfileprefix):
	# creates the scatter plots for DNS houses and writes the tabular files (done here because I am lazy)
	table,detailedtable,housedicts=make_dnsop_table (zones)
	with open (f'{plotfileprefix}-roas.txt','w') as fout:
		fout.write(table)
	with open (f'{plotfileprefix}-Detailed-roas.txt','w') as fout:
		fout.write(detailedtable)
	with open (f'{plotfileprefix}-Detailed-roas.json','w') as fout:
		fout.write(json.dumps(housedicts,sort_keys=True,indent=4))

	fig,ax = plt.subplots (1,1, figsize=(16,9), constrained_layout=True)
	drawDNSHousescatterplot(ax,housedicts)
	plt.savefig (f'{plotfileprefix}-scatterplot.png')
	plt.clf()
#end def chartHouses (plotfileprefix):

def drawDNSHousescatterplot (ax, housedicts):
	# charts a scatterplot for the house-related data
	xlabel="Percentage of DNS House's Route Origins with ROA"
	ylabel='Number of TLDs & RevMap in House'
	title='DNS Houses and ROA Coverage'
	x=list()
	y=list()
	for h in housedicts.keys():
		if housedicts[h]['pct'] != 'NaN':
			x.append (int(housedicts[h]['pct']))
			y.append (int(housedicts[h]['tldcount']))
	drawscatterplot (ax, title, xlabel, ylabel, x, y)
#end def drawDNSHousescatterplot (ax, housedicts):

def drawscatterplot (ax, title, xlabel, ylabel, x, y, s=None, c=None):
	# generically draws a scatterplot

	# set fontsizes for PPT
	ax.set_xlabel(xlabel,fontsize=24)
	ax.set_ylabel(ylabel,fontsize=24)
	ax.set_title(title,fontsize=24)

	# X goes from 0-100%, leave a margin
	ax.set_xlim(-10,110)
	ax.set_xticks([10*x for x in range (0,11)])
	ax.set_xticklabels([str(x)+'%' for x in range (0,110,10)],fontdict={'fontsize':'24'})

	ax.tick_params(axis="y", labelsize=24)

	# x is pct, y is whatever, s (size) might mean the significane and c (color) the category within the chart
	# them is all lists
	ax.scatter(x,y,s,c)

	# make enough room for the 'made on' date
	bottom,top=ax.get_ylim()
	left,right=ax.get_xlim()
	piedate = datetime.datetime.strptime(datadate,'%Y-%m-%d').strftime('%d %b %Y')
	ax.text (left,bottom,f'on {piedate}',fontsize=12)
#end def drawscatterplot ()

def chooseannotations (operator):
	# a very subjective labelling for the PPT at APNIC 50
	# this will not stand the test of time, probably

	if 'ULTRADNS' in operator:
		return 'green',''
	elif 'VRSN' in operator or 'VRGS' in operator:
		return 'green',''
	elif 'AFILIAS' in operator:
		return 'green',''
	elif 'WOODY' in operator:
		return 'orange',''
	elif operator.startswith('RIPE'):
		return 'red','RIPE'
	elif operator.startswith('APNIC'):
		return 'red','APNIC'
	elif operator.startswith('LACNIC'):
		return 'red','LACNIC'
	elif operator.startswith('AFRINIC'):
		return 'red','AFRINIC'
	elif operator.startswith('ARIN'):
		return 'red','ARIN'
	else:
		return 'black',''
#end def chooseannotations (operator):

def setupASNscatterplots(autnumdicts):
	# draws the ASN-related scatterplots
	xlabel="Percentage of AS Number's Route Origins with ROA"
	ylabel='AS Number'
	title='AS Numbers and ROA Coverage'
	x=list() # pct coverge for AS
	y=list() # the aut num itself
	s=list() # number of TLDs
	c=list() # will be colors
	a=list() # annotation (names)
	for asn in autnumdicts.keys():
		if autnumdicts[asn]['pct'] != 'NaN':
			x.append (int(autnumdicts[asn]['pct']))
			y.append (int(asn))
			s.append (int(autnumdicts[asn]['tldcount']))
			chosencolor,chosenlabel=chooseannotations(autnumdicts[asn]['autnumoperator'])
			c.append (chosencolor)
			a.append (chosenlabel)
		#end if autnumdicts[asn]['pct'] != 'NaN':
	#end for asn in autnumdicts.keys():
	return title, xlabel, ylabel, x, y, s, c, a
#end def drawASNplainscatterplot(ax,autnumdicts):

def drawASNplainscatterplot (ax, title, xlabel, ylabel, x, y, s, c, a):
	# draw the plain plot, the one that would most likely be on a data presentation platform
	drawscatterplot (ax, title, xlabel, ylabel, x, y, s)
#end def drawASNplainscatterplot

def drawASNannotatedscatterplot (ax, title, xlabel, ylabel, x, y, s, c, a):
	# this adds the annotations used in the presentation (APNIC 50)
	drawscatterplot (ax, title, xlabel, ylabel, x, y, s, c)
	ax.add_patch(Rectangle((0,0), 100, 65535, alpha=0.5, facecolor="skyblue"))
	ax.text (10.,65600.,'16bit AS numbers in blue box',fontsize=18)
	annotate_count=0
	for x1,y1,text in sorted(zip (x,y,a),key=lambda k: k[1]):
		if text is not '':
			ax.text (x1+10,annotate_count*25000,text,fontsize=18)
			ax.plot ((x1,x1+10),(y1,annotate_count*25000+5000),linewidth=1,color='black')
			annotate_count+=1
		#end if text is not '':
	#end for x1,y1,text in sorted(zip (x,y,a),key=lambda k: k[1]):
#end def drawASNannotatedscatterplot

def chartASNs (plotfileprefix):
	# draw the plots as used in APNIC 50
	# and write the tables to files as well
	table,autnumdicts=make_asop_table (addresses)
	with open (f'{plotfileprefix}-roas.txt','w') as fout:
		fout.write(table)
	with open (f'{plotfileprefix}-roas.json','w') as fout:
		fout.write(json.dumps(autnumdicts,sort_keys=True,indent=4))
	# x and y - coordinates
	# s - size
	# c - color
	# a - annotation
	title, xlabel, ylabel, x, y, s, c, a = setupASNscatterplots(autnumdicts)
	fig,ax = plt.subplots (1,1, figsize=(16,9), constrained_layout=True)
	drawASNplainscatterplot(ax, title, xlabel, ylabel, x, y, s, c, a)
	plt.savefig (f'{plotfileprefix}-scatterplot-plain.png')
	plt.clf()
	fig,ax = plt.subplots (1,1, figsize=(16,9), constrained_layout=True)
	drawASNannotatedscatterplot(ax, title, xlabel, ylabel, x, y, s, c, a)
	plt.savefig (f'{plotfileprefix}-scatterplot-annotated.png')
	plt.clf()
#end def chartASNs (plotfileprefix):

class asInfo:
	# a way to aggregate stats per AS number and not as it is gathered in the census
	def __init__ (self, autnumber):
		self.autnum=autnumber
		self.autnumoperator='Unset'
		self.prefixset=dict()
		self.prefixset[True]=set() # prefixes/as with ROA
		self.prefixset[False]=set() # prefixes/as with no ROA
		self.addresses=set()
		self.nameservers=set()
		self.zones=dict() # dicts by category of zones
	#end def __init__
#end class asInfo

def buildautnumdict(addresses):
	# builds counts for AS
	# autnums will be the list (dict) of asInfo, for each AS number
	autnums=dict()

	for addr in addresses.keys():
		addrobj=addresses[addr]
		for ro in addrobj["Route-Originations"]:
			# ro is route origin

			if ro["Route-Origin-AutNum"] is None:
				# no guarantee that Team Cymru has the data
				continue

			if ro["Route-Origin-AutNum"] not in autnums.keys():
				autnums[ro["Route-Origin-AutNum"]]=asInfo(ro["Route-Origin-AutNum"])
			asobj=autnums[ro["Route-Origin-AutNum"]]

			# this might be repetitive, probably ought to be under the if above
			asobj.autnumoperator=ro["Route-Origin-AutNumName"]

			# there may be multiple addresses and route origins landing at this AS though
			asobj.prefixset[ro["Route-Origin-HasROA"]].add(ro["Route-Origin-Prefix"])
			asobj.addresses.add(addr)

			for ns in addrobj["Used-in-authoritative-set"]:
				nsobj=nameservers[ns]

				# this is how we count the nameservers in an ASN
				asobj.nameservers.add(ns)

				for zone in nsobj["usedbyzonesinauthority"]:
					# counting the zones supported by the ASN
					zoneobj=zones[zone]

					#count by zone category (ccTLD/gTLD/...)
					if zoneobj['category'] not in asobj.zones.keys():
						asobj.zones[zoneobj['category']]=set()

					asobj.zones[zoneobj['category']].add(zone)
				#end for zone in nsobj["usedbyzonesinauthority"]:
			#end for ns in addrobj["Used-in-authoritative-set"]:
		#end for ro in addrobj["Route-Originations"]:
	#end for addr in addresses.keys():
	return autnums
#end def buildautnumdict(addresses):

def make_asop_table (addresses):
	# makes the AS operator table (pipe delim, json, and suitable for charting)

	# first get all the data in the form needed
	autnums=buildautnumdict(addresses)

	# the table and the structure needed for plotting
	asreports=list()
	autnumdicts=dict()

	for autnum in autnums.keys():
		#for each ASN
		autnumobj=autnums[autnum]

		autnumdict=dict()
		autnumdict['HasROA']=len(autnumobj.prefixset[True])
		autnumdict['HasNoROA']=len(autnumobj.prefixset[False])
		autnumdict['Total']=autnumdict['HasROA']+autnumdict['HasNoROA']

		if autnumdict['Total'] == 0:
			autnumdict['pct']='NaN'
		else:
			autnumdict['pct']=100.*autnumdict['HasROA']/autnumdict['Total']

		autnumdict['zonecount']=0
		autnumdict['tldcount']=0

		for category in autnumobj.zones.keys():
			autnumdict['zonecount']+=len(autnumobj.zones[category])
			if category in 'ccTLD gTLD revMap'.split():
				autnumdict['tldcount']+=len(autnumobj.zones[category])
		autnumdict['addresscount']=len(autnumobj.addresses)
		autnumdict['autnumoperator']=autnumobj.autnumoperator

		autnumdicts[autnumobj.autnum]=autnumdict

		# this is the crude way of building the table
		# the first field is the TLD count, they way I'd sorted in old slides
		# that field will be cut off when I make the table below, after the "sorted()" step
		asreports.append(f"{autnumdict['tldcount']:7}|{autnumobj.autnum:7}|{autnumdict['tldcount']:7}|{autnumdict['Total']:7}|{autnumdict['addresscount']:7}|{autnumdict['pct']:6.1f}%|{autnumdict['autnumoperator']}")
	#end for autnum in autnumdict.keys():

	tablelines=f'{"AutNum":7}|{"TLDs":7}|{"Prefix":7}|{"Addr":7}|{"Cover":7}|{"Operator"}'
	tablelines+='\n'
	for nextline in sorted(asreports,reverse=True):
		tablelines+=nextline[8:] # lops off the tld zone count used for sorting
		tablelines+='\n'
	return tablelines,autnumdicts
#end def make_asop_table

if __name__ == '__main__':
	# this runs the whole
	executablefile,workingdirectory=executablefileanddirectory()
	# runtime is no longer used (it was for logging, when I did that) but may come back
	runtime=datetime.datetime.utcnow().strftime('%Y-%m-%d-%H%M%S')

	try:
		#the reason this is in a try is that I used to handle exceptions,
		# now I don't.  But if I daemonize this, I may add back logging and
		# special exception handling

		zones,nameservers,addresses,datadate=read_maps()
		dnshouses=zonestohouses.buildhouses (zones)

		# create a place to put results without clobbering

		resultsdirectory=f'{workingdirectory}results/{datadate}/'

		# for a firstrun, need to make the results dir
		if not os.path.isdir (f'{workingdirectory}results/'):
			os.mkdir (f'{workingdirectory}results/')

		# for the data date, make sure there's a place for everything
		if not os.path.isdir (resultsdirectory):
			os.mkdir (resultsdirectory)

		chartall (f'{resultsdirectory}PIEall.png')
		chartv4v6 (f'{resultsdirectory}PIEv4v6.png')
		chartcats (f'{resultsdirectory}PIEcats.png')
		chartRIRs (f'{resultsdirectory}PIErirs.png')
		chartHouses (f'{resultsdirectory}DNShouse')
		chartASNs (f'{resultsdirectory}ASN')

	except:
		#fancy way to say, if you run at the command line
		if os.isatty (sys.stdin.fileno()):
			raise
	finally:
		pass
	#end finally
#end if __name__ == '__main__':
