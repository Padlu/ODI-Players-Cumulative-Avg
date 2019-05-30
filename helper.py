import requests
from bs4 import BeautifulSoup
from random import choice
import csv
from user_agent import generate_user_agent			# LIBRARY TO GENERATE FAKE USER AGENT #

def generate_proxies():		# GENERATES POOL OF 45-100 PROXIES (ENOUGH TO ((NOT)) FLOOD THE SERVER WITH REQUESTS) #
	url = "https://www.sslproxies.org/"		# BEST FREE PROXIES #
	response = requests.get(url)
	proxy_soup = BeautifulSoup(response.content, 'html5lib')
	return list(map(lambda x:x[0]+":"+x[1], list(zip(map(lambda x:x.text, proxy_soup.findAll('td')[::8]), map(lambda x:x.text, proxy_soup.findAll('td')[1::8])))))[:-4]

def proxy_request(i, proxies, request_type, url, **kwargs):
	while 1:	# LOOP ENSURES THAT EACH URL IS REQUESTED WITH RANDOM PROXY AND USER AGENT FOR EVERY ITERATION UNTIL WE SUCCESSFULLY GET THE REQUEST WITH REASONABLE TIMEOUT OF 5 SECS (SO NO NEED TO PURPOSEFULLY MAKE SCRAPPING SLOW USING SLEEP()) #
		try:
			proxy = choice(proxies)		# GET NEW PROXY FROM THE POOL
			headers = {'User-Agent': generate_user_agent(device_type="desktop", os=('mac', 'linux'))}		# GENERATE NEW AGENT #
			if i == 0:		# REQUEST FOR GETTING ALL ODI PLAYERS #
				print("For url page "+url[-40:-39]+" trying proxy : ", proxy)
			elif i == 1:		# REQUEST FOR GETTING EACH ODI PLAYER'S USER DATA(RUNS | DATE_OF_MATCH) #
				print("For "+url[40:-55]+" trying proxy : ", proxy)
			response = requests.request(request_type, url, headers=headers, proxies={'http' : proxy, 'https': proxy}, timeout=5, **kwargs)
			if response is not None and response.status_code == 200:
				return response
		except:
			pass
			
def get_proxies_urls(i):
	urls = list()
	if i == 0:		# URLS FOR GETTING ALL ODI PLAYERS PAGES #
		for k in range(1,14):
			urls.append("http://stats.espncricinfo.com/ci/engine/stats/index.html?class=2;filter=advanced;orderby=player;page="+str(k)+";size=200;template=results;type=batting")
	elif i == 1:		# URLS FOR GETTING EACH ODI PLAYER'S USER DATA PAGES #
		with open("players_odi.csv", 'r') as f:
			reader = csv.reader(f)
			next(reader)
			urls.clear()
			for row in reader:
				urls.append(row[2])
	return generate_proxies(), urls