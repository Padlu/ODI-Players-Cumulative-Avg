import requests
from bs4 import BeautifulSoup
from random import choice
import csv
from user_agent import generate_user_agent			# LIBRARY TO GENERATE FAKE USER AGENT #
import time
import os
import pickle

def generate_proxies():		# GENERATES POOL OF 45-100 PROXIES (ENOUGH TO ((NOT)) FLOOD THE SERVER WITH REQUESTS) #
	url = "https://www.sslproxies.org/"		# BEST FREE PROXIES #
	response = requests.get(url)
	proxy_soup = BeautifulSoup(response.content, 'html5lib')
	return list(map(lambda x:x[0]+":"+x[1], list(zip(map(lambda x:x.text, proxy_soup.findAll('td')[::8]), map(lambda x:x.text, proxy_soup.findAll('td')[1::8])))))[:-4]

def proxy_request(i, proxies, request_type, url, **kwargs):
	while 1:	# LOOP ENSURES THAT EACH URL IS REQUESTED WITH RANDOM PROXY AND USER AGENT FOR EVERY ITERATION UNTIL SUCCESSFULLY GET THE REQUEST. REASONABLE TIMEOUT OF 5 SECS USED FOR EVERY PROXY (SO NO NEED TO PURPOSEFULLY MAKE SCRAPPING SLOW USING SLEEP()) #
		try:
			proxy = choice(proxies)		# GET RANDOM NEW PROXY FROM THE POOL
			headers = {'User-Agent': generate_user_agent(device_type="desktop", os=('mac', 'linux'))}		# GENERATE RANDOM NEW AGENT #
			response = requests.request(request_type, url, headers=headers, proxies={'http' : proxy, 'https': proxy}, timeout=5, **kwargs)
			if response is not None and response.status_code == 200:		# RESPONSE SUCCESSFUL #
				if i == 0:		# SUCCESSFULE REQUEST FOR GETTING ALL ODI PLAYERS FOR A PAGE #
					print("Response for page "+url[-40:-39]+" Successful: ", response,"\t=>\n")
				elif i == 1:		# SUCCESSFUL REQUEST FOR GETTING CAREER RUNS STATS OF AN ODI PLAYER #
					print("Response for "+url[40:-84]+" Successful: ", response)
				return response
		except:		# EXCEPT ALL KIND OF ERRORS AND JUST PASS FOR NEXT PROXY AND USER AGENT #
			pass
			
def get_urls():
	urls = list()
	# URLS FOR GETTING ALL ODI PLAYERS PAGES | EACH PAGE 200 PLAYERS | TOTAL 13 PAGES#
	for k in range(1,14):
		urls.append("http://stats.espncricinfo.com/ci/engine/stats/index.html?class=2;filter=advanced;page="+str(k)+";size=200;template=results;type=batting")
	return urls

def get_empty_odi_runs_dict():		# CREATES A DICTIONARY OF KEYS AS YEARS AND VALUES (0) AS RUNS FOR A PLAYER #
	runs_over_odi_course = dict()
	for i in range(1971,2020):
		runs_over_odi_course[str(i)] = 0
	return runs_over_odi_course

def get_cumulative_yearwise_score(response):		# GET THE YEARLY CUMULATIVE RUNS SCORE FOR A PLAYER #
	STAT_soup = BeautifulSoup(response.content, 'lxml')
	captions = STAT_soup.findAll("caption")
	if len(captions) == 0:		## HANDLE IF WE DON'T GET THE CAPTIONS LIST FROM SOUP ## IT WAS GIVING NULL LIST SOMETIMES AND I HAD LESS TIME IN MY HAND SO HAD TO DO SMALL ADJUSTMENTS TO CODE TO GET THE WORK DONE ##
		return None
	caption = captions[0]
	for cap in captions:
		if cap.get_text() == 'Series averages':
			caption = cap
			break
	table = caption.find_parent('table', {'class': 'engineTable'})		# SINCE CLASS WITH SAME NAMES CAN BE MULTIPLE WE KNOW THERE IS ONLY ONE TABLE(WHICH WE WANT) WITH CAPTION == 'SERIES AVERAGES' #
	rows = table.findAll('tr', {'class':'data1'})
	prev_row_year = '0000'
	sum_runs = 0
	cumulative_odi_runs = get_empty_odi_runs_dict()
	for row in rows:
		cells = row.findAll('td')
		if cells[4].text == '-':
			runs = 0
		else:
			runs = int(cells[4].text) # RUNS COLUMN #
		curr_row_year = str(cells[-4].contents[0])[-8:-4] # DATE COLUMN #
		if prev_row_year == '0000':		# #1 ITERATION #
			prev_row_year = curr_row_year
			sum_runs = runs
		elif prev_row_year == curr_row_year:		# CUMULATE THE RUNS FOR SIMILAR YEAR #
			sum_runs += runs
		else:						# SAVE THE CUMULATED RUNS AND DO SAME FOR NEXT YEAR #
			for i in range(int(prev_row_year), int(curr_row_year)):
				cumulative_odi_runs[str(i)] = sum_runs
			prev_row_year = curr_row_year
			sum_runs += runs
	for i in range(int(prev_row_year), 2020):		# SET THE FINAL VALUE TO ALL THE YEARS AFTER ODI RETIREMENT OF A PLAYER #
		cumulative_odi_runs[str(i)] = sum_runs
	return cumulative_odi_runs		

def get_list_of_players_data(response):		# GET THE LIST OF PLAYERS FROM THE PAGE WITH THEIR NAME, COUNTRY AND LINK TO STATS #
	players = list()
	ODI_soup = BeautifulSoup(response.content, 'lxml')
	captions = ODI_soup.findAll("caption")
	if len(captions) == 0:		## HANDLE IF WE DON'T GET THE CAPTIONS LIST FROM SOUP ## IT WAS GIVING NULL LIST SOMETIMES AND I HAD LESS TIME IN MY HAND SO HAD TO DO SMALL ADJUSTMENTS TO CODE TO GET THE WORK DONE ##
		return None
	caption = captions[0]
	for cap in captions:
		if cap.get_text() == 'Overall figures':
			caption = cap
			break
	table = caption.find_parent('table', {'class': 'engineTable'})		# SINCE CLASS WITH SAME NAMES CAN BE MULTIPLE WE KNOW THERE IS ONLY ONE TABLE(WHICH WE WANT) WITH CAPTION == 'OVERALL FIGURES' #
	rows = table.findAll('tr',{'class':'data1'})
	for row in rows:
		player = {'name':'', 'country':'', 'career_summary_link':''}		# RESET FOR NEW PLAYER #
		cell = row.findAll('td')[0]
		link = cell.contents[0]
		player['name'] = link.contents[0]
		player['country'] = cell.contents[1]
		player['career_summary_link'] = 'http://stats.espncricinfo.com/ci/engine' + str(link.attrs['href'])[11:] + '?class=2;filter=advanced;orderby=start;template=results;type=batting;view=series'
		players.append(player)
	return players

def main(url_idx, player_idx, total_successful_req, completed, writer):
	global proxies, urls
	start_t = time.time()
	print("Start time:", start_t)
	print("Proxy POOL: (",len(proxies),")\n")
	task = 0.0
	for i in range(url_idx,len(urls)):		# GET ALL UNIQUE PLAYERS LIST OF NAMES AND THEIR INDIVIDUAL PAGES LINK #
		response_players = proxy_request(0, proxies,'get', urls[i])
		players_list = get_list_of_players_data(response_players)
		print("list of players: ",len(players_list))
		while players_list is None:		## HANDLE IF WE DON'T GET THE CAPTIONS LIST FROM SOUP ## IT WAS GIVING NULL LIST SOMETIMES AND I HAD LESS TIME IN MY HAND SO HAD TO DO SMALL ADJUSTMENTS TO CODE TO GET THE WORK DONE ##
			response_players = proxy_request(0, proxies,'get', urls[i])
			players_list = get_list_of_players_data(response_players)
		for j in range(player_idx,len(players_list)):		# GET THE ODI CAREER STATS (CUMULATIVE SUM) FOR ALL PLAYERS IN THE PAGE #
			stat_url = players_list[j]['career_summary_link']
			response_player = proxy_request(1, proxies, 'get', stat_url)
			odi_runs_in_career = list(get_cumulative_yearwise_score(response_player).values())
			while odi_runs_in_career is None:		## HANDLE IF WE DON'T GET THE CAPTIONS LIST FROM SOUP ## IT WAS GIVING NULL LIST SOMETIMES AND I HAD LESS TIME IN MY HAND SO HAD TO DO SMALL ADJUSTMENTS TO CODE TO GET THE WORK DONE ##
				response_player = proxy_request(1, proxies, 'get', stat_url)
				odi_runs_in_career = list(get_cumulative_yearwise_score(response_player).values())
			row = [players_list[j]['name'], players_list[j]['country']]
			row.extend(odi_runs_in_career)
			writer.writerow(row)		# WRITE IN A CSV FILE THE PLAYER NAME, COUNTRY, CUMULATIVE SCORE #
			if total_successful_req % 50 == 0:		# GENERATE NEW POOL OF PROXIES AFTER EVERY 50 ITERATIONS #
				proxies = generate_proxies()
				print("New Proxy POOL: (",len(proxies),")\n")
			pickle.dump([i,j+1,total_successful_req, completed], open('odi_runs_scraping.pickle','wb'))		# STORE THE PROGRESS FOR EACH PLAYER/ITERATION #
			total_successful_req += 1
			task = (((((j+1)/len(players_list))*100)*(((1/len(urls)))*100))/100)
			print("Total successful requests: ", total_successful_req)
			print("Completed : ","{:.2f}".format(completed+task), "%")
			print("Elapsed time: ","{:.2f}".format((time.time() - start_t)/3600),"Hrs\n------------------------------------------------------------------------------\n")
		completed += task
	print("Done!")
	print("Total time: ", "{:.2f}".format((time.time() - start_t)/3600), " Hrs")


		# GET THE POOL OF PROXIES AND REQUIRED URLS TO SCRAPE #
urls = get_urls()		
proxies = generate_proxies()

if os.path.isfile('./players_odi_cumulative_runs.csv'):		# IF FILE PRESENT JUST GET IT #
	f = open("players_odi_cumulative_runs.csv", "a", encoding='utf-8',newline='')
	writer = csv.writer(f)
else:															# IF FILE NOT PRESENT CREATE  IT #
	f = open("players_odi_cumulative_runs.csv", "w", encoding='utf-8',newline='')
	writer = csv.writer(f)
	writer.writerow(['Name Of Player', 'Country', 'Years'])
	years = "1971 1972 1973 1974 1975 1976 1977 1978 1979 1980 1981 1982 1983 1984 1985 1986 1987 1988 1989 1990 1991 1992 1993 1994 1995 1996 1997 1998 1999 2000 2001 2002 2003 2004 2005 2006 2007 2008 2009 2010 2011 2012 2013 2014 2015 2016 2017 2018 2019".split(' ')
	row = [' ', ' ']
	row.extend(years)
	writer.writerow(row)

## I CREATED A PICKLE TO STORE THE PROGRESS AND CONTINUE FROM WHERE LEFT SO THAT IF LAPTOP SHUTS DOWN OR IDE CRASHES WE COULD RESUME OUR SCRAPPING FROM WHERE LEFT OFF ##

if os.path.isfile('./odi_runs_scraping.pickle'):		# CHECK IF THE PICKLE EXISTS(PREVIOUSLY THE CODE HAS RAN) #
	pickle_in = open('odi_runs_scraping.pickle', 'rb')
	url_idx, player_idx, total_successful_req, completed = pickle.load(pickle_in)		# GET THE REQUIRED DATA #
	main(url_idx, player_idx, total_successful_req, completed, writer)			# RESUME THE WORK #
else:		# CODE IS RUNNING FOR THE FIRST TIME #
	main(0, 0, 0, 0.0, writer)
	
#OUTPUT:		IT TOOK TOTAL OF 5HRS 15MINS TO GET THE DATA PLUS CUMULATE IT AT THE SAME TIME. MY PREVIOUS CODE DID IT IN 3HRS 20 ISH MINS 
#Start time: 1559286987.529514
#Proxy POOL: ( 100 )
#
#Response for page 1 Successful:  <Response [200]> 	=>
#

#list of players:  200
#Response for player/35320. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  1
#Completed :  0.04 %
#Elapsed time:  32.40 s
#------------------------------------------------------------------------------
#
#Response for player/50710. Successful:  <Response [200]>
#
#Total successful requests:  2
#Completed :  0.08 %
#Elapsed time:  43.19 s
#------------------------------------------------------------------------------
#
#Response for player/7133. Successful:  <Response [200]>
#
#Total successful requests:  3
#Completed :  0.12 %
#Elapsed time:  45.44 s
#------------------------------------------------------------------------------
#
#Response for player/49209. Successful:  <Response [200]>
#
#Total successful requests:  4
#Completed :  0.15 %
#Elapsed time:  70.09 s
#------------------------------------------------------------------------------
#
#Response for player/49289. Successful:  <Response [200]>
#
#Total successful requests:  5
#Completed :  0.19 %
#Elapsed time:  76.29 s
#------------------------------------------------------------------------------
#
#Response for player/40570. Successful:  <Response [200]>
#
#Total successful requests:  6
#Completed :  0.23 %
#Elapsed time:  80.37 s
#------------------------------------------------------------------------------
#
#Response for player/45789. Successful:  <Response [200]>
#
#Total successful requests:  7
#Completed :  0.27 %
#Elapsed time:  91.60 s
#------------------------------------------------------------------------------
#
#Response for player/28779. Successful:  <Response [200]>
#
#Total successful requests:  8
#Completed :  0.31 %
#Elapsed time:  93.46 s
#------------------------------------------------------------------------------
#
#Response for player/28114. Successful:  <Response [200]>
#
#Total successful requests:  9
#Completed :  0.35 %
#Elapsed time:  96.13 s
#------------------------------------------------------------------------------
#
#Response for player/253802. Successful:  <Response [200]>
#
#Total successful requests:  10
#Completed :  0.38 %
#Elapsed time:  98.22 s
#------------------------------------------------------------------------------
#
#Response for player/28081. Successful:  <Response [200]>
#
#Total successful requests:  11
#Completed :  0.42 %
#Elapsed time:  104.21 s
#------------------------------------------------------------------------------
#
#Response for player/52337. Successful:  <Response [200]>
#
#Total successful requests:  12
#Completed :  0.46 %
#Elapsed time:  116.97 s
#------------------------------------------------------------------------------
#
#Response for player/48472. Successful:  <Response [200]>
#
#Total successful requests:  13
#Completed :  0.50 %
#Elapsed time:  119.74 s
#------------------------------------------------------------------------------
#
#Response for player/51880. Successful:  <Response [200]>
#
#Total successful requests:  14
#Completed :  0.54 %
#Elapsed time:  122.67 s
#------------------------------------------------------------------------------
#
#Response for player/43650. Successful:  <Response [200]>
#
#Total successful requests:  15
#Completed :  0.58 %
#Elapsed time:  136.50 s
#------------------------------------------------------------------------------
#
#Response for player/5390. Successful:  <Response [200]>
#
#Total successful requests:  16
#Completed :  0.62 %
#Elapsed time:  162.99 s
#------------------------------------------------------------------------------
#
#Response for player/44936. Successful:  <Response [200]>
#
#Total successful requests:  17
#Completed :  0.65 %
#Elapsed time:  169.33 s
#------------------------------------------------------------------------------
#
#Response for player/26329. Successful:  <Response [200]>
#
#Total successful requests:  18
#Completed :  0.69 %
#Elapsed time:  172.25 s
#------------------------------------------------------------------------------
#
#Response for player/48462. Successful:  <Response [200]>
#
#Total successful requests:  19
#Completed :  0.73 %
#Elapsed time:  175.19 s
#------------------------------------------------------------------------------
#
#Response for player/42605. Successful:  <Response [200]>
#
#Total successful requests:  20
#Completed :  0.77 %
#Elapsed time:  184.59 s
#------------------------------------------------------------------------------
#
#Response for player/51469. Successful:  <Response [200]>
#
#Total successful requests:  21
#Completed :  0.81 %
#Elapsed time:  186.92 s
#------------------------------------------------------------------------------
#
#Response for player/36084. Successful:  <Response [200]>
#
#Total successful requests:  22
#Completed :  0.85 %
#Elapsed time:  195.50 s
#------------------------------------------------------------------------------
#
#Response for player/52047. Successful:  <Response [200]>
#
#Total successful requests:  23
#Completed :  0.88 %
#Elapsed time:  200.59 s
#------------------------------------------------------------------------------
#
#Response for player/48124. Successful:  <Response [200]>
#
#Total successful requests:  24
#Completed :  0.92 %
#Elapsed time:  225.87 s
#------------------------------------------------------------------------------
#
#Response for player/8189. Successful:  <Response [200]>
#
#Total successful requests:  25
#Completed :  0.96 %
#Elapsed time:  233.10 s
#------------------------------------------------------------------------------
#
#Response for player/35263. Successful:  <Response [200]>
#
#Total successful requests:  26
#Completed :  1.00 %
#Elapsed time:  236.52 s
#------------------------------------------------------------------------------
#
#Response for player/45224. Successful:  <Response [200]>
#
#Total successful requests:  27
#Completed :  1.04 %
#Elapsed time:  247.45 s
#------------------------------------------------------------------------------
#
#Response for player/42639. Successful:  <Response [200]>
#
#Total successful requests:  28
#Completed :  1.08 %
#Elapsed time:  260.23 s
#------------------------------------------------------------------------------
#
#Response for player/37000. Successful:  <Response [200]>
#
#Total successful requests:  29
#Completed :  1.12 %
#Elapsed time:  265.62 s
#------------------------------------------------------------------------------
#
#Response for player/38699. Successful:  <Response [200]>
#
#Total successful requests:  30
#Completed :  1.15 %
#Elapsed time:  278.54 s
#------------------------------------------------------------------------------
#
#Response for player/34102. Successful:  <Response [200]>
#
#Total successful requests:  31
#Completed :  1.19 %
#Elapsed time:  283.99 s
#------------------------------------------------------------------------------
#
#Response for player/4578. Successful:  <Response [200]>
#
#Total successful requests:  32
#Completed :  1.23 %
#Elapsed time:  285.57 s
#------------------------------------------------------------------------------
#
#Response for player/43906. Successful:  <Response [200]>
#
#Total successful requests:  33
#Completed :  1.27 %
#Elapsed time:  290.23 s
#------------------------------------------------------------------------------
#
#Response for player/8192. Successful:  <Response [200]>
#
#Total successful requests:  34
#Completed :  1.31 %
#Elapsed time:  292.91 s
#------------------------------------------------------------------------------
#
#Response for player/42657. Successful:  <Response [200]>
#
#Total successful requests:  35
#Completed :  1.35 %
#Elapsed time:  321.49 s
#------------------------------------------------------------------------------
#
#Response for player/50244. Successful:  <Response [200]>
#
#Total successful requests:  36
#Completed :  1.38 %
#Elapsed time:  329.15 s
#------------------------------------------------------------------------------
#
#Response for player/40879. Successful:  <Response [200]>
#
#Total successful requests:  37
#Completed :  1.42 %
#Elapsed time:  341.48 s
#------------------------------------------------------------------------------
#
#Response for player/43652. Successful:  <Response [200]>
#
#Total successful requests:  38
#Completed :  1.46 %
#Elapsed time:  343.85 s
#------------------------------------------------------------------------------
#
#Response for player/42623. Successful:  <Response [200]>
#
#Total successful requests:  39
#Completed :  1.50 %
#Elapsed time:  345.98 s
#------------------------------------------------------------------------------
#
#Response for player/36185. Successful:  <Response [200]>
#
#Total successful requests:  40
#Completed :  1.54 %
#Elapsed time:  353.76 s
#------------------------------------------------------------------------------
#
#Response for player/24598. Successful:  <Response [200]>
#
#Total successful requests:  41
#Completed :  1.58 %
#Elapsed time:  372.43 s
#------------------------------------------------------------------------------
#
#Response for player/47270. Successful:  <Response [200]>
#
#Total successful requests:  42
#Completed :  1.62 %
#Elapsed time:  375.89 s
#------------------------------------------------------------------------------
#
#Response for player/50747. Successful:  <Response [200]>
#
#Total successful requests:  43
#Completed :  1.65 %
#Elapsed time:  386.40 s
#------------------------------------------------------------------------------
#
#Response for player/4144. Successful:  <Response [200]>
#
#Total successful requests:  44
#Completed :  1.69 %
#Elapsed time:  390.92 s
#------------------------------------------------------------------------------
#
#Response for player/45813. Successful:  <Response [200]>
#
#Total successful requests:  45
#Completed :  1.73 %
#Elapsed time:  399.31 s
#------------------------------------------------------------------------------
#
#Response for player/55427. Successful:  <Response [200]>
#
#Total successful requests:  46
#Completed :  1.77 %
#Elapsed time:  402.81 s
#------------------------------------------------------------------------------
#
#Response for player/52812. Successful:  <Response [200]>
#
#Total successful requests:  47
#Completed :  1.81 %
#Elapsed time:  412.11 s
#------------------------------------------------------------------------------
#
#Response for player/56194. Successful:  <Response [200]>
#
#Total successful requests:  48
#Completed :  1.85 %
#Elapsed time:  417.02 s
#------------------------------------------------------------------------------
#
#Response for player/55429. Successful:  <Response [200]>
#
#Total successful requests:  49
#Completed :  1.88 %
#Elapsed time:  429.27 s
#------------------------------------------------------------------------------
#
#Response for player/40551. Successful:  <Response [200]>
#
#Total successful requests:  50
#Completed :  1.92 %
#Elapsed time:  431.94 s
#------------------------------------------------------------------------------
#
#Response for player/4174. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  51
#Completed :  1.96 %
#Elapsed time:  439.36 s
#------------------------------------------------------------------------------
#
#Response for player/226492. Successful:  <Response [200]>
#
#Total successful requests:  52
#Completed :  2.00 %
#Elapsed time:  443.92 s
#------------------------------------------------------------------------------
#
#Response for player/41434. Successful:  <Response [200]>
#
#Total successful requests:  53
#Completed :  2.04 %
#Elapsed time:  454.04 s
#------------------------------------------------------------------------------
#
#Response for player/52810. Successful:  <Response [200]>
#
#Total successful requests:  54
#Completed :  2.08 %
#Elapsed time:  468.04 s
#------------------------------------------------------------------------------
#
#Response for player/55814. Successful:  <Response [200]>
#
#Total successful requests:  55
#Completed :  2.12 %
#Elapsed time:  481.04 s
#------------------------------------------------------------------------------
#
#Response for player/5616. Successful:  <Response [200]>
#
#Total successful requests:  56
#Completed :  2.15 %
#Elapsed time:  483.76 s
#------------------------------------------------------------------------------
#
#Response for player/37737. Successful:  <Response [200]>
#
#Total successful requests:  57
#Completed :  2.19 %
#Elapsed time:  486.74 s
#------------------------------------------------------------------------------
#
#Response for player/6044. Successful:  <Response [200]>
#
#Total successful requests:  58
#Completed :  2.23 %
#Elapsed time:  498.78 s
#------------------------------------------------------------------------------
#
#Response for player/4169. Successful:  <Response [200]>
#
#Total successful requests:  59
#Completed :  2.27 %
#Elapsed time:  500.50 s
#------------------------------------------------------------------------------
#
#Response for player/46973. Successful:  <Response [200]>
#
#Total successful requests:  60
#Completed :  2.31 %
#Elapsed time:  504.14 s
#------------------------------------------------------------------------------
#
#Response for player/42420. Successful:  <Response [200]>
#
#Total successful requests:  61
#Completed :  2.35 %
#Elapsed time:  506.36 s
#------------------------------------------------------------------------------
#
#Response for player/52969. Successful:  <Response [200]>
#
#Total successful requests:  62
#Completed :  2.38 %
#Elapsed time:  511.53 s
#------------------------------------------------------------------------------
#
#Response for player/52066. Successful:  <Response [200]>
#
#Total successful requests:  63
#Completed :  2.42 %
#Elapsed time:  520.69 s
#------------------------------------------------------------------------------
#
#Response for player/8180. Successful:  <Response [200]>
#
#Total successful requests:  64
#Completed :  2.46 %
#Elapsed time:  522.41 s
#------------------------------------------------------------------------------
#
#Response for player/56143. Successful:  <Response [200]>
#
#Total successful requests:  65
#Completed :  2.50 %
#Elapsed time:  532.01 s
#------------------------------------------------------------------------------
#
#Response for player/33335. Successful:  <Response [200]>
#
#Total successful requests:  66
#Completed :  2.54 %
#Elapsed time:  547.65 s
#------------------------------------------------------------------------------
#
#Response for player/52983. Successful:  <Response [200]>
#
#Total successful requests:  67
#Completed :  2.58 %
#Elapsed time:  551.14 s
#------------------------------------------------------------------------------
#
#Response for player/55608. Successful:  <Response [200]>
#
#Total successful requests:  68
#Completed :  2.62 %
#Elapsed time:  564.27 s
#------------------------------------------------------------------------------
#
#Response for player/44485. Successful:  <Response [200]>
#
#Total successful requests:  69
#Completed :  2.65 %
#Elapsed time:  565.73 s
#------------------------------------------------------------------------------
#
#Response for player/56029. Successful:  <Response [200]>
#
#Total successful requests:  70
#Completed :  2.69 %
#Elapsed time:  570.05 s
#------------------------------------------------------------------------------
#
#Response for player/277906. Successful:  <Response [200]>
#
#Total successful requests:  71
#Completed :  2.73 %
#Elapsed time:  578.72 s
#------------------------------------------------------------------------------
#
#Response for player/5939. Successful:  <Response [200]>
#
#Total successful requests:  72
#Completed :  2.77 %
#Elapsed time:  581.69 s
#------------------------------------------------------------------------------
#
#Response for player/9062. Successful:  <Response [200]>
#
#Total successful requests:  73
#Completed :  2.81 %
#Elapsed time:  591.40 s
#------------------------------------------------------------------------------
#
#Response for player/49764. Successful:  <Response [200]>
#
#Total successful requests:  74
#Completed :  2.85 %
#Elapsed time:  593.16 s
#------------------------------------------------------------------------------
#
#Response for player/29632. Successful:  <Response [200]>
#
#Total successful requests:  75
#Completed :  2.88 %
#Elapsed time:  599.55 s
#------------------------------------------------------------------------------
#
#Response for player/28235. Successful:  <Response [200]>
#
#Total successful requests:  76
#Completed :  2.92 %
#Elapsed time:  606.21 s
#------------------------------------------------------------------------------
#
#Response for player/303669. Successful:  <Response [200]>
#
#Total successful requests:  77
#Completed :  2.96 %
#Elapsed time:  633.69 s
#------------------------------------------------------------------------------
#
#Response for player/6513. Successful:  <Response [200]>
#
#Total successful requests:  78
#Completed :  3.00 %
#Elapsed time:  640.69 s
#------------------------------------------------------------------------------
#
#Response for player/28763. Successful:  <Response [200]>
#
#Total successful requests:  79
#Completed :  3.04 %
#Elapsed time:  647.10 s
#------------------------------------------------------------------------------
#
#Response for player/55301. Successful:  <Response [200]>
#
#Total successful requests:  80
#Completed :  3.08 %
#Elapsed time:  653.75 s
#------------------------------------------------------------------------------
#
#Response for player/49626. Successful:  <Response [200]>
#
#Total successful requests:  81
#Completed :  3.12 %
#Elapsed time:  671.03 s
#------------------------------------------------------------------------------
#
#Response for player/51901. Successful:  <Response [200]>
#
#Total successful requests:  82
#Completed :  3.15 %
#Elapsed time:  674.61 s
#------------------------------------------------------------------------------
#
#Response for player/44828. Successful:  <Response [200]>
#
#Total successful requests:  83
#Completed :  3.19 %
#Elapsed time:  679.63 s
#------------------------------------------------------------------------------
#
#Response for player/41378. Successful:  <Response [200]>
#
#Total successful requests:  84
#Completed :  3.23 %
#Elapsed time:  684.39 s
#------------------------------------------------------------------------------
#
#Response for player/10772. Successful:  <Response [200]>
#
#Total successful requests:  85
#Completed :  3.27 %
#Elapsed time:  696.62 s
#------------------------------------------------------------------------------
#
#Response for player/7702. Successful:  <Response [200]>
#
#Total successful requests:  86
#Completed :  3.31 %
#Elapsed time:  699.48 s
#------------------------------------------------------------------------------
#
#Response for player/39836. Successful:  <Response [200]>
#
#Total successful requests:  87
#Completed :  3.35 %
#Elapsed time:  701.52 s
#------------------------------------------------------------------------------
#
#Response for player/44932. Successful:  <Response [200]>
#
#Total successful requests:  88
#Completed :  3.38 %
#Elapsed time:  704.77 s
#------------------------------------------------------------------------------
#
#Response for player/36597. Successful:  <Response [200]>
#
#Total successful requests:  89
#Completed :  3.42 %
#Elapsed time:  709.89 s
#------------------------------------------------------------------------------
#
#Response for player/38967. Successful:  <Response [200]>
#
#Total successful requests:  90
#Completed :  3.46 %
#Elapsed time:  713.76 s
#------------------------------------------------------------------------------
#
#Response for player/37712. Successful:  <Response [200]>
#
#Total successful requests:  91
#Completed :  3.50 %
#Elapsed time:  730.70 s
#------------------------------------------------------------------------------
#
#Response for player/36622. Successful:  <Response [200]>
#
#Total successful requests:  92
#Completed :  3.54 %
#Elapsed time:  738.22 s
#------------------------------------------------------------------------------
#
#Response for player/44111. Successful:  <Response [200]>
#
#Total successful requests:  93
#Completed :  3.58 %
#Elapsed time:  748.02 s
#------------------------------------------------------------------------------
#
#Response for player/20372. Successful:  <Response [200]>
#
#Total successful requests:  94
#Completed :  3.62 %
#Elapsed time:  749.59 s
#------------------------------------------------------------------------------
#
#Response for player/379143. Successful:  <Response [200]>
#
#Total successful requests:  95
#Completed :  3.65 %
#Elapsed time:  756.81 s
#------------------------------------------------------------------------------
#
#Response for player/38407. Successful:  <Response [200]>
#
#Total successful requests:  96
#Completed :  3.69 %
#Elapsed time:  771.43 s
#------------------------------------------------------------------------------
#
#Response for player/19296. Successful:  <Response [200]>
#
#Total successful requests:  97
#Completed :  3.73 %
#Elapsed time:  779.76 s
#------------------------------------------------------------------------------
#
#Response for player/34028. Successful:  <Response [200]>
#
#Total successful requests:  98
#Completed :  3.77 %
#Elapsed time:  808.31 s
#------------------------------------------------------------------------------
#
#Response for player/37232. Successful:  <Response [200]>
#
#Total successful requests:  99
#Completed :  3.81 %
#Elapsed time:  812.66 s
#------------------------------------------------------------------------------
#
#Response for player/6499. Successful:  <Response [200]>
#
#Total successful requests:  100
#Completed :  3.85 %
#Elapsed time:  821.14 s
#------------------------------------------------------------------------------
#
#Response for player/219889. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  101
#Completed :  3.88 %
#Elapsed time:  853.97 s
#------------------------------------------------------------------------------
#
#Response for player/55343. Successful:  <Response [200]>
#
#Total successful requests:  102
#Completed :  3.92 %
#Elapsed time:  867.56 s
#------------------------------------------------------------------------------
#
#Response for player/21585. Successful:  <Response [200]>
#
#Total successful requests:  103
#Completed :  3.96 %
#Elapsed time:  883.56 s
#------------------------------------------------------------------------------
#
#Response for player/13399. Successful:  <Response [200]>
#
#Total successful requests:  104
#Completed :  4.00 %
#Elapsed time:  895.02 s
#------------------------------------------------------------------------------
#
#Response for player/20387. Successful:  <Response [200]>
#
#Total successful requests:  105
#Completed :  4.04 %
#Elapsed time:  927.08 s
#------------------------------------------------------------------------------
#
#Response for player/34103. Successful:  <Response [200]>
#
#Total successful requests:  106
#Completed :  4.08 %
#Elapsed time:  931.70 s
#------------------------------------------------------------------------------
#
#Response for player/5334. Successful:  <Response [200]>
#
#Total successful requests:  107
#Completed :  4.12 %
#Elapsed time:  936.11 s
#------------------------------------------------------------------------------
#
#Response for player/16178. Successful:  <Response [200]>
#
#Total successful requests:  108
#Completed :  4.15 %
#Elapsed time:  955.07 s
#------------------------------------------------------------------------------
#
#Response for player/24611. Successful:  <Response [200]>
#
#Total successful requests:  109
#Completed :  4.19 %
#Elapsed time:  956.74 s
#------------------------------------------------------------------------------
#
#Response for player/48122. Successful:  <Response [200]>
#
#Total successful requests:  110
#Completed :  4.23 %
#Elapsed time:  965.79 s
#------------------------------------------------------------------------------
#
#Response for player/49005. Successful:  <Response [200]>
#
#Total successful requests:  111
#Completed :  4.27 %
#Elapsed time:  967.72 s
#------------------------------------------------------------------------------
#
#Response for player/303427. Successful:  <Response [200]>
#
#Total successful requests:  112
#Completed :  4.31 %
#Elapsed time:  982.06 s
#------------------------------------------------------------------------------
#
#Response for player/38757. Successful:  <Response [200]>
#
#Total successful requests:  113
#Completed :  4.35 %
#Elapsed time:  988.95 s
#------------------------------------------------------------------------------
#
#Response for player/44489. Successful:  <Response [200]>
#
#Total successful requests:  114
#Completed :  4.38 %
#Elapsed time:  997.98 s
#------------------------------------------------------------------------------
#
#Response for player/14187. Successful:  <Response [200]>
#
#Total successful requests:  115
#Completed :  4.42 %
#Elapsed time:  1001.18 s
#------------------------------------------------------------------------------
#
#Response for player/50744. Successful:  <Response [200]>
#
#Total successful requests:  116
#Completed :  4.46 %
#Elapsed time:  1003.93 s
#------------------------------------------------------------------------------
#
#Response for player/30028. Successful:  <Response [200]>
#
#Total successful requests:  117
#Completed :  4.50 %
#Elapsed time:  1010.75 s
#------------------------------------------------------------------------------
#
#Response for player/56025. Successful:  <Response [200]>
#
#Total successful requests:  118
#Completed :  4.54 %
#Elapsed time:  1018.09 s
#------------------------------------------------------------------------------
#
#Response for player/43547. Successful:  <Response [200]>
#
#Total successful requests:  119
#Completed :  4.58 %
#Elapsed time:  1023.32 s
#------------------------------------------------------------------------------
#
#Response for player/49361. Successful:  <Response [200]>
#
#Total successful requests:  120
#Completed :  4.62 %
#Elapsed time:  1027.45 s
#------------------------------------------------------------------------------
#
#Response for player/40560. Successful:  <Response [200]>
#
#Total successful requests:  121
#Completed :  4.65 %
#Elapsed time:  1032.44 s
#------------------------------------------------------------------------------
#
#Response for player/52934. Successful:  <Response [200]>
#
#Total successful requests:  122
#Completed :  4.69 %
#Elapsed time:  1035.58 s
#------------------------------------------------------------------------------
#
#Response for player/15913. Successful:  <Response [200]>
#
#Total successful requests:  123
#Completed :  4.73 %
#Elapsed time:  1037.04 s
#------------------------------------------------------------------------------
#
#Response for player/300628. Successful:  <Response [200]>
#
#Total successful requests:  124
#Completed :  4.77 %
#Elapsed time:  1038.97 s
#------------------------------------------------------------------------------
#
#Response for player/45821. Successful:  <Response [200]>
#
#Total successful requests:  125
#Completed :  4.81 %
#Elapsed time:  1050.25 s
#------------------------------------------------------------------------------
#
#Response for player/308967. Successful:  <Response [200]>
#
#Total successful requests:  126
#Completed :  4.85 %
#Elapsed time:  1059.11 s
#------------------------------------------------------------------------------
#
#Response for player/55870. Successful:  <Response [200]>
#
#Total successful requests:  127
#Completed :  4.88 %
#Elapsed time:  1071.63 s
#------------------------------------------------------------------------------
#
#Response for player/46774. Successful:  <Response [200]>
#
#Total successful requests:  128
#Completed :  4.92 %
#Elapsed time:  1076.23 s
#------------------------------------------------------------------------------
#
#Response for player/7924. Successful:  <Response [200]>
#
#Total successful requests:  129
#Completed :  4.96 %
#Elapsed time:  1081.05 s
#------------------------------------------------------------------------------
#
#Response for player/35654. Successful:  <Response [200]>
#
#Total successful requests:  130
#Completed :  5.00 %
#Elapsed time:  1086.24 s
#------------------------------------------------------------------------------
#
#Response for player/55988. Successful:  <Response [200]>
#
#Total successful requests:  131
#Completed :  5.04 %
#Elapsed time:  1090.50 s
#------------------------------------------------------------------------------
#
#Response for player/24605. Successful:  <Response [200]>
#
#Total successful requests:  132
#Completed :  5.08 %
#Elapsed time:  1098.10 s
#------------------------------------------------------------------------------
#
#Response for player/267192. Successful:  <Response [200]>
#
#Total successful requests:  133
#Completed :  5.12 %
#Elapsed time:  1104.27 s
#------------------------------------------------------------------------------
#
#Response for player/24728. Successful:  <Response [200]>
#
#Total successful requests:  134
#Completed :  5.15 %
#Elapsed time:  1114.24 s
#------------------------------------------------------------------------------
#
#Response for player/44708. Successful:  <Response [200]>
#
#Total successful requests:  135
#Completed :  5.19 %
#Elapsed time:  1120.97 s
#------------------------------------------------------------------------------
#
#Response for player/12856. Successful:  <Response [200]>
#
#Total successful requests:  136
#Completed :  5.23 %
#Elapsed time:  1122.69 s
#------------------------------------------------------------------------------
#
#Response for player/55805. Successful:  <Response [200]>
#
#Total successful requests:  137
#Completed :  5.27 %
#Elapsed time:  1129.59 s
#------------------------------------------------------------------------------
#
#Response for player/47884. Successful:  <Response [200]>
#
#Total successful requests:  138
#Completed :  5.31 %
#Elapsed time:  1132.17 s
#------------------------------------------------------------------------------
#
#Response for player/38117. Successful:  <Response [200]>
#
#Total successful requests:  139
#Completed :  5.35 %
#Elapsed time:  1136.49 s
#------------------------------------------------------------------------------
#
#Response for player/41306. Successful:  <Response [200]>
#
#Total successful requests:  140
#Completed :  5.38 %
#Elapsed time:  1138.91 s
#------------------------------------------------------------------------------
#
#Response for player/41028. Successful:  <Response [200]>
#
#Total successful requests:  141
#Completed :  5.42 %
#Elapsed time:  1153.78 s
#------------------------------------------------------------------------------
#
#Response for player/11728. Successful:  <Response [200]>
#
#Total successful requests:  142
#Completed :  5.46 %
#Elapsed time:  1158.03 s
#------------------------------------------------------------------------------
#
#Response for player/317273. Successful:  <Response [200]>
#
#Total successful requests:  143
#Completed :  5.50 %
#Elapsed time:  1183.00 s
#------------------------------------------------------------------------------
#
#Response for player/13418. Successful:  <Response [200]>
#
#Total successful requests:  144
#Completed :  5.54 %
#Elapsed time:  1191.92 s
#------------------------------------------------------------------------------
#
#Response for player/38258. Successful:  <Response [200]>
#
#Total successful requests:  145
#Completed :  5.58 %
#Elapsed time:  1199.37 s
#------------------------------------------------------------------------------
#
#Response for player/5560. Successful:  <Response [200]>
#
#Total successful requests:  146
#Completed :  5.62 %
#Elapsed time:  1210.78 s
#------------------------------------------------------------------------------
#
#Response for player/33975. Successful:  <Response [200]>
#
#Total successful requests:  147
#Completed :  5.65 %
#Elapsed time:  1213.79 s
#------------------------------------------------------------------------------
#
#Response for player/28794. Successful:  <Response [200]>
#
#Total successful requests:  148
#Completed :  5.69 %
#Elapsed time:  1222.78 s
#------------------------------------------------------------------------------
#
#Response for player/6285. Successful:  <Response [200]>
#
#Total successful requests:  149
#Completed :  5.73 %
#Elapsed time:  1225.48 s
#------------------------------------------------------------------------------
#
#Response for player/4451. Successful:  <Response [200]>
#
#Total successful requests:  150
#Completed :  5.77 %
#Elapsed time:  1234.92 s
#------------------------------------------------------------------------------
#
#Response for player/55787. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  151
#Completed :  5.81 %
#Elapsed time:  1245.32 s
#------------------------------------------------------------------------------
#
#Response for player/298438. Successful:  <Response [200]>
#
#Total successful requests:  152
#Completed :  5.85 %
#Elapsed time:  1258.33 s
#------------------------------------------------------------------------------
#
#Response for player/301236. Successful:  <Response [200]>
#
#Total successful requests:  153
#Completed :  5.88 %
#Elapsed time:  1261.17 s
#------------------------------------------------------------------------------
#
#Response for player/51439. Successful:  <Response [200]>
#
#Total successful requests:  154
#Completed :  5.92 %
#Elapsed time:  1263.13 s
#------------------------------------------------------------------------------
#
#Response for player/277916. Successful:  <Response [200]>
#
#Total successful requests:  155
#Completed :  5.96 %
#Elapsed time:  1266.43 s
#------------------------------------------------------------------------------
#
#Response for player/55761. Successful:  <Response [200]>
#
#Total successful requests:  156
#Completed :  6.00 %
#Elapsed time:  1286.41 s
#------------------------------------------------------------------------------
#
#Response for player/321777. Successful:  <Response [200]>
#
#Total successful requests:  157
#Completed :  6.04 %
#Elapsed time:  1287.44 s
#------------------------------------------------------------------------------
#
#Response for player/52057. Successful:  <Response [200]>
#
#Total successful requests:  158
#Completed :  6.08 %
#Elapsed time:  1289.25 s
#------------------------------------------------------------------------------
#
#Response for player/277472. Successful:  <Response [200]>
#
#Total successful requests:  159
#Completed :  6.12 %
#Elapsed time:  1297.91 s
#------------------------------------------------------------------------------
#
#Response for player/47623. Successful:  <Response [200]>
#
#Total successful requests:  160
#Completed :  6.15 %
#Elapsed time:  1299.12 s
#------------------------------------------------------------------------------
#
#Response for player/52347. Successful:  <Response [200]>
#
#Total successful requests:  161
#Completed :  6.19 %
#Elapsed time:  1306.43 s
#------------------------------------------------------------------------------
#
#Response for player/37491. Successful:  <Response [200]>
#
#Total successful requests:  162
#Completed :  6.23 %
#Elapsed time:  1309.99 s
#------------------------------------------------------------------------------
#
#Response for player/29990. Successful:  <Response [200]>
#
#Total successful requests:  163
#Completed :  6.27 %
#Elapsed time:  1342.55 s
#------------------------------------------------------------------------------
#
#Response for player/6683. Successful:  <Response [200]>
#
#Total successful requests:  164
#Completed :  6.31 %
#Elapsed time:  1356.88 s
#------------------------------------------------------------------------------
#
#Response for player/55307. Successful:  <Response [200]>
#
#Total successful requests:  165
#Completed :  6.35 %
#Elapsed time:  1361.42 s
#------------------------------------------------------------------------------
#
#Response for player/348144. Successful:  <Response [200]>
#
#Total successful requests:  166
#Completed :  6.38 %
#Elapsed time:  1363.10 s
#------------------------------------------------------------------------------
#
#Response for player/42683. Successful:  <Response [200]>
#
#Total successful requests:  167
#Completed :  6.42 %
#Elapsed time:  1365.10 s
#------------------------------------------------------------------------------
#
#Response for player/419873. Successful:  <Response [200]>
#
#Total successful requests:  168
#Completed :  6.46 %
#Elapsed time:  1369.01 s
#------------------------------------------------------------------------------
#
#Response for player/38624. Successful:  <Response [200]>
#
#Total successful requests:  169
#Completed :  6.50 %
#Elapsed time:  1371.71 s
#------------------------------------------------------------------------------
#
#Response for player/55848. Successful:  <Response [200]>
#
#Total successful requests:  170
#Completed :  6.54 %
#Elapsed time:  1378.99 s
#------------------------------------------------------------------------------
#
#Response for player/325026. Successful:  <Response [200]>
#
#Total successful requests:  171
#Completed :  6.58 %
#Elapsed time:  1382.20 s
#------------------------------------------------------------------------------
#
#Response for player/10582. Successful:  <Response [200]>
#
#Total successful requests:  172
#Completed :  6.62 %
#Elapsed time:  1387.52 s
#------------------------------------------------------------------------------
#
#Response for player/41308. Successful:  <Response [200]>
#
#Total successful requests:  173
#Completed :  6.65 %
#Elapsed time:  1395.90 s
#------------------------------------------------------------------------------
#
#Response for player/24249. Successful:  <Response [200]>
#
#Total successful requests:  174
#Completed :  6.69 %
#Elapsed time:  1420.19 s
#------------------------------------------------------------------------------
#
#Response for player/259410. Successful:  <Response [200]>
#
#Total successful requests:  175
#Completed :  6.73 %
#Elapsed time:  1425.10 s
#------------------------------------------------------------------------------
#
#Response for player/25913. Successful:  <Response [200]>
#
#Total successful requests:  176
#Completed :  6.77 %
#Elapsed time:  1427.78 s
#------------------------------------------------------------------------------
#
#Response for player/24289. Successful:  <Response [200]>
#
#Total successful requests:  177
#Completed :  6.81 %
#Elapsed time:  1433.31 s
#------------------------------------------------------------------------------
#
#Response for player/43695. Successful:  <Response [200]>
#
#Total successful requests:  178
#Completed :  6.85 %
#Elapsed time:  1435.92 s
#------------------------------------------------------------------------------
#
#Response for player/45458. Successful:  <Response [200]>
#
#Total successful requests:  179
#Completed :  6.88 %
#Elapsed time:  1443.48 s
#------------------------------------------------------------------------------
#
#Response for player/299572. Successful:  <Response [200]>
#
#Total successful requests:  180
#Completed :  6.92 %
#Elapsed time:  1447.58 s
#------------------------------------------------------------------------------
#
#Response for player/30009. Successful:  <Response [200]>
#
#Total successful requests:  181
#Completed :  6.96 %
#Elapsed time:  1450.83 s
#------------------------------------------------------------------------------
#
#Response for player/280734. Successful:  <Response [200]>
#
#Total successful requests:  182
#Completed :  7.00 %
#Elapsed time:  1455.23 s
#------------------------------------------------------------------------------
#
#Response for player/38062. Successful:  <Response [200]>
#
#Total successful requests:  183
#Completed :  7.04 %
#Elapsed time:  1468.04 s
#------------------------------------------------------------------------------
#
#Response for player/24705. Successful:  <Response [200]>
#
#Total successful requests:  184
#Completed :  7.08 %
#Elapsed time:  1469.80 s
#------------------------------------------------------------------------------
#
#Response for player/249866. Successful:  <Response [200]>
#
#Total successful requests:  185
#Completed :  7.12 %
#Elapsed time:  1474.20 s
#------------------------------------------------------------------------------
#
#Response for player/20263. Successful:  <Response [200]>
#
#Total successful requests:  186
#Completed :  7.15 %
#Elapsed time:  1485.64 s
#------------------------------------------------------------------------------
#
#Response for player/38714. Successful:  <Response [200]>
#
#Total successful requests:  187
#Completed :  7.19 %
#Elapsed time:  1491.29 s
#------------------------------------------------------------------------------
#
#Response for player/388802. Successful:  <Response [200]>
#
#Total successful requests:  188
#Completed :  7.23 %
#Elapsed time:  1508.29 s
#------------------------------------------------------------------------------
#
#Response for player/55354. Successful:  <Response [200]>
#
#Total successful requests:  189
#Completed :  7.27 %
#Elapsed time:  1515.74 s
#------------------------------------------------------------------------------
#
#Response for player/21537. Successful:  <Response [200]>
#
#Total successful requests:  190
#Completed :  7.31 %
#Elapsed time:  1520.80 s
#------------------------------------------------------------------------------
#
#Response for player/30750. Successful:  <Response [200]>
#
#Total successful requests:  191
#Completed :  7.35 %
#Elapsed time:  1527.89 s
#------------------------------------------------------------------------------
#
#Response for player/34059. Successful:  <Response [200]>
#
#Total successful requests:  192
#Completed :  7.38 %
#Elapsed time:  1551.71 s
#------------------------------------------------------------------------------
#
#Response for player/14325. Successful:  <Response [200]>
#
#Total successful requests:  193
#Completed :  7.42 %
#Elapsed time:  1555.84 s
#------------------------------------------------------------------------------
#
#Response for player/4558. Successful:  <Response [200]>
#
#Total successful requests:  194
#Completed :  7.46 %
#Elapsed time:  1561.20 s
#------------------------------------------------------------------------------
#
#Response for player/297433. Successful:  <Response [200]>
#
#Total successful requests:  195
#Completed :  7.50 %
#Elapsed time:  1562.42 s
#------------------------------------------------------------------------------
#
#Response for player/55412. Successful:  <Response [200]>
#
#Total successful requests:  196
#Completed :  7.54 %
#Elapsed time:  1565.72 s
#------------------------------------------------------------------------------
#
#Response for player/311158. Successful:  <Response [200]>
#
#Total successful requests:  197
#Completed :  7.58 %
#Elapsed time:  1568.36 s
#------------------------------------------------------------------------------
#
#Response for player/230559. Successful:  <Response [200]>
#
#Total successful requests:  198
#Completed :  7.62 %
#Elapsed time:  1573.78 s
#------------------------------------------------------------------------------
#
#Response for player/51462. Successful:  <Response [200]>
#
#Total successful requests:  199
#Completed :  7.65 %
#Elapsed time:  1582.71 s
#------------------------------------------------------------------------------
#
#Response for player/300631. Successful:  <Response [200]>
#
#Total successful requests:  200
#Completed :  7.69 %
#Elapsed time:  1587.78 s
#------------------------------------------------------------------------------
#
#Response for page 2 Successful:  <Response [200]> 	=>
#

#list of players:  200
#Response for player/38710. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  201
#Completed :  7.73 %
#Elapsed time:  1626.55 s
#------------------------------------------------------------------------------
#
#Response for player/581379. Successful:  <Response [200]>
#
#Total successful requests:  202
#Completed :  7.77 %
#Elapsed time:  1650.99 s
#------------------------------------------------------------------------------
#
#Response for player/55612. Successful:  <Response [200]>
#
#Total successful requests:  203
#Completed :  7.81 %
#Elapsed time:  1658.57 s
#------------------------------------------------------------------------------
#
#Response for player/8251. Successful:  <Response [200]>
#
#Total successful requests:  204
#Completed :  7.85 %
#Elapsed time:  1664.73 s
#------------------------------------------------------------------------------
#
#Response for player/37105. Successful:  <Response [200]>
#
#Total successful requests:  205
#Completed :  7.88 %
#Elapsed time:  1674.79 s
#------------------------------------------------------------------------------
#
#Response for player/51100. Successful:  <Response [200]>
#
#Total successful requests:  206
#Completed :  7.92 %
#Elapsed time:  1698.64 s
#------------------------------------------------------------------------------
#
#Response for player/56153. Successful:  <Response [200]>
#
#Total successful requests:  207
#Completed :  7.96 %
#Elapsed time:  1701.96 s
#------------------------------------------------------------------------------
#
#Response for player/52917. Successful:  <Response [200]>
#
#Total successful requests:  208
#Completed :  8.00 %
#Elapsed time:  1710.17 s
#------------------------------------------------------------------------------
#
#Response for player/55906. Successful:  <Response [200]>
#
#Total successful requests:  209
#Completed :  8.04 %
#Elapsed time:  1722.45 s
#------------------------------------------------------------------------------
#
#Response for player/233514. Successful:  <Response [200]>
#
#Total successful requests:  210
#Completed :  8.08 %
#Elapsed time:  1731.44 s
#------------------------------------------------------------------------------
#
#Response for player/227760. Successful:  <Response [200]>
#
#Total successful requests:  211
#Completed :  8.12 %
#Elapsed time:  1742.14 s
#------------------------------------------------------------------------------
#
#Response for player/9163. Successful:  <Response [200]>
#
#Total successful requests:  212
#Completed :  8.15 %
#Elapsed time:  1744.05 s
#------------------------------------------------------------------------------
#
#Response for player/13340. Successful:  <Response [200]>
#
#Total successful requests:  213
#Completed :  8.19 %
#Elapsed time:  1751.08 s
#------------------------------------------------------------------------------
#
#Response for player/12803. Successful:  <Response [200]>
#
#Total successful requests:  214
#Completed :  8.23 %
#Elapsed time:  1759.01 s
#------------------------------------------------------------------------------
#
#Response for player/52681. Successful:  <Response [200]>
#
#Total successful requests:  215
#Completed :  8.27 %
#Elapsed time:  1761.50 s
#------------------------------------------------------------------------------
#
#Response for player/25446. Successful:  <Response [200]>
#
#Total successful requests:  216
#Completed :  8.31 %
#Elapsed time:  1765.54 s
#------------------------------------------------------------------------------
#
#Response for player/320652. Successful:  <Response [200]>
#
#Total successful requests:  217
#Completed :  8.35 %
#Elapsed time:  1780.76 s
#------------------------------------------------------------------------------
#
#Response for player/8291. Successful:  <Response [200]>
#
#Total successful requests:  218
#Completed :  8.38 %
#Elapsed time:  1791.27 s
#------------------------------------------------------------------------------
#
#Response for player/24609. Successful:  <Response [200]>
#
#Total successful requests:  219
#Completed :  8.42 %
#Elapsed time:  1802.05 s
#------------------------------------------------------------------------------
#
#Response for player/24752. Successful:  <Response [200]>
#
#Total successful requests:  220
#Completed :  8.46 %
#Elapsed time:  1808.78 s
#------------------------------------------------------------------------------
#
#Response for player/234675. Successful:  <Response [200]>
#
#Total successful requests:  221
#Completed :  8.50 %
#Elapsed time:  1816.41 s
#------------------------------------------------------------------------------
#
#Response for player/43656. Successful:  <Response [200]>
#
#Total successful requests:  222
#Completed :  8.54 %
#Elapsed time:  1818.93 s
#------------------------------------------------------------------------------
#
#Response for player/50804. Successful:  <Response [200]>
#
#Total successful requests:  223
#Completed :  8.58 %
#Elapsed time:  1843.15 s
#------------------------------------------------------------------------------
#
#Response for player/24714. Successful:  <Response [200]>
#
#Total successful requests:  224
#Completed :  8.62 %
#Elapsed time:  1850.60 s
#------------------------------------------------------------------------------
#
#Response for player/533956. Successful:  <Response [200]>
#
#Total successful requests:  225
#Completed :  8.65 %
#Elapsed time:  1853.71 s
#------------------------------------------------------------------------------
#
#Response for player/30934. Successful:  <Response [200]>
#
#Total successful requests:  226
#Completed :  8.69 %
#Elapsed time:  1860.67 s
#------------------------------------------------------------------------------
#
#Response for player/22182. Successful:  <Response [200]>
#
#Total successful requests:  227
#Completed :  8.73 %
#Elapsed time:  1862.03 s
#------------------------------------------------------------------------------
#
#Response for player/52345. Successful:  <Response [200]>
#
#Total successful requests:  228
#Completed :  8.77 %
#Elapsed time:  1864.00 s
#------------------------------------------------------------------------------
#
#Response for player/44956. Successful:  <Response [200]>
#
#Total successful requests:  229
#Completed :  8.81 %
#Elapsed time:  1866.67 s
#------------------------------------------------------------------------------
#
#Response for player/5724. Successful:  <Response [200]>
#
#Total successful requests:  230
#Completed :  8.85 %
#Elapsed time:  1873.85 s
#------------------------------------------------------------------------------
#
#Response for player/23797. Successful:  <Response [200]>
#
#Total successful requests:  231
#Completed :  8.88 %
#Elapsed time:  1889.74 s
#------------------------------------------------------------------------------
#
#Response for player/53116. Successful:  <Response [200]>
#
#Total successful requests:  232
#Completed :  8.92 %
#Elapsed time:  1893.87 s
#------------------------------------------------------------------------------
#
#Response for player/56266. Successful:  <Response [200]>
#
#Total successful requests:  233
#Completed :  8.96 %
#Elapsed time:  1899.07 s
#------------------------------------------------------------------------------
#
#Response for player/232435. Successful:  <Response [200]>
#
#Total successful requests:  234
#Completed :  9.00 %
#Elapsed time:  1901.66 s
#------------------------------------------------------------------------------
#
#Response for player/51657. Successful:  <Response [200]>
#
#Total successful requests:  235
#Completed :  9.04 %
#Elapsed time:  1906.97 s
#------------------------------------------------------------------------------
#
#Response for player/26225. Successful:  <Response [200]>
#
#Total successful requests:  236
#Completed :  9.08 %
#Elapsed time:  1911.54 s
#------------------------------------------------------------------------------
#
#Response for player/51110. Successful:  <Response [200]>
#
#Total successful requests:  237
#Completed :  9.12 %
#Elapsed time:  1915.18 s
#------------------------------------------------------------------------------
#
#Response for player/40563. Successful:  <Response [200]>
#
#Total successful requests:  238
#Completed :  9.15 %
#Elapsed time:  1921.14 s
#------------------------------------------------------------------------------
#
#Response for player/41303. Successful:  <Response [200]>
#
#Total successful requests:  239
#Completed :  9.19 %
#Elapsed time:  1922.82 s
#------------------------------------------------------------------------------
#
#Response for player/36609. Successful:  <Response [200]>
#
#Total successful requests:  240
#Completed :  9.23 %
#Elapsed time:  1924.92 s
#------------------------------------------------------------------------------
#
#Response for player/53115. Successful:  <Response [200]>
#
#Total successful requests:  241
#Completed :  9.27 %
#Elapsed time:  1930.91 s
#------------------------------------------------------------------------------
#
#Response for player/52199. Successful:  <Response [200]>
#
#Total successful requests:  242
#Completed :  9.31 %
#Elapsed time:  1932.94 s
#------------------------------------------------------------------------------
#
#Response for player/32323. Successful:  <Response [200]>
#
#Total successful requests:  243
#Completed :  9.35 %
#Elapsed time:  1934.52 s
#------------------------------------------------------------------------------
#
#Response for player/39037. Successful:  <Response [200]>
#
#Total successful requests:  244
#Completed :  9.38 %
#Elapsed time:  1945.73 s
#------------------------------------------------------------------------------
#
#Response for player/20123. Successful:  <Response [200]>
#
#Total successful requests:  245
#Completed :  9.42 %
#Elapsed time:  1948.75 s
#------------------------------------------------------------------------------
#
#Response for player/55456. Successful:  <Response [200]>
#
#Total successful requests:  246
#Completed :  9.46 %
#Elapsed time:  1951.99 s
#------------------------------------------------------------------------------
#
#Response for player/55954. Successful:  <Response [200]>
#
#Total successful requests:  247
#Completed :  9.50 %
#Elapsed time:  1966.03 s
#------------------------------------------------------------------------------
#
#Response for player/36951. Successful:  <Response [200]>
#
#Total successful requests:  248
#Completed :  9.54 %
#Elapsed time:  1967.97 s
#------------------------------------------------------------------------------
#
#Response for player/5766. Successful:  <Response [200]>
#
#Total successful requests:  249
#Completed :  9.58 %
#Elapsed time:  1973.61 s
#------------------------------------------------------------------------------
#
#Response for player/8579. Successful:  <Response [200]>
#
#Total successful requests:  250
#Completed :  9.62 %
#Elapsed time:  1980.81 s
#------------------------------------------------------------------------------
#
#Response for player/230193. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  251
#Completed :  9.65 %
#Elapsed time:  1983.14 s
#------------------------------------------------------------------------------
#
#Response for player/5628. Successful:  <Response [200]>
#
#Total successful requests:  252
#Completed :  9.69 %
#Elapsed time:  1985.08 s
#------------------------------------------------------------------------------
#
#Response for player/56007. Successful:  <Response [200]>
#
#Total successful requests:  253
#Completed :  9.73 %
#Elapsed time:  1987.54 s
#------------------------------------------------------------------------------
#
#Response for player/37224. Successful:  <Response [200]>
#
#Total successful requests:  254
#Completed :  9.77 %
#Elapsed time:  1997.40 s
#------------------------------------------------------------------------------
#
#Response for player/30045. Successful:  <Response [200]>
#
#Total successful requests:  255
#Completed :  9.81 %
#Elapsed time:  1999.20 s
#------------------------------------------------------------------------------
#
#Response for player/318339. Successful:  <Response [200]>
#
#Total successful requests:  256
#Completed :  9.85 %
#Elapsed time:  2005.12 s
#------------------------------------------------------------------------------
#
#Response for player/40582. Successful:  <Response [200]>
#
#Total successful requests:  257
#Completed :  9.88 %
#Elapsed time:  2017.29 s
#------------------------------------------------------------------------------
#
#Response for player/55854. Successful:  <Response [200]>
#
#Total successful requests:  258
#Completed :  9.92 %
#Elapsed time:  2036.48 s
#------------------------------------------------------------------------------
#
#Response for player/42423. Successful:  <Response [200]>
#
#Total successful requests:  259
#Completed :  9.96 %
#Elapsed time:  2038.10 s
#------------------------------------------------------------------------------
#
#Response for player/49010. Successful:  <Response [200]>
#
#Total successful requests:  260
#Completed :  10.00 %
#Elapsed time:  2040.66 s
#------------------------------------------------------------------------------
#
#Response for player/303423. Successful:  <Response [200]>
#
#Total successful requests:  261
#Completed :  10.04 %
#Elapsed time:  2068.32 s
#------------------------------------------------------------------------------
#
#Response for player/8917. Successful:  <Response [200]>
#
#Total successful requests:  262
#Completed :  10.08 %
#Elapsed time:  2082.79 s
#------------------------------------------------------------------------------
#
#Response for player/33141. Successful:  <Response [200]>
#
#Total successful requests:  263
#Completed :  10.12 %
#Elapsed time:  2085.73 s
#------------------------------------------------------------------------------
#
#Response for player/629074. Successful:  <Response [200]>
#
#Total successful requests:  264
#Completed :  10.15 %
#Elapsed time:  2086.57 s
#------------------------------------------------------------------------------
#
#Response for player/46208. Successful:  <Response [200]>
#
#Total successful requests:  265
#Completed :  10.19 %
#Elapsed time:  2089.00 s
#------------------------------------------------------------------------------
#
#Response for player/55528. Successful:  <Response [200]>
#
#Total successful requests:  266
#Completed :  10.23 %
#Elapsed time:  2097.70 s
#------------------------------------------------------------------------------
#
#Response for player/38929. Successful:  <Response [200]>
#
#Total successful requests:  267
#Completed :  10.27 %
#Elapsed time:  2098.63 s
#------------------------------------------------------------------------------
#
#Response for player/512191. Successful:  <Response [200]>
#
#Total successful requests:  268
#Completed :  10.31 %
#Elapsed time:  2101.06 s
#------------------------------------------------------------------------------
#
#Response for player/25490. Successful:  <Response [200]>
#
#Total successful requests:  269
#Completed :  10.35 %
#Elapsed time:  2111.06 s
#------------------------------------------------------------------------------
#
#Response for player/48369. Successful:  <Response [200]>
#
#Total successful requests:  270
#Completed :  10.38 %
#Elapsed time:  2116.48 s
#------------------------------------------------------------------------------
#
#Response for player/209457. Successful:  <Response [200]>
#
#Total successful requests:  271
#Completed :  10.42 %
#Elapsed time:  2123.14 s
#------------------------------------------------------------------------------
#
#Response for player/38622. Successful:  <Response [200]>
#
#Total successful requests:  272
#Completed :  10.46 %
#Elapsed time:  2125.13 s
#------------------------------------------------------------------------------
#
#Response for player/50431. Successful:  <Response [200]>
#
#Total successful requests:  273
#Completed :  10.50 %
#Elapsed time:  2129.93 s
#------------------------------------------------------------------------------
#
#Response for player/53234. Successful:  <Response [200]>
#
#Total successful requests:  274
#Completed :  10.54 %
#Elapsed time:  2157.58 s
#------------------------------------------------------------------------------
#
#Response for player/42620. Successful:  <Response [200]>
#
#Total successful requests:  275
#Completed :  10.58 %
#Elapsed time:  2161.00 s
#------------------------------------------------------------------------------
#
#Response for player/391485. Successful:  <Response [200]>
#
#Total successful requests:  276
#Completed :  10.62 %
#Elapsed time:  2175.29 s
#------------------------------------------------------------------------------
#
#Response for player/48470. Successful:  <Response [200]>
#
#Total successful requests:  277
#Completed :  10.65 %
#Elapsed time:  2179.60 s
#------------------------------------------------------------------------------
#
#Response for player/429754. Successful:  <Response [200]>
#
#Total successful requests:  278
#Completed :  10.69 %
#Elapsed time:  2184.23 s
#------------------------------------------------------------------------------
#
#Response for player/53118. Successful:  <Response [200]>
#
#Total successful requests:  279
#Completed :  10.73 %
#Elapsed time:  2196.22 s
#------------------------------------------------------------------------------
#
#Response for player/32685. Successful:  <Response [200]>
#
#Total successful requests:  280
#Completed :  10.77 %
#Elapsed time:  2199.19 s
#------------------------------------------------------------------------------
#
#Response for player/47660. Successful:  <Response [200]>
#
#Total successful requests:  281
#Completed :  10.81 %
#Elapsed time:  2208.98 s
#------------------------------------------------------------------------------
#
#Response for player/55497. Successful:  <Response [200]>
#
#Total successful requests:  282
#Completed :  10.85 %
#Elapsed time:  2215.94 s
#------------------------------------------------------------------------------
#
#Response for player/49629. Successful:  <Response [200]>
#
#Total successful requests:  283
#Completed :  10.88 %
#Elapsed time:  2227.84 s
#------------------------------------------------------------------------------
#
#Response for player/39024. Successful:  <Response [200]>
#
#Total successful requests:  284
#Completed :  10.92 %
#Elapsed time:  2231.15 s
#------------------------------------------------------------------------------
#
#Response for player/52445. Successful:  <Response [200]>
#
#Total successful requests:  285
#Completed :  10.96 %
#Elapsed time:  2243.82 s
#------------------------------------------------------------------------------
#
#Response for player/36620. Successful:  <Response [200]>
#
#Total successful requests:  286
#Completed :  11.00 %
#Elapsed time:  2249.98 s
#------------------------------------------------------------------------------
#
#Response for player/45797. Successful:  <Response [200]>
#
#Total successful requests:  287
#Completed :  11.04 %
#Elapsed time:  2258.41 s
#------------------------------------------------------------------------------
#
#Response for player/24719. Successful:  <Response [200]>
#
#Total successful requests:  288
#Completed :  11.08 %
#Elapsed time:  2269.06 s
#------------------------------------------------------------------------------
#
#Response for player/24750. Successful:  <Response [200]>
#
#Total successful requests:  289
#Completed :  11.12 %
#Elapsed time:  2277.64 s
#------------------------------------------------------------------------------
#
#Response for player/436677. Successful:  <Response [200]>
#
#Total successful requests:  290
#Completed :  11.15 %
#Elapsed time:  2294.12 s
#------------------------------------------------------------------------------
#
#Response for player/37696. Successful:  <Response [200]>
#
#Total successful requests:  291
#Completed :  11.19 %
#Elapsed time:  2309.49 s
#------------------------------------------------------------------------------
#
#Response for player/55416. Successful:  <Response [200]>
#
#Total successful requests:  292
#Completed :  11.23 %
#Elapsed time:  2322.11 s
#------------------------------------------------------------------------------
#
#Response for player/272450. Successful:  <Response [200]>
#
#Total successful requests:  293
#Completed :  11.27 %
#Elapsed time:  2325.90 s
#------------------------------------------------------------------------------
#
#Response for player/42321. Successful:  <Response [200]>
#
#Total successful requests:  294
#Completed :  11.31 %
#Elapsed time:  2329.09 s
#------------------------------------------------------------------------------
#
#Response for player/51891. Successful:  <Response [200]>
#
#Total successful requests:  295
#Completed :  11.35 %
#Elapsed time:  2335.51 s
#------------------------------------------------------------------------------
#
#Response for player/44091. Successful:  <Response [200]>
#
#Total successful requests:  296
#Completed :  11.38 %
#Elapsed time:  2337.40 s
#------------------------------------------------------------------------------
#
#Response for player/24708. Successful:  <Response [200]>
#
#Total successful requests:  297
#Completed :  11.42 %
#Elapsed time:  2339.84 s
#------------------------------------------------------------------------------
#
#Response for player/55820. Successful:  <Response [200]>
#
#Total successful requests:  298
#Completed :  11.46 %
#Elapsed time:  2350.60 s
#------------------------------------------------------------------------------
#
#Response for player/7502. Successful:  <Response [200]>
#
#Total successful requests:  299
#Completed :  11.50 %
#Elapsed time:  2363.37 s
#------------------------------------------------------------------------------
#
#Response for player/568276. Successful:  <Response [200]>
#
#Total successful requests:  300
#Completed :  11.54 %
#Elapsed time:  2370.84 s
#------------------------------------------------------------------------------
#
#Response for player/37254. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  301
#Completed :  11.58 %
#Elapsed time:  2376.19 s
#------------------------------------------------------------------------------
#
#Response for player/38373. Successful:  <Response [200]>
#
#Total successful requests:  302
#Completed :  11.62 %
#Elapsed time:  2388.16 s
#------------------------------------------------------------------------------
#
#Response for player/9230. Successful:  <Response [200]>
#
#Total successful requests:  303
#Completed :  11.65 %
#Elapsed time:  2398.52 s
#------------------------------------------------------------------------------
#
#Response for player/24760. Successful:  <Response [200]>
#
#Total successful requests:  304
#Completed :  11.69 %
#Elapsed time:  2408.42 s
#------------------------------------------------------------------------------
#
#Response for player/316397. Successful:  <Response [200]>
#
#Total successful requests:  305
#Completed :  11.73 %
#Elapsed time:  2429.29 s
#------------------------------------------------------------------------------
#
#Response for player/37091. Successful:  <Response [200]>
#
#Total successful requests:  306
#Completed :  11.77 %
#Elapsed time:  2443.21 s
#------------------------------------------------------------------------------
#
#Response for player/49535. Successful:  <Response [200]>
#
#Total successful requests:  307
#Completed :  11.81 %
#Elapsed time:  2445.87 s
#------------------------------------------------------------------------------
#
#Response for player/5702. Successful:  <Response [200]>
#
#Total successful requests:  308
#Completed :  11.85 %
#Elapsed time:  2448.98 s
#------------------------------------------------------------------------------
#
#Response for player/6128. Successful:  <Response [200]>
#
#Total successful requests:  309
#Completed :  11.88 %
#Elapsed time:  2461.25 s
#------------------------------------------------------------------------------
#
#Response for player/318788. Successful:  <Response [200]>
#
#Total successful requests:  310
#Completed :  11.92 %
#Elapsed time:  2466.68 s
#------------------------------------------------------------------------------
#
#Response for player/55935. Successful:  <Response [200]>
#
#Total successful requests:  311
#Completed :  11.96 %
#Elapsed time:  2470.64 s
#------------------------------------------------------------------------------
#
#Response for player/56093. Successful:  <Response [200]>
#
#Total successful requests:  312
#Completed :  12.00 %
#Elapsed time:  2480.28 s
#------------------------------------------------------------------------------
#
#Response for player/291844. Successful:  <Response [200]>
#
#Total successful requests:  313
#Completed :  12.04 %
#Elapsed time:  2490.84 s
#------------------------------------------------------------------------------
#
#Response for player/38393. Successful:  <Response [200]>
#
#Total successful requests:  314
#Completed :  12.08 %
#Elapsed time:  2501.39 s
#------------------------------------------------------------------------------
#
#Response for player/45815. Successful:  <Response [200]>
#
#Total successful requests:  315
#Completed :  12.12 %
#Elapsed time:  2503.40 s
#------------------------------------------------------------------------------
#
#Response for player/333066. Successful:  <Response [200]>
#
#Total successful requests:  316
#Completed :  12.15 %
#Elapsed time:  2509.70 s
#------------------------------------------------------------------------------
#
#Response for player/18675. Successful:  <Response [200]>
#
#Total successful requests:  317
#Completed :  12.19 %
#Elapsed time:  2516.38 s
#------------------------------------------------------------------------------
#
#Response for player/300618. Successful:  <Response [200]>
#
#Total successful requests:  318
#Completed :  12.23 %
#Elapsed time:  2544.35 s
#------------------------------------------------------------------------------
#
#Response for player/530011. Successful:  <Response [200]>
#
#Total successful requests:  319
#Completed :  12.27 %
#Elapsed time:  2546.03 s
#------------------------------------------------------------------------------
#
#Response for player/31036. Successful:  <Response [200]>
#
#Total successful requests:  320
#Completed :  12.31 %
#Elapsed time:  2548.44 s
#------------------------------------------------------------------------------
#
#Response for player/37004. Successful:  <Response [200]>
#
#Total successful requests:  321
#Completed :  12.35 %
#Elapsed time:  2554.50 s
#------------------------------------------------------------------------------
#
#Response for player/524049. Successful:  <Response [200]>
#
#Total successful requests:  322
#Completed :  12.38 %
#Elapsed time:  2572.83 s
#------------------------------------------------------------------------------
#
#Response for player/26184. Successful:  <Response [200]>
#
#Total successful requests:  323
#Completed :  12.42 %
#Elapsed time:  2586.74 s
#------------------------------------------------------------------------------
#
#Response for player/42658. Successful:  <Response [200]>
#
#Total successful requests:  324
#Completed :  12.46 %
#Elapsed time:  2588.82 s
#------------------------------------------------------------------------------
#
#Response for player/39954. Successful:  <Response [200]>
#
#Total successful requests:  325
#Completed :  12.50 %
#Elapsed time:  2611.67 s
#------------------------------------------------------------------------------
#
#Response for player/55872. Successful:  <Response [200]>
#
#Total successful requests:  326
#Completed :  12.54 %
#Elapsed time:  2617.61 s
#------------------------------------------------------------------------------
#
#Response for player/6995. Successful:  <Response [200]>
#
#Total successful requests:  327
#Completed :  12.58 %
#Elapsed time:  2619.93 s
#------------------------------------------------------------------------------
#
#Response for player/318845. Successful:  <Response [200]>
#
#Total successful requests:  328
#Completed :  12.62 %
#Elapsed time:  2622.43 s
#------------------------------------------------------------------------------
#
#Response for player/215155. Successful:  <Response [200]>
#
#Total successful requests:  329
#Completed :  12.65 %
#Elapsed time:  2625.61 s
#------------------------------------------------------------------------------
#
#Response for player/29264. Successful:  <Response [200]>
#
#Total successful requests:  330
#Completed :  12.69 %
#Elapsed time:  2632.49 s
#------------------------------------------------------------------------------
#
#Response for player/6274. Successful:  <Response [200]>
#
#Total successful requests:  331
#Completed :  12.73 %
#Elapsed time:  2644.52 s
#------------------------------------------------------------------------------
#
#Response for player/56251. Successful:  <Response [200]>
#
#Total successful requests:  332
#Completed :  12.77 %
#Elapsed time:  2655.69 s
#------------------------------------------------------------------------------
#
#Response for player/14020. Successful:  <Response [200]>
#
#Total successful requests:  333
#Completed :  12.81 %
#Elapsed time:  2659.92 s
#------------------------------------------------------------------------------
#
#Response for player/31034. Successful:  <Response [200]>
#
#Total successful requests:  334
#Completed :  12.85 %
#Elapsed time:  2663.05 s
#------------------------------------------------------------------------------
#
#Response for player/6502. Successful:  <Response [200]>
#
#Total successful requests:  335
#Completed :  12.88 %
#Elapsed time:  2673.12 s
#------------------------------------------------------------------------------
#
#Response for player/48469. Successful:  <Response [200]>
#
#Total successful requests:  336
#Completed :  12.92 %
#Elapsed time:  2688.36 s
#------------------------------------------------------------------------------
#
#Response for player/373538. Successful:  <Response [200]>
#
#Total successful requests:  337
#Completed :  12.96 %
#Elapsed time:  2703.55 s
#------------------------------------------------------------------------------
#
#Response for player/43121. Successful:  <Response [200]>
#
#Total successful requests:  338
#Completed :  13.00 %
#Elapsed time:  2705.15 s
#------------------------------------------------------------------------------
#
#Response for player/6628. Successful:  <Response [200]>
#
#Total successful requests:  339
#Completed :  13.04 %
#Elapsed time:  2706.92 s
#------------------------------------------------------------------------------
#
#Response for player/55946. Successful:  <Response [200]>
#
#Total successful requests:  340
#Completed :  13.08 %
#Elapsed time:  2726.41 s
#------------------------------------------------------------------------------
#
#Response for player/55973. Successful:  <Response [200]>
#
#Total successful requests:  341
#Completed :  13.12 %
#Elapsed time:  2734.07 s
#------------------------------------------------------------------------------
#
#Response for player/6278. Successful:  <Response [200]>
#
#Total successful requests:  342
#Completed :  13.15 %
#Elapsed time:  2739.35 s
#------------------------------------------------------------------------------
#
#Response for player/290716. Successful:  <Response [200]>
#
#Total successful requests:  343
#Completed :  13.19 %
#Elapsed time:  2743.48 s
#------------------------------------------------------------------------------
#
#Response for player/47015. Successful:  <Response [200]>
#
#Total successful requests:  344
#Completed :  13.23 %
#Elapsed time:  2746.57 s
#------------------------------------------------------------------------------
#
#Response for player/318340. Successful:  <Response [200]>
#
#Total successful requests:  345
#Completed :  13.27 %
#Elapsed time:  2753.07 s
#------------------------------------------------------------------------------
#
#Response for player/232359. Successful:  <Response [200]>
#
#Total successful requests:  346
#Completed :  13.31 %
#Elapsed time:  2758.95 s
#------------------------------------------------------------------------------
#
#Response for player/318334. Successful:  <Response [200]>
#
#Total successful requests:  347
#Completed :  13.35 %
#Elapsed time:  2780.81 s
#------------------------------------------------------------------------------
#
#Response for player/24790. Successful:  <Response [200]>
#
#Total successful requests:  348
#Completed :  13.38 %
#Elapsed time:  2800.56 s
#------------------------------------------------------------------------------
#
#Response for player/461281. Successful:  <Response [200]>
#
#Total successful requests:  349
#Completed :  13.42 %
#Elapsed time:  2809.90 s
#------------------------------------------------------------------------------
#
#Response for player/49638. Successful:  <Response [200]>
#
#Total successful requests:  350
#Completed :  13.46 %
#Elapsed time:  2812.26 s
#------------------------------------------------------------------------------
#
#Response for player/277662. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  351
#Completed :  13.50 %
#Elapsed time:  2818.71 s
#------------------------------------------------------------------------------
#
#Response for player/24701. Successful:  <Response [200]>
#
#Total successful requests:  352
#Completed :  13.54 %
#Elapsed time:  2825.33 s
#------------------------------------------------------------------------------
#
#Response for player/345821. Successful:  <Response [200]>
#
#Total successful requests:  353
#Completed :  13.58 %
#Elapsed time:  2832.44 s
#------------------------------------------------------------------------------
#
#Response for player/214696. Successful:  <Response [200]>
#
#Total successful requests:  354
#Completed :  13.62 %
#Elapsed time:  2834.75 s
#------------------------------------------------------------------------------
#
#Response for player/20286. Successful:  <Response [200]>
#
#Total successful requests:  355
#Completed :  13.65 %
#Elapsed time:  2844.77 s
#------------------------------------------------------------------------------
#
#Response for player/24990. Successful:  <Response [200]>
#
#Total successful requests:  356
#Completed :  13.69 %
#Elapsed time:  2849.09 s
#------------------------------------------------------------------------------
#
#Response for player/55758. Successful:  <Response [200]>
#
#Total successful requests:  357
#Completed :  13.73 %
#Elapsed time:  2854.17 s
#------------------------------------------------------------------------------
#
#Response for player/9187. Successful:  <Response [200]>
#
#Total successful requests:  358
#Completed :  13.77 %
#Elapsed time:  2862.83 s
#------------------------------------------------------------------------------
#
#Response for player/44410. Successful:  <Response [200]>
#
#Total successful requests:  359
#Completed :  13.81 %
#Elapsed time:  2874.50 s
#------------------------------------------------------------------------------
#
#Response for player/37749. Successful:  <Response [200]>
#
#Total successful requests:  360
#Completed :  13.85 %
#Elapsed time:  2878.54 s
#------------------------------------------------------------------------------
#
#Response for player/39013. Successful:  <Response [200]>
#
#Total successful requests:  361
#Completed :  13.88 %
#Elapsed time:  2883.08 s
#------------------------------------------------------------------------------
#
#Response for player/19327. Successful:  <Response [200]>
#
#Total successful requests:  362
#Completed :  13.92 %
#Elapsed time:  2884.71 s
#------------------------------------------------------------------------------
#
#Response for player/247235. Successful:  <Response [200]>
#
#Total successful requests:  363
#Completed :  13.96 %
#Elapsed time:  2886.47 s
#------------------------------------------------------------------------------
#
#Response for player/52962. Successful:  <Response [200]>
#
#Total successful requests:  364
#Completed :  14.00 %
#Elapsed time:  2887.75 s
#------------------------------------------------------------------------------
#
#Response for player/24697. Successful:  <Response [200]>
#
#Total successful requests:  365
#Completed :  14.04 %
#Elapsed time:  2889.69 s
#------------------------------------------------------------------------------
#
#Response for player/38396. Successful:  <Response [200]>
#
#Total successful requests:  366
#Completed :  14.08 %
#Elapsed time:  2922.87 s
#------------------------------------------------------------------------------
#
#Response for player/230855. Successful:  <Response [200]>
#
#Total successful requests:  367
#Completed :  14.12 %
#Elapsed time:  2924.43 s
#------------------------------------------------------------------------------
#
#Response for player/37740. Successful:  <Response [200]>
#
#Total successful requests:  368
#Completed :  14.15 %
#Elapsed time:  2930.67 s
#------------------------------------------------------------------------------
#
#Response for player/37265. Successful:  <Response [200]>
#
#Total successful requests:  369
#Completed :  14.19 %
#Elapsed time:  2944.98 s
#------------------------------------------------------------------------------
#
#Response for player/380354. Successful:  <Response [200]>
#
#Total successful requests:  370
#Completed :  14.23 %
#Elapsed time:  2951.95 s
#------------------------------------------------------------------------------
#
#Response for player/270484. Successful:  <Response [200]>
#
#Total successful requests:  371
#Completed :  14.27 %
#Elapsed time:  2956.21 s
#------------------------------------------------------------------------------
#
#Response for player/539511. Successful:  <Response [200]>
#
#Total successful requests:  372
#Completed :  14.31 %
#Elapsed time:  2971.10 s
#------------------------------------------------------------------------------
#
#Response for player/49368. Successful:  <Response [200]>
#
#Total successful requests:  373
#Completed :  14.35 %
#Elapsed time:  2978.86 s
#------------------------------------------------------------------------------
#
#Response for player/46788. Successful:  <Response [200]>
#
#Total successful requests:  374
#Completed :  14.38 %
#Elapsed time:  2993.65 s
#------------------------------------------------------------------------------
#
#Response for player/8166. Successful:  <Response [200]>
#
#Total successful requests:  375
#Completed :  14.42 %
#Elapsed time:  2995.49 s
#------------------------------------------------------------------------------
#
#Response for player/355269. Successful:  <Response [200]>
#
#Total successful requests:  376
#Completed :  14.46 %
#Elapsed time:  3002.51 s
#------------------------------------------------------------------------------
#
#Response for player/431901. Successful:  <Response [200]>
#
#Total successful requests:  377
#Completed :  14.50 %
#Elapsed time:  3025.41 s
#------------------------------------------------------------------------------
#
#Response for player/32283. Successful:  <Response [200]>
#
#Total successful requests:  378
#Completed :  14.54 %
#Elapsed time:  3028.14 s
#------------------------------------------------------------------------------
#
#Response for player/252932. Successful:  <Response [200]>
#
#Total successful requests:  379
#Completed :  14.58 %
#Elapsed time:  3035.41 s
#------------------------------------------------------------------------------
#
#Response for player/56074. Successful:  <Response [200]>
#
#Total successful requests:  380
#Completed :  14.62 %
#Elapsed time:  3038.28 s
#------------------------------------------------------------------------------
#
#Response for player/36592. Successful:  <Response [200]>
#
#Total successful requests:  381
#Completed :  14.65 %
#Elapsed time:  3045.96 s
#------------------------------------------------------------------------------
#
#Response for player/25430. Successful:  <Response [200]>
#
#Total successful requests:  382
#Completed :  14.69 %
#Elapsed time:  3047.75 s
#------------------------------------------------------------------------------
#
#Response for player/276298. Successful:  <Response [200]>
#
#Total successful requests:  383
#Completed :  14.73 %
#Elapsed time:  3052.95 s
#------------------------------------------------------------------------------
#
#Response for player/55952. Successful:  <Response [200]>
#
#Total successful requests:  384
#Completed :  14.77 %
#Elapsed time:  3054.60 s
#------------------------------------------------------------------------------
#
#Response for player/36595. Successful:  <Response [200]>
#
#Total successful requests:  385
#Completed :  14.81 %
#Elapsed time:  3061.43 s
#------------------------------------------------------------------------------
#
#Response for player/7629. Successful:  <Response [200]>
#
#Total successful requests:  386
#Completed :  14.85 %
#Elapsed time:  3063.36 s
#------------------------------------------------------------------------------
#
#Response for player/37250. Successful:  <Response [200]>
#
#Total successful requests:  387
#Completed :  14.88 %
#Elapsed time:  3066.42 s
#------------------------------------------------------------------------------
#
#Response for player/56221. Successful:  <Response [200]>
#
#Total successful requests:  388
#Completed :  14.92 %
#Elapsed time:  3069.44 s
#------------------------------------------------------------------------------
#
#Response for player/219885. Successful:  <Response [200]>
#
#Total successful requests:  389
#Completed :  14.96 %
#Elapsed time:  3071.18 s
#------------------------------------------------------------------------------
#
#Response for player/56054. Successful:  <Response [200]>
#
#Total successful requests:  390
#Completed :  15.00 %
#Elapsed time:  3089.39 s
#------------------------------------------------------------------------------
#
#Response for player/25120. Successful:  <Response [200]>
#
#Total successful requests:  391
#Completed :  15.04 %
#Elapsed time:  3094.30 s
#------------------------------------------------------------------------------
#
#Response for player/308235. Successful:  <Response [200]>
#
#Total successful requests:  392
#Completed :  15.08 %
#Elapsed time:  3101.79 s
#------------------------------------------------------------------------------
#
#Response for player/43543. Successful:  <Response [200]>
#
#Total successful requests:  393
#Completed :  15.12 %
#Elapsed time:  3108.43 s
#------------------------------------------------------------------------------
#
#Response for player/40250. Successful:  <Response [200]>
#
#Total successful requests:  394
#Completed :  15.15 %
#Elapsed time:  3115.15 s
#------------------------------------------------------------------------------
#
#Response for player/38613. Successful:  <Response [200]>
#
#Total successful requests:  395
#Completed :  15.19 %
#Elapsed time:  3121.10 s
#------------------------------------------------------------------------------
#
#Response for player/24237. Successful:  <Response [200]>
#
#Total successful requests:  396
#Completed :  15.23 %
#Elapsed time:  3135.31 s
#------------------------------------------------------------------------------
#
#Response for player/325012. Successful:  <Response [200]>
#
#Total successful requests:  397
#Completed :  15.27 %
#Elapsed time:  3145.96 s
#------------------------------------------------------------------------------
#
#Response for player/7358. Successful:  <Response [200]>
#
#Total successful requests:  398
#Completed :  15.31 %
#Elapsed time:  3147.77 s
#------------------------------------------------------------------------------
#
#Response for player/25428. Successful:  <Response [200]>
#
#Total successful requests:  399
#Completed :  15.35 %
#Elapsed time:  3166.09 s
#------------------------------------------------------------------------------
#
#Response for player/52419. Successful:  <Response [200]>
#
#Total successful requests:  400
#Completed :  15.38 %
#Elapsed time:  3182.64 s
#------------------------------------------------------------------------------
#
#Response for page 3 Successful:  <Response [200]> 	=>
#

#list of players:  200
#Response for player/417268. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  401
#Completed :  15.42 %
#Elapsed time:  3276.04 s
#------------------------------------------------------------------------------
#
#Response for player/6033. Successful:  <Response [200]>
#
#Total successful requests:  402
#Completed :  15.46 %
#Elapsed time:  3279.24 s
#------------------------------------------------------------------------------
#
#Response for player/49623. Successful:  <Response [200]>
#
#Total successful requests:  403
#Completed :  15.50 %
#Elapsed time:  3325.14 s
#------------------------------------------------------------------------------
#
#Response for player/36581. Successful:  <Response [200]>
#
#Total successful requests:  404
#Completed :  15.54 %
#Elapsed time:  3333.06 s
#------------------------------------------------------------------------------
#
#Response for player/30176. Successful:  <Response [200]>
#
#Total successful requests:  405
#Completed :  15.58 %
#Elapsed time:  3339.95 s
#------------------------------------------------------------------------------
#
#Response for player/38401. Successful:  <Response [200]>
#
#Total successful requests:  406
#Completed :  15.62 %
#Elapsed time:  3341.07 s
#------------------------------------------------------------------------------
#
#Response for player/35582. Successful:  <Response [200]>
#
#Total successful requests:  407
#Completed :  15.65 %
#Elapsed time:  3347.72 s
#------------------------------------------------------------------------------
#
#Response for player/214695. Successful:  <Response [200]>
#
#Total successful requests:  408
#Completed :  15.69 %
#Elapsed time:  3351.01 s
#------------------------------------------------------------------------------
#
#Response for player/51738. Successful:  <Response [200]>
#
#Total successful requests:  409
#Completed :  15.73 %
#Elapsed time:  3356.54 s
#------------------------------------------------------------------------------
#
#Response for player/45396. Successful:  <Response [200]>
#
#Total successful requests:  410
#Completed :  15.77 %
#Elapsed time:  3364.24 s
#------------------------------------------------------------------------------
#
#Response for player/290462. Successful:  <Response [200]>
#
#Total successful requests:  411
#Completed :  15.81 %
#Elapsed time:  3378.37 s
#------------------------------------------------------------------------------
#
#Response for player/670025. Successful:  <Response [200]>
#
#Total successful requests:  412
#Completed :  15.85 %
#Elapsed time:  3382.20 s
#------------------------------------------------------------------------------
#
#Response for player/7252. Successful:  <Response [200]>
#
#Total successful requests:  413
#Completed :  15.88 %
#Elapsed time:  3384.74 s
#------------------------------------------------------------------------------
#
#Response for player/297635. Successful:  <Response [200]>
#
#Total successful requests:  414
#Completed :  15.92 %
#Elapsed time:  3386.97 s
#------------------------------------------------------------------------------
#
#Response for player/34105. Successful:  <Response [200]>
#
#Total successful requests:  415
#Completed :  15.96 %
#Elapsed time:  3393.95 s
#------------------------------------------------------------------------------
#
#Response for player/36075. Successful:  <Response [200]>
#
#Total successful requests:  416
#Completed :  16.00 %
#Elapsed time:  3400.65 s
#------------------------------------------------------------------------------
#
#Response for player/9310. Successful:  <Response [200]>
#
#Total successful requests:  417
#Completed :  16.04 %
#Elapsed time:  3413.29 s
#------------------------------------------------------------------------------
#
#Response for player/49363. Successful:  <Response [200]>
#
#Total successful requests:  418
#Completed :  16.08 %
#Elapsed time:  3415.65 s
#------------------------------------------------------------------------------
#
#Response for player/8119. Successful:  <Response [200]>
#
#Total successful requests:  419
#Completed :  16.12 %
#Elapsed time:  3419.02 s
#------------------------------------------------------------------------------
#
#Response for player/46978. Successful:  <Response [200]>
#
#Total successful requests:  420
#Completed :  16.15 %
#Elapsed time:  3420.99 s
#------------------------------------------------------------------------------
#
#Response for player/55822. Successful:  <Response [200]>
#
#Total successful requests:  421
#Completed :  16.19 %
#Elapsed time:  3422.71 s
#------------------------------------------------------------------------------
#
#Response for player/26802. Successful:  <Response [200]>
#
#Total successful requests:  422
#Completed :  16.23 %
#Elapsed time:  3425.15 s
#------------------------------------------------------------------------------
#
#Response for player/44407. Successful:  <Response [200]>
#
#Total successful requests:  423
#Completed :  16.27 %
#Elapsed time:  3426.54 s
#------------------------------------------------------------------------------
#
#Response for player/440970. Successful:  <Response [200]>
#
#Total successful requests:  424
#Completed :  16.31 %
#Elapsed time:  3437.88 s
#------------------------------------------------------------------------------
#
#Response for player/15501. Successful:  <Response [200]>
#
#Total successful requests:  425
#Completed :  16.35 %
#Elapsed time:  3485.30 s
#------------------------------------------------------------------------------
#
#Response for player/50424. Successful:  <Response [200]>
#
#Total successful requests:  426
#Completed :  16.38 %
#Elapsed time:  3501.86 s
#------------------------------------------------------------------------------
#
#Response for player/7656. Successful:  <Response [200]>
#
#Total successful requests:  427
#Completed :  16.42 %
#Elapsed time:  3502.82 s
#------------------------------------------------------------------------------
#
#Response for player/8535. Successful:  <Response [200]>
#
#Total successful requests:  428
#Completed :  16.46 %
#Elapsed time:  3506.14 s
#------------------------------------------------------------------------------
#
#Response for player/52045. Successful:  <Response [200]>
#
#Total successful requests:  429
#Completed :  16.50 %
#Elapsed time:  3518.23 s
#------------------------------------------------------------------------------
#
#Response for player/7115. Successful:  <Response [200]>
#
#Total successful requests:  430
#Completed :  16.54 %
#Elapsed time:  3523.14 s
#------------------------------------------------------------------------------
#
#Response for player/8581. Successful:  <Response [200]>
#
#Total successful requests:  431
#Completed :  16.58 %
#Elapsed time:  3544.56 s
#------------------------------------------------------------------------------
#
#Response for player/49356. Successful:  <Response [200]>
#
#Total successful requests:  432
#Completed :  16.62 %
#Elapsed time:  3554.94 s
#------------------------------------------------------------------------------
#
#Response for player/50421. Successful:  <Response [200]>
#
#Total successful requests:  433
#Completed :  16.65 %
#Elapsed time:  3556.48 s
#------------------------------------------------------------------------------
#
#Response for player/51872. Successful:  <Response [200]>
#
#Total successful requests:  434
#Completed :  16.69 %
#Elapsed time:  3557.66 s
#------------------------------------------------------------------------------
#
#Response for player/45705. Successful:  <Response [200]>
#
#Total successful requests:  435
#Completed :  16.73 %
#Elapsed time:  3571.66 s
#------------------------------------------------------------------------------
#
#Response for player/46214. Successful:  <Response [200]>
#
#Total successful requests:  436
#Completed :  16.77 %
#Elapsed time:  3574.21 s
#------------------------------------------------------------------------------
#
#Response for player/55329. Successful:  <Response [200]>
#
#Total successful requests:  437
#Completed :  16.81 %
#Elapsed time:  3588.46 s
#------------------------------------------------------------------------------
#
#Response for player/352048. Successful:  <Response [200]>
#
#Total successful requests:  438
#Completed :  16.85 %
#Elapsed time:  3620.69 s
#------------------------------------------------------------------------------
#
#Response for player/452472. Successful:  <Response [200]>
#
#Total successful requests:  439
#Completed :  16.88 %
#Elapsed time:  3635.92 s
#------------------------------------------------------------------------------
#
#Response for player/5696. Successful:  <Response [200]>
#
#Total successful requests:  440
#Completed :  16.92 %
#Elapsed time:  3675.30 s
#------------------------------------------------------------------------------
#
#Response for player/272364. Successful:  <Response [200]>
#
#Total successful requests:  441
#Completed :  16.96 %
#Elapsed time:  3685.25 s
#------------------------------------------------------------------------------
#
#Response for player/52285. Successful:  <Response [200]>
#
#Total successful requests:  442
#Completed :  17.00 %
#Elapsed time:  3703.32 s
#------------------------------------------------------------------------------
#
#Response for player/502714. Successful:  <Response [200]>
#
#Total successful requests:  443
#Completed :  17.04 %
#Elapsed time:  3704.80 s
#------------------------------------------------------------------------------
#
#Response for player/50250. Successful:  <Response [200]>
#
#Total successful requests:  444
#Completed :  17.08 %
#Elapsed time:  3706.33 s
#------------------------------------------------------------------------------
#
#Response for player/8448. Successful:  <Response [200]>
#
#Total successful requests:  445
#Completed :  17.12 %
#Elapsed time:  3712.61 s
#------------------------------------------------------------------------------
#
#Response for player/55840. Successful:  <Response [200]>
#
#Total successful requests:  446
#Completed :  17.15 %
#Elapsed time:  3718.50 s
#------------------------------------------------------------------------------
#
#Response for player/227762. Successful:  <Response [200]>
#
#Total successful requests:  447
#Completed :  17.19 %
#Elapsed time:  3724.77 s
#------------------------------------------------------------------------------
#
#Response for player/32498. Successful:  <Response [200]>
#
#Total successful requests:  448
#Completed :  17.23 %
#Elapsed time:  3731.97 s
#------------------------------------------------------------------------------
#
#Response for player/333000. Successful:  <Response [200]>
#
#Total successful requests:  449
#Completed :  17.27 %
#Elapsed time:  3742.00 s
#------------------------------------------------------------------------------
#
#Response for player/23852. Successful:  <Response [200]>
#
#Total successful requests:  450
#Completed :  17.31 %
#Elapsed time:  3746.85 s
#------------------------------------------------------------------------------
#
#Response for player/793463. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  451
#Completed :  17.35 %
#Elapsed time:  3756.01 s
#------------------------------------------------------------------------------
#
#Response for player/56224. Successful:  <Response [200]>
#
#Total successful requests:  452
#Completed :  17.38 %
#Elapsed time:  3766.31 s
#------------------------------------------------------------------------------
#
#Response for player/30102. Successful:  <Response [200]>
#
#Total successful requests:  453
#Completed :  17.42 %
#Elapsed time:  3786.59 s
#------------------------------------------------------------------------------
#
#Response for player/5681. Successful:  <Response [200]>
#
#Total successful requests:  454
#Completed :  17.46 %
#Elapsed time:  3789.09 s
#------------------------------------------------------------------------------
#
#Response for player/41919. Successful:  <Response [200]>
#
#Total successful requests:  455
#Completed :  17.50 %
#Elapsed time:  3794.97 s
#------------------------------------------------------------------------------
#
#Response for player/50844. Successful:  <Response [200]>
#
#Total successful requests:  456
#Completed :  17.54 %
#Elapsed time:  3815.25 s
#------------------------------------------------------------------------------
#
#Response for player/539304. Successful:  <Response [200]>
#
#Total successful requests:  457
#Completed :  17.58 %
#Elapsed time:  3835.73 s
#------------------------------------------------------------------------------
#
#Response for player/30745. Successful:  <Response [200]>
#
#Total successful requests:  458
#Completed :  17.62 %
#Elapsed time:  3839.69 s
#------------------------------------------------------------------------------
#
#Response for player/23725. Successful:  <Response [200]>
#
#Total successful requests:  459
#Completed :  17.65 %
#Elapsed time:  3842.49 s
#------------------------------------------------------------------------------
#
#Response for player/46248. Successful:  <Response [200]>
#
#Total successful requests:  460
#Completed :  17.69 %
#Elapsed time:  3846.01 s
#------------------------------------------------------------------------------
#
#Response for player/43553. Successful:  <Response [200]>
#
#Total successful requests:  461
#Completed :  17.73 %
#Elapsed time:  3856.36 s
#------------------------------------------------------------------------------
#
#Response for player/56283. Successful:  <Response [200]>
#
#Total successful requests:  462
#Completed :  17.77 %
#Elapsed time:  3865.06 s
#------------------------------------------------------------------------------
#
#Response for player/227758. Successful:  <Response [200]>
#
#Total successful requests:  463
#Completed :  17.81 %
#Elapsed time:  3867.70 s
#------------------------------------------------------------------------------
#
#Response for player/24286. Successful:  <Response [200]>
#
#Total successful requests:  464
#Completed :  17.85 %
#Elapsed time:  3873.34 s
#------------------------------------------------------------------------------
#
#Response for player/42626. Successful:  <Response [200]>
#
#Total successful requests:  465
#Completed :  17.88 %
#Elapsed time:  3876.91 s
#------------------------------------------------------------------------------
#
#Response for player/55408. Successful:  <Response [200]>
#
#Total successful requests:  466
#Completed :  17.92 %
#Elapsed time:  3887.68 s
#------------------------------------------------------------------------------
#
#Response for player/361952. Successful:  <Response [200]>
#
#Total successful requests:  467
#Completed :  17.96 %
#Elapsed time:  3895.03 s
#------------------------------------------------------------------------------
#
#Response for player/12854. Successful:  <Response [200]>
#
#Total successful requests:  468
#Completed :  18.00 %
#Elapsed time:  3920.77 s
#------------------------------------------------------------------------------
#
#Response for player/5001. Successful:  <Response [200]>
#
#Total successful requests:  469
#Completed :  18.04 %
#Elapsed time:  3923.17 s
#------------------------------------------------------------------------------
#
#Response for player/293983. Successful:  <Response [200]>
#
#Total successful requests:  470
#Completed :  18.08 %
#Elapsed time:  3925.30 s
#------------------------------------------------------------------------------
#
#Response for player/55346. Successful:  <Response [200]>
#
#Total successful requests:  471
#Completed :  18.12 %
#Elapsed time:  3929.50 s
#------------------------------------------------------------------------------
#
#Response for player/12884. Successful:  <Response [200]>
#
#Total successful requests:  472
#Completed :  18.15 %
#Elapsed time:  3945.47 s
#------------------------------------------------------------------------------
#
#Response for player/6038. Successful:  <Response [200]>
#
#Total successful requests:  473
#Completed :  18.19 %
#Elapsed time:  3948.74 s
#------------------------------------------------------------------------------
#
#Response for player/41262. Successful:  <Response [200]>
#
#Total successful requests:  474
#Completed :  18.23 %
#Elapsed time:  3991.52 s
#------------------------------------------------------------------------------
#
#Response for player/23826. Successful:  <Response [200]>
#
#Total successful requests:  475
#Completed :  18.27 %
#Elapsed time:  3993.75 s
#------------------------------------------------------------------------------
#
#Response for player/32242. Successful:  <Response [200]>
#
#Total successful requests:  476
#Completed :  18.31 %
#Elapsed time:  4000.12 s
#------------------------------------------------------------------------------
#
#Response for player/43266. Successful:  <Response [200]>
#
#Total successful requests:  477
#Completed :  18.35 %
#Elapsed time:  4003.96 s
#------------------------------------------------------------------------------
#
#Response for player/297488. Successful:  <Response [200]>
#
#Total successful requests:  478
#Completed :  18.38 %
#Elapsed time:  4010.03 s
#------------------------------------------------------------------------------
#
#Response for player/38009. Successful:  <Response [200]>
#
#Total successful requests:  479
#Completed :  18.42 %
#Elapsed time:  4011.30 s
#------------------------------------------------------------------------------
#
#Response for player/625371. Successful:  <Response [200]>
#
#Total successful requests:  480
#Completed :  18.46 %
#Elapsed time:  4018.96 s
#------------------------------------------------------------------------------
#
#Response for player/21466. Successful:  <Response [200]>
#
#Total successful requests:  481
#Completed :  18.50 %
#Elapsed time:  4020.43 s
#------------------------------------------------------------------------------
#
#Response for player/12466. Successful:  <Response [200]>
#
#Total successful requests:  482
#Completed :  18.54 %
#Elapsed time:  4021.47 s
#------------------------------------------------------------------------------
#
#Response for player/5597. Successful:  <Response [200]>
#
#Total successful requests:  483
#Completed :  18.58 %
#Elapsed time:  4029.75 s
#------------------------------------------------------------------------------
#
#Response for player/42628. Successful:  <Response [200]>
#
#Total successful requests:  484
#Completed :  18.62 %
#Elapsed time:  4042.28 s
#------------------------------------------------------------------------------
#
#Response for player/23460. Successful:  <Response [200]>
#
#Total successful requests:  485
#Completed :  18.65 %
#Elapsed time:  4050.64 s
#------------------------------------------------------------------------------
#
#Response for player/323389. Successful:  <Response [200]>
#
#Total successful requests:  486
#Completed :  18.69 %
#Elapsed time:  4055.67 s
#------------------------------------------------------------------------------
#
#Response for player/49633. Successful:  <Response [200]>
#
#Total successful requests:  487
#Completed :  18.73 %
#Elapsed time:  4062.68 s
#------------------------------------------------------------------------------
#
#Response for player/53214. Successful:  <Response [200]>
#
#Total successful requests:  488
#Completed :  18.77 %
#Elapsed time:  4065.89 s
#------------------------------------------------------------------------------
#
#Response for player/55414. Successful:  <Response [200]>
#
#Total successful requests:  489
#Completed :  18.81 %
#Elapsed time:  4073.19 s
#------------------------------------------------------------------------------
#
#Response for player/47267. Successful:  <Response [200]>
#
#Total successful requests:  490
#Completed :  18.85 %
#Elapsed time:  4083.61 s
#------------------------------------------------------------------------------
#
#Response for player/220519. Successful:  <Response [200]>
#
#Total successful requests:  491
#Completed :  18.88 %
#Elapsed time:  4085.27 s
#------------------------------------------------------------------------------
#
#Response for player/11865. Successful:  <Response [200]>
#
#Total successful requests:  492
#Completed :  18.92 %
#Elapsed time:  4095.11 s
#------------------------------------------------------------------------------
#
#Response for player/465793. Successful:  <Response [200]>
#
#Total successful requests:  493
#Completed :  18.96 %
#Elapsed time:  4096.70 s
#------------------------------------------------------------------------------
#
#Response for player/51659. Successful:  <Response [200]>
#
#Total successful requests:  494
#Completed :  19.00 %
#Elapsed time:  4098.16 s
#------------------------------------------------------------------------------
#
#Response for player/52442. Successful:  <Response [200]>
#
#Total successful requests:  495
#Completed :  19.04 %
#Elapsed time:  4109.28 s
#------------------------------------------------------------------------------
#
#Response for player/26421. Successful:  <Response [200]>
#
#Total successful requests:  496
#Completed :  19.08 %
#Elapsed time:  4118.31 s
#------------------------------------------------------------------------------
#
#Response for player/350629. Successful:  <Response [200]>
#
#Total successful requests:  497
#Completed :  19.12 %
#Elapsed time:  4131.78 s
#------------------------------------------------------------------------------
#
#Response for player/49636. Successful:  <Response [200]>
#
#Total successful requests:  498
#Completed :  19.15 %
#Elapsed time:  4133.04 s
#------------------------------------------------------------------------------
#
#Response for player/4560. Successful:  <Response [200]>
#
#Total successful requests:  499
#Completed :  19.19 %
#Elapsed time:  4140.91 s
#------------------------------------------------------------------------------
#
#Response for player/55578. Successful:  <Response [200]>
#
#Total successful requests:  500
#Completed :  19.23 %
#Elapsed time:  4147.67 s
#------------------------------------------------------------------------------
#
#Response for player/820351. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  501
#Completed :  19.27 %
#Elapsed time:  4160.75 s
#------------------------------------------------------------------------------
#
#Response for player/49125. Successful:  <Response [200]>
#
#Total successful requests:  502
#Completed :  19.31 %
#Elapsed time:  4162.47 s
#------------------------------------------------------------------------------
#
#Response for player/232364. Successful:  <Response [200]>
#
#Total successful requests:  503
#Completed :  19.35 %
#Elapsed time:  4169.27 s
#------------------------------------------------------------------------------
#
#Response for player/44102. Successful:  <Response [200]>
#
#Total successful requests:  504
#Completed :  19.38 %
#Elapsed time:  4181.26 s
#------------------------------------------------------------------------------
#
#Response for player/5236. Successful:  <Response [200]>
#
#Total successful requests:  505
#Completed :  19.42 %
#Elapsed time:  4186.95 s
#------------------------------------------------------------------------------
#
#Response for player/307808. Successful:  <Response [200]>
#
#Total successful requests:  506
#Completed :  19.46 %
#Elapsed time:  4188.91 s
#------------------------------------------------------------------------------
#
#Response for player/33066. Successful:  <Response [200]>
#
#Total successful requests:  507
#Completed :  19.50 %
#Elapsed time:  4198.39 s
#------------------------------------------------------------------------------
#
#Response for player/42362. Successful:  <Response [200]>
#
#Total successful requests:  508
#Completed :  19.54 %
#Elapsed time:  4199.18 s
#------------------------------------------------------------------------------
#
#Response for player/38973. Successful:  <Response [200]>
#
#Total successful requests:  509
#Completed :  19.58 %
#Elapsed time:  4204.98 s
#------------------------------------------------------------------------------
#
#Response for player/14153. Successful:  <Response [200]>
#
#Total successful requests:  510
#Completed :  19.62 %
#Elapsed time:  4217.03 s
#------------------------------------------------------------------------------
#
#Response for player/51107. Successful:  <Response [200]>
#
#Total successful requests:  511
#Completed :  19.65 %
#Elapsed time:  4219.16 s
#------------------------------------------------------------------------------
#
#Response for player/38246. Successful:  <Response [200]>
#
#Total successful requests:  512
#Completed :  19.69 %
#Elapsed time:  4224.93 s
#------------------------------------------------------------------------------
#
#Response for player/24964. Successful:  <Response [200]>
#
#Total successful requests:  513
#Completed :  19.73 %
#Elapsed time:  4227.59 s
#------------------------------------------------------------------------------
#
#Response for player/26948. Successful:  <Response [200]>
#
#Total successful requests:  514
#Completed :  19.77 %
#Elapsed time:  4237.18 s
#------------------------------------------------------------------------------
#
#Response for player/37601. Successful:  <Response [200]>
#
#Total successful requests:  515
#Completed :  19.81 %
#Elapsed time:  4250.77 s
#------------------------------------------------------------------------------
#
#Response for player/334337. Successful:  <Response [200]>
#
#Total successful requests:  516
#Completed :  19.85 %
#Elapsed time:  4261.30 s
#------------------------------------------------------------------------------
#
#Response for player/55259. Successful:  <Response [200]>
#
#Total successful requests:  517
#Completed :  19.88 %
#Elapsed time:  4265.37 s
#------------------------------------------------------------------------------
#
#Response for player/38008. Successful:  <Response [200]>
#
#Total successful requests:  518
#Completed :  19.92 %
#Elapsed time:  4267.13 s
#------------------------------------------------------------------------------
#
#Response for player/38118. Successful:  <Response [200]>
#
#Total successful requests:  519
#Completed :  19.96 %
#Elapsed time:  4282.91 s
#------------------------------------------------------------------------------
#
#Response for player/267455. Successful:  <Response [200]>
#
#Total successful requests:  520
#Completed :  20.00 %
#Elapsed time:  4286.70 s
#------------------------------------------------------------------------------
#
#Response for player/6525. Successful:  <Response [200]>
#
#Total successful requests:  521
#Completed :  20.04 %
#Elapsed time:  4296.15 s
#------------------------------------------------------------------------------
#
#Response for player/974719. Successful:  <Response [200]>
#
#Total successful requests:  522
#Completed :  20.08 %
#Elapsed time:  4300.55 s
#------------------------------------------------------------------------------
#
#Response for player/49700. Successful:  <Response [200]>
#
#Total successful requests:  523
#Completed :  20.12 %
#Elapsed time:  4306.91 s
#------------------------------------------------------------------------------
#
#Response for player/33058. Successful:  <Response [200]>
#
#Total successful requests:  524
#Completed :  20.15 %
#Elapsed time:  4311.63 s
#------------------------------------------------------------------------------
#
#Response for player/55713. Successful:  <Response [200]>
#
#Total successful requests:  525
#Completed :  20.19 %
#Elapsed time:  4315.43 s
#------------------------------------------------------------------------------
#
#Response for player/51208. Successful:  <Response [200]>
#
#Total successful requests:  526
#Completed :  20.23 %
#Elapsed time:  4326.09 s
#------------------------------------------------------------------------------
#
#Response for player/50249. Successful:  <Response [200]>
#
#Total successful requests:  527
#Completed :  20.27 %
#Elapsed time:  4328.88 s
#------------------------------------------------------------------------------
#
#Response for player/44149. Successful:  <Response [200]>
#
#Total successful requests:  528
#Completed :  20.31 %
#Elapsed time:  4333.58 s
#------------------------------------------------------------------------------
#
#Response for player/13411. Successful:  <Response [200]>
#
#Total successful requests:  529
#Completed :  20.35 %
#Elapsed time:  4336.32 s
#------------------------------------------------------------------------------
#
#Response for player/14244. Successful:  <Response [200]>
#
#Total successful requests:  530
#Completed :  20.38 %
#Elapsed time:  4338.00 s
#------------------------------------------------------------------------------
#
#Response for player/293831. Successful:  <Response [200]>
#
#Total successful requests:  531
#Completed :  20.42 %
#Elapsed time:  4341.85 s
#------------------------------------------------------------------------------
#
#Response for player/52059. Successful:  <Response [200]>
#
#Total successful requests:  532
#Completed :  20.46 %
#Elapsed time:  4358.20 s
#------------------------------------------------------------------------------
#
#Response for player/19445. Successful:  <Response [200]>
#
#Total successful requests:  533
#Completed :  20.50 %
#Elapsed time:  4359.74 s
#------------------------------------------------------------------------------
#
#Response for player/6250. Successful:  <Response [200]>
#
#Total successful requests:  534
#Completed :  20.54 %
#Elapsed time:  4361.77 s
#------------------------------------------------------------------------------
#
#Response for player/41263. Successful:  <Response [200]>
#
#Total successful requests:  535
#Completed :  20.58 %
#Elapsed time:  4365.17 s
#------------------------------------------------------------------------------
#
#Response for player/19264. Successful:  <Response [200]>
#
#Total successful requests:  536
#Completed :  20.62 %
#Elapsed time:  4374.60 s
#------------------------------------------------------------------------------
#
#Response for player/16203. Successful:  <Response [200]>
#
#Total successful requests:  537
#Completed :  20.65 %
#Elapsed time:  4391.97 s
#------------------------------------------------------------------------------
#
#Response for player/23681. Successful:  <Response [200]>
#
#Total successful requests:  538
#Completed :  20.69 %
#Elapsed time:  4400.17 s
#------------------------------------------------------------------------------
#
#Response for player/43590. Successful:  <Response [200]>
#
#Total successful requests:  539
#Completed :  20.73 %
#Elapsed time:  4402.61 s
#------------------------------------------------------------------------------
#
#Response for player/38058. Successful:  <Response [200]>
#
#Total successful requests:  540
#Completed :  20.77 %
#Elapsed time:  4408.08 s
#------------------------------------------------------------------------------
#
#Response for player/29725. Successful:  <Response [200]>
#
#Total successful requests:  541
#Completed :  20.81 %
#Elapsed time:  4412.98 s
#------------------------------------------------------------------------------
#
#Response for player/536936. Successful:  <Response [200]>
#
#Total successful requests:  542
#Completed :  20.85 %
#Elapsed time:  4414.78 s
#------------------------------------------------------------------------------
#
#Response for player/37602. Successful:  <Response [200]>
#
#Total successful requests:  543
#Completed :  20.88 %
#Elapsed time:  4421.50 s
#------------------------------------------------------------------------------
#
#Response for player/25589. Successful:  <Response [200]>
#
#Total successful requests:  544
#Completed :  20.92 %
#Elapsed time:  4425.42 s
#------------------------------------------------------------------------------
#
#Response for player/314615. Successful:  <Response [200]>
#
#Total successful requests:  545
#Completed :  20.96 %
#Elapsed time:  4426.22 s
#------------------------------------------------------------------------------
#
#Response for player/348034. Successful:  <Response [200]>
#
#Total successful requests:  546
#Completed :  21.00 %
#Elapsed time:  4434.39 s
#------------------------------------------------------------------------------
#
#Response for player/360456. Successful:  <Response [200]>
#
#Total successful requests:  547
#Completed :  21.04 %
#Elapsed time:  4443.90 s
#------------------------------------------------------------------------------
#
#Response for player/5674. Successful:  <Response [200]>
#
#Total successful requests:  548
#Completed :  21.08 %
#Elapsed time:  4457.57 s
#------------------------------------------------------------------------------
#
#Response for player/46987. Successful:  <Response [200]>
#
#Total successful requests:  549
#Completed :  21.12 %
#Elapsed time:  4463.31 s
#------------------------------------------------------------------------------
#
#Response for player/56186. Successful:  <Response [200]>
#
#Total successful requests:  550
#Completed :  21.15 %
#Elapsed time:  4465.69 s
#------------------------------------------------------------------------------
#
#Response for player/38924. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  551
#Completed :  21.19 %
#Elapsed time:  4471.65 s
#------------------------------------------------------------------------------
#
#Response for player/22403. Successful:  <Response [200]>
#
#Total successful requests:  552
#Completed :  21.23 %
#Elapsed time:  4473.34 s
#------------------------------------------------------------------------------
#
#Response for player/25451. Successful:  <Response [200]>
#
#Total successful requests:  553
#Completed :  21.27 %
#Elapsed time:  4477.61 s
#------------------------------------------------------------------------------
#
#Response for player/31038. Successful:  <Response [200]>
#
#Total successful requests:  554
#Completed :  21.31 %
#Elapsed time:  4502.17 s
#------------------------------------------------------------------------------
#
#Response for player/373696. Successful:  <Response [200]>
#
#Total successful requests:  555
#Completed :  21.35 %
#Elapsed time:  4505.30 s
#------------------------------------------------------------------------------
#
#Response for player/38965. Successful:  <Response [200]>
#
#Total successful requests:  556
#Completed :  21.38 %
#Elapsed time:  4511.33 s
#------------------------------------------------------------------------------
#
#Response for player/46750. Successful:  <Response [200]>
#
#Total successful requests:  557
#Completed :  21.42 %
#Elapsed time:  4513.86 s
#------------------------------------------------------------------------------
#
#Response for player/235516. Successful:  <Response [200]>
#
#Total successful requests:  558
#Completed :  21.46 %
#Elapsed time:  4514.62 s
#------------------------------------------------------------------------------
#
#Response for player/4161. Successful:  <Response [200]>
#
#Total successful requests:  559
#Completed :  21.50 %
#Elapsed time:  4524.06 s
#------------------------------------------------------------------------------
#
#Response for player/230549. Successful:  <Response [200]>
#
#Total successful requests:  560
#Completed :  21.54 %
#Elapsed time:  4528.02 s
#------------------------------------------------------------------------------
#
#Response for player/49758. Successful:  <Response [200]>
#
#Total successful requests:  561
#Completed :  21.58 %
#Elapsed time:  4542.63 s
#------------------------------------------------------------------------------
#
#Response for player/55438. Successful:  <Response [200]>
#
#Total successful requests:  562
#Completed :  21.62 %
#Elapsed time:  4546.57 s
#------------------------------------------------------------------------------
#
#Response for player/55391. Successful:  <Response [200]>
#
#Total successful requests:  563
#Completed :  21.65 %
#Elapsed time:  4554.27 s
#------------------------------------------------------------------------------
#
#Response for player/41297. Successful:  <Response [200]>
#
#Total successful requests:  564
#Completed :  21.69 %
#Elapsed time:  4561.92 s
#------------------------------------------------------------------------------
#
#Response for player/244497. Successful:  <Response [200]>
#
#Total successful requests:  565
#Completed :  21.73 %
#Elapsed time:  4569.26 s
#------------------------------------------------------------------------------
#
#Response for player/45840. Successful:  <Response [200]>
#
#Total successful requests:  566
#Completed :  21.77 %
#Elapsed time:  4581.90 s
#------------------------------------------------------------------------------
#
#Response for player/22442. Successful:  <Response [200]>
#
#Total successful requests:  567
#Completed :  21.81 %
#Elapsed time:  4596.64 s
#------------------------------------------------------------------------------
#
#Response for player/38398. Successful:  <Response [200]>
#
#Total successful requests:  568
#Completed :  21.85 %
#Elapsed time:  4608.40 s
#------------------------------------------------------------------------------
#
#Response for player/56227. Successful:  <Response [200]>
#
#Total successful requests:  569
#Completed :  21.88 %
#Elapsed time:  4613.48 s
#------------------------------------------------------------------------------
#
#Response for player/23850. Successful:  <Response [200]>
#
#Total successful requests:  570
#Completed :  21.92 %
#Elapsed time:  4628.31 s
#------------------------------------------------------------------------------
#
#Response for player/10617. Successful:  <Response [200]>
#
#Total successful requests:  571
#Completed :  21.96 %
#Elapsed time:  4633.86 s
#------------------------------------------------------------------------------
#
#Response for player/238612. Successful:  <Response [200]>
#
#Total successful requests:  572
#Completed :  22.00 %
#Elapsed time:  4636.06 s
#------------------------------------------------------------------------------
#
#Response for player/42272. Successful:  <Response [200]>
#
#Total successful requests:  573
#Completed :  22.04 %
#Elapsed time:  4639.58 s
#------------------------------------------------------------------------------
#
#Response for player/326016. Successful:  <Response [200]>
#
#Total successful requests:  574
#Completed :  22.08 %
#Elapsed time:  4642.64 s
#------------------------------------------------------------------------------
#
#Response for player/302845. Successful:  <Response [200]>
#
#Total successful requests:  575
#Completed :  22.12 %
#Elapsed time:  4650.45 s
#------------------------------------------------------------------------------
#
#Response for player/39745. Successful:  <Response [200]>
#
#Total successful requests:  576
#Completed :  22.15 %
#Elapsed time:  4655.01 s
#------------------------------------------------------------------------------
#
#Response for player/37101. Successful:  <Response [200]>
#
#Total successful requests:  577
#Completed :  22.19 %
#Elapsed time:  4664.75 s
#------------------------------------------------------------------------------
#
#Response for player/245166. Successful:  <Response [200]>
#
#Total successful requests:  578
#Completed :  22.23 %
#Elapsed time:  4672.29 s
#------------------------------------------------------------------------------
#
#Response for player/55388. Successful:  <Response [200]>
#
#Total successful requests:  579
#Completed :  22.27 %
#Elapsed time:  4680.13 s
#------------------------------------------------------------------------------
#
#Response for player/600498. Successful:  <Response [200]>
#
#Total successful requests:  580
#Completed :  22.31 %
#Elapsed time:  4695.87 s
#------------------------------------------------------------------------------
#
#Response for player/26238. Successful:  <Response [200]>
#
#Total successful requests:  581
#Completed :  22.35 %
#Elapsed time:  4710.87 s
#------------------------------------------------------------------------------
#
#Response for player/222354. Successful:  <Response [200]>
#
#Total successful requests:  582
#Completed :  22.38 %
#Elapsed time:  4712.54 s
#------------------------------------------------------------------------------
#
#Response for player/8151. Successful:  <Response [200]>
#
#Total successful requests:  583
#Completed :  22.42 %
#Elapsed time:  4721.33 s
#------------------------------------------------------------------------------
#
#Response for player/36306. Successful:  <Response [200]>
#
#Total successful requests:  584
#Completed :  22.46 %
#Elapsed time:  4743.51 s
#------------------------------------------------------------------------------
#
#Response for player/55825. Successful:  <Response [200]>
#
#Total successful requests:  585
#Completed :  22.50 %
#Elapsed time:  4758.26 s
#------------------------------------------------------------------------------
#
#Response for player/9208. Successful:  <Response [200]>
#
#Total successful requests:  586
#Completed :  22.54 %
#Elapsed time:  4759.93 s
#------------------------------------------------------------------------------
#
#Response for player/265564. Successful:  <Response [200]>
#
#Total successful requests:  587
#Completed :  22.58 %
#Elapsed time:  4762.60 s
#------------------------------------------------------------------------------
#
#Response for player/24723. Successful:  <Response [200]>
#
#Total successful requests:  588
#Completed :  22.62 %
#Elapsed time:  4765.10 s
#------------------------------------------------------------------------------
#
#Response for player/46934. Successful:  <Response [200]>
#
#Total successful requests:  589
#Completed :  22.65 %
#Elapsed time:  4766.31 s
#------------------------------------------------------------------------------
#
#Response for player/43363. Successful:  <Response [200]>
#
#Total successful requests:  590
#Completed :  22.69 %
#Elapsed time:  4768.26 s
#------------------------------------------------------------------------------
#
#Response for player/7326. Successful:  <Response [200]>
#
#Total successful requests:  591
#Completed :  22.73 %
#Elapsed time:  4769.93 s
#------------------------------------------------------------------------------
#
#Response for player/516561. Successful:  <Response [200]>
#
#Total successful requests:  592
#Completed :  22.77 %
#Elapsed time:  4770.89 s
#------------------------------------------------------------------------------
#
#Response for player/12514. Successful:  <Response [200]>
#
#Total successful requests:  593
#Completed :  22.81 %
#Elapsed time:  4778.23 s
#------------------------------------------------------------------------------
#
#Response for player/950303. Successful:  <Response [200]>
#
#Total successful requests:  594
#Completed :  22.85 %
#Elapsed time:  4785.76 s
#------------------------------------------------------------------------------
#
#Response for player/20431. Successful:  <Response [200]>
#
#Total successful requests:  595
#Completed :  22.88 %
#Elapsed time:  4793.72 s
#------------------------------------------------------------------------------
#
#Response for player/23694. Successful:  <Response [200]>
#
#Total successful requests:  596
#Completed :  22.92 %
#Elapsed time:  4795.73 s
#------------------------------------------------------------------------------
#
#Response for player/44416. Successful:  <Response [200]>
#
#Total successful requests:  597
#Completed :  22.96 %
#Elapsed time:  4813.58 s
#------------------------------------------------------------------------------
#
#Response for player/56035. Successful:  <Response [200]>
#
#Total successful requests:  598
#Completed :  23.00 %
#Elapsed time:  4817.44 s
#------------------------------------------------------------------------------
#
#Response for player/11974. Successful:  <Response [200]>
#
#Total successful requests:  599
#Completed :  23.04 %
#Elapsed time:  4838.48 s
#------------------------------------------------------------------------------
#
#Response for player/51488. Successful:  <Response [200]>
#
#Total successful requests:  600
#Completed :  23.08 %
#Elapsed time:  4841.08 s
#------------------------------------------------------------------------------
#
#Response for page 4 Successful:  <Response [200]> 	=>
#

#list of players:  200
#Response for player/46393. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  601
#Completed :  23.12 %
#Elapsed time:  4919.66 s
#------------------------------------------------------------------------------
#
#Response for player/8105. Successful:  <Response [200]>
#
#Total successful requests:  602
#Completed :  23.15 %
#Elapsed time:  4921.47 s
#------------------------------------------------------------------------------
#
#Response for player/51446. Successful:  <Response [200]>
#
#Total successful requests:  603
#Completed :  23.19 %
#Elapsed time:  4923.00 s
#------------------------------------------------------------------------------
#
#Response for player/23899. Successful:  <Response [200]>
#
#Total successful requests:  604
#Completed :  23.23 %
#Elapsed time:  4927.92 s
#------------------------------------------------------------------------------
#
#Response for player/315594. Successful:  <Response [200]>
#
#Total successful requests:  605
#Completed :  23.27 %
#Elapsed time:  4933.60 s
#------------------------------------------------------------------------------
#
#Response for player/18632. Successful:  <Response [200]>
#
#Total successful requests:  606
#Completed :  23.31 %
#Elapsed time:  4945.58 s
#------------------------------------------------------------------------------
#
#Response for player/38261. Successful:  <Response [200]>
#
#Total successful requests:  607
#Completed :  23.35 %
#Elapsed time:  4948.78 s
#------------------------------------------------------------------------------
#
#Response for player/25022. Successful:  <Response [200]>
#
#Total successful requests:  608
#Completed :  23.38 %
#Elapsed time:  4955.50 s
#------------------------------------------------------------------------------
#
#Response for player/23688. Successful:  <Response [200]>
#
#Total successful requests:  609
#Completed :  23.42 %
#Elapsed time:  4956.80 s
#------------------------------------------------------------------------------
#
#Response for player/55736. Successful:  <Response [200]>
#
#Total successful requests:  610
#Completed :  23.46 %
#Elapsed time:  4972.83 s
#------------------------------------------------------------------------------
#
#Response for player/6282. Successful:  <Response [200]>
#
#Total successful requests:  611
#Completed :  23.50 %
#Elapsed time:  4990.84 s
#------------------------------------------------------------------------------
#
#Response for player/319758. Successful:  <Response [200]>
#
#Total successful requests:  612
#Completed :  23.54 %
#Elapsed time:  4997.31 s
#------------------------------------------------------------------------------
#
#Response for player/51221. Successful:  <Response [200]>
#
#Total successful requests:  613
#Completed :  23.58 %
#Elapsed time:  5002.13 s
#------------------------------------------------------------------------------
#
#Response for player/4146. Successful:  <Response [200]>
#
#Total successful requests:  614
#Completed :  23.62 %
#Elapsed time:  5010.14 s
#------------------------------------------------------------------------------
#
#Response for player/407265. Successful:  <Response [200]>
#
#Total successful requests:  615
#Completed :  23.65 %
#Elapsed time:  5010.90 s
#------------------------------------------------------------------------------
#
#Response for player/671805. Successful:  <Response [200]>
#
#Total successful requests:  616
#Completed :  23.69 %
#Elapsed time:  5017.66 s
#------------------------------------------------------------------------------
#
#Response for player/414248. Successful:  <Response [200]>
#
#Total successful requests:  617
#Completed :  23.73 %
#Elapsed time:  5029.74 s
#------------------------------------------------------------------------------
#
#Response for player/48447. Successful:  <Response [200]>
#
#Total successful requests:  618
#Completed :  23.77 %
#Elapsed time:  5031.46 s
#------------------------------------------------------------------------------
#
#Response for player/30912. Successful:  <Response [200]>
#
#Total successful requests:  619
#Completed :  23.81 %
#Elapsed time:  5036.46 s
#------------------------------------------------------------------------------
#
#Response for player/43524. Successful:  <Response [200]>
#
#Total successful requests:  620
#Completed :  23.85 %
#Elapsed time:  5048.51 s
#------------------------------------------------------------------------------
#
#Response for player/33949. Successful:  <Response [200]>
#
#Total successful requests:  621
#Completed :  23.88 %
#Elapsed time:  5053.94 s
#------------------------------------------------------------------------------
#
#Response for player/36383. Successful:  <Response [200]>
#
#Total successful requests:  622
#Completed :  23.92 %
#Elapsed time:  5061.61 s
#------------------------------------------------------------------------------
#
#Response for player/307075. Successful:  <Response [200]>
#
#Total successful requests:  623
#Completed :  23.96 %
#Elapsed time:  5063.66 s
#------------------------------------------------------------------------------
#
#Response for player/269280. Successful:  <Response [200]>
#
#Total successful requests:  624
#Completed :  24.00 %
#Elapsed time:  5074.32 s
#------------------------------------------------------------------------------
#
#Response for player/25051. Successful:  <Response [200]>
#
#Total successful requests:  625
#Completed :  24.04 %
#Elapsed time:  5085.50 s
#------------------------------------------------------------------------------
#
#Response for player/55971. Successful:  <Response [200]>
#
#Total successful requests:  626
#Completed :  24.08 %
#Elapsed time:  5088.83 s
#------------------------------------------------------------------------------
#
#Response for player/55970. Successful:  <Response [200]>
#
#Total successful requests:  627
#Completed :  24.12 %
#Elapsed time:  5093.17 s
#------------------------------------------------------------------------------
#
#Response for player/55395. Successful:  <Response [200]>
#
#Total successful requests:  628
#Completed :  24.15 %
#Elapsed time:  5094.36 s
#------------------------------------------------------------------------------
#
#Response for player/414966. Successful:  <Response [200]>
#
#Total successful requests:  629
#Completed :  24.19 %
#Elapsed time:  5108.05 s
#------------------------------------------------------------------------------
#
#Response for player/36297. Successful:  <Response [200]>
#
#Total successful requests:  630
#Completed :  24.23 %
#Elapsed time:  5120.34 s
#------------------------------------------------------------------------------
#
#Response for player/50432. Successful:  <Response [200]>
#
#Total successful requests:  631
#Completed :  24.27 %
#Elapsed time:  5153.75 s
#------------------------------------------------------------------------------
#
#Response for player/290630. Successful:  <Response [200]>
#
#Total successful requests:  632
#Completed :  24.31 %
#Elapsed time:  5161.37 s
#------------------------------------------------------------------------------
#
#Response for player/540316. Successful:  <Response [200]>
#
#Total successful requests:  633
#Completed :  24.35 %
#Elapsed time:  5165.18 s
#------------------------------------------------------------------------------
#
#Response for player/35712. Successful:  <Response [200]>
#
#Total successful requests:  634
#Completed :  24.38 %
#Elapsed time:  5167.08 s
#------------------------------------------------------------------------------
#
#Response for player/6462. Successful:  <Response [200]>
#
#Total successful requests:  635
#Completed :  24.42 %
#Elapsed time:  5175.50 s
#------------------------------------------------------------------------------
#
#Response for player/55680. Successful:  <Response [200]>
#
#Total successful requests:  636
#Completed :  24.46 %
#Elapsed time:  5189.38 s
#------------------------------------------------------------------------------
#
#Response for player/7926. Successful:  <Response [200]>
#
#Total successful requests:  637
#Completed :  24.50 %
#Elapsed time:  5201.26 s
#------------------------------------------------------------------------------
#
#Response for player/24692. Successful:  <Response [200]>
#
#Total successful requests:  638
#Completed :  24.54 %
#Elapsed time:  5203.33 s
#------------------------------------------------------------------------------
#
#Response for player/6551. Successful:  <Response [200]>
#
#Total successful requests:  639
#Completed :  24.58 %
#Elapsed time:  5214.08 s
#------------------------------------------------------------------------------
#
#Response for player/25112. Successful:  <Response [200]>
#
#Total successful requests:  640
#Completed :  24.62 %
#Elapsed time:  5222.86 s
#------------------------------------------------------------------------------
#
#Response for player/362603. Successful:  <Response [200]>
#
#Total successful requests:  641
#Completed :  24.65 %
#Elapsed time:  5224.95 s
#------------------------------------------------------------------------------
#
#Response for player/326434. Successful:  <Response [200]>
#
#Total successful requests:  642
#Completed :  24.69 %
#Elapsed time:  5233.06 s
#------------------------------------------------------------------------------
#
#Response for player/18627. Successful:  <Response [200]>
#
#Total successful requests:  643
#Completed :  24.73 %
#Elapsed time:  5236.06 s
#------------------------------------------------------------------------------
#
#Response for player/47711. Successful:  <Response [200]>
#
#Total successful requests:  644
#Completed :  24.77 %
#Elapsed time:  5243.04 s
#------------------------------------------------------------------------------
#
#Response for player/33943. Successful:  <Response [200]>
#
#Total successful requests:  645
#Completed :  24.81 %
#Elapsed time:  5243.89 s
#------------------------------------------------------------------------------
#
#Response for player/19500. Successful:  <Response [200]>
#
#Total successful requests:  646
#Completed :  24.85 %
#Elapsed time:  5245.56 s
#------------------------------------------------------------------------------
#
#Response for player/418615. Successful:  <Response [200]>
#
#Total successful requests:  647
#Completed :  24.88 %
#Elapsed time:  5248.93 s
#------------------------------------------------------------------------------
#
#Response for player/268740. Successful:  <Response [200]>
#
#Total successful requests:  648
#Completed :  24.92 %
#Elapsed time:  5264.90 s
#------------------------------------------------------------------------------
#
#Response for player/269237. Successful:  <Response [200]>
#
#Total successful requests:  649
#Completed :  24.96 %
#Elapsed time:  5271.55 s
#------------------------------------------------------------------------------
#
#Response for player/233802. Successful:  <Response [200]>
#
#Total successful requests:  650
#Completed :  25.00 %
#Elapsed time:  5277.87 s
#------------------------------------------------------------------------------
#
#Response for player/36192. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  651
#Completed :  25.04 %
#Elapsed time:  5294.12 s
#------------------------------------------------------------------------------
#
#Response for player/352894. Successful:  <Response [200]>
#
#Total successful requests:  652
#Completed :  25.08 %
#Elapsed time:  5302.74 s
#------------------------------------------------------------------------------
#
#Response for player/51232. Successful:  <Response [200]>
#
#Total successful requests:  653
#Completed :  25.12 %
#Elapsed time:  5311.75 s
#------------------------------------------------------------------------------
#
#Response for player/55894. Successful:  <Response [200]>
#
#Total successful requests:  654
#Completed :  25.15 %
#Elapsed time:  5315.70 s
#------------------------------------------------------------------------------
#
#Response for player/711559. Successful:  <Response [200]>
#
#Total successful requests:  655
#Completed :  25.19 %
#Elapsed time:  5328.77 s
#------------------------------------------------------------------------------
#
#Response for player/55269. Successful:  <Response [200]>
#
#Total successful requests:  656
#Completed :  25.23 %
#Elapsed time:  5331.32 s
#------------------------------------------------------------------------------
#
#Response for player/25635. Successful:  <Response [200]>
#
#Total successful requests:  657
#Completed :  25.27 %
#Elapsed time:  5335.56 s
#------------------------------------------------------------------------------
#
#Response for player/550133. Successful:  <Response [200]>
#
#Total successful requests:  658
#Completed :  25.31 %
#Elapsed time:  5342.29 s
#------------------------------------------------------------------------------
#
#Response for player/55698. Successful:  <Response [200]>
#
#Total successful requests:  659
#Completed :  25.35 %
#Elapsed time:  5344.59 s
#------------------------------------------------------------------------------
#
#Response for player/51226. Successful:  <Response [200]>
#
#Total successful requests:  660
#Completed :  25.38 %
#Elapsed time:  5356.56 s
#------------------------------------------------------------------------------
#
#Response for player/55267. Successful:  <Response [200]>
#
#Total successful requests:  661
#Completed :  25.42 %
#Elapsed time:  5357.60 s
#------------------------------------------------------------------------------
#
#Response for player/9117. Successful:  <Response [200]>
#
#Total successful requests:  662
#Completed :  25.46 %
#Elapsed time:  5361.41 s
#------------------------------------------------------------------------------
#
#Response for player/55641. Successful:  <Response [200]>
#
#Total successful requests:  663
#Completed :  25.50 %
#Elapsed time:  5362.11 s
#------------------------------------------------------------------------------
#
#Response for player/337790. Successful:  <Response [200]>
#
#Total successful requests:  664
#Completed :  25.54 %
#Elapsed time:  5366.04 s
#------------------------------------------------------------------------------
#
#Response for player/4433. Successful:  <Response [200]>
#
#Total successful requests:  665
#Completed :  25.58 %
#Elapsed time:  5367.57 s
#------------------------------------------------------------------------------
#
#Response for player/48446. Successful:  <Response [200]>
#
#Total successful requests:  666
#Completed :  25.62 %
#Elapsed time:  5371.75 s
#------------------------------------------------------------------------------
#
#Response for player/30873. Successful:  <Response [200]>
#
#Total successful requests:  667
#Completed :  25.65 %
#Elapsed time:  5374.39 s
#------------------------------------------------------------------------------
#
#Response for player/24882. Successful:  <Response [200]>
#
#Total successful requests:  668
#Completed :  25.69 %
#Elapsed time:  5381.22 s
#------------------------------------------------------------------------------
#
#Response for player/49347. Successful:  <Response [200]>
#
#Total successful requests:  669
#Completed :  25.73 %
#Elapsed time:  5394.99 s
#------------------------------------------------------------------------------
#
#Response for player/41316. Successful:  <Response [200]>
#
#Total successful requests:  670
#Completed :  25.77 %
#Elapsed time:  5396.62 s
#------------------------------------------------------------------------------
#
#Response for player/43265. Successful:  <Response [200]>
#
#Total successful requests:  671
#Completed :  25.81 %
#Elapsed time:  5407.81 s
#------------------------------------------------------------------------------
#
#Response for player/23767. Successful:  <Response [200]>
#
#Total successful requests:  672
#Completed :  25.85 %
#Elapsed time:  5418.86 s
#------------------------------------------------------------------------------
#
#Response for player/533862. Successful:  <Response [200]>
#
#Total successful requests:  673
#Completed :  25.88 %
#Elapsed time:  5423.22 s
#------------------------------------------------------------------------------
#
#Response for player/348016. Successful:  <Response [200]>
#
#Total successful requests:  674
#Completed :  25.92 %
#Elapsed time:  5430.68 s
#------------------------------------------------------------------------------
#
#Response for player/274926. Successful:  <Response [200]>
#
#Total successful requests:  675
#Completed :  25.96 %
#Elapsed time:  5433.15 s
#------------------------------------------------------------------------------
#
#Response for player/42655. Successful:  <Response [200]>
#
#Total successful requests:  676
#Completed :  26.00 %
#Elapsed time:  5435.12 s
#------------------------------------------------------------------------------
#
#Response for player/439952. Successful:  <Response [200]>
#
#Total successful requests:  677
#Completed :  26.04 %
#Elapsed time:  5439.41 s
#------------------------------------------------------------------------------
#
#Response for player/49677. Successful:  <Response [200]>
#
#Total successful requests:  678
#Completed :  26.08 %
#Elapsed time:  5443.05 s
#------------------------------------------------------------------------------
#
#Response for player/24762. Successful:  <Response [200]>
#
#Total successful requests:  679
#Completed :  26.12 %
#Elapsed time:  5447.61 s
#------------------------------------------------------------------------------
#
#Response for player/457249. Successful:  <Response [200]>
#
#Total successful requests:  680
#Completed :  26.15 %
#Elapsed time:  5454.43 s
#------------------------------------------------------------------------------
#
#Response for player/387420. Successful:  <Response [200]>
#
#Total successful requests:  681
#Completed :  26.19 %
#Elapsed time:  5458.68 s
#------------------------------------------------------------------------------
#
#Response for player/52626. Successful:  <Response [200]>
#
#Total successful requests:  682
#Completed :  26.23 %
#Elapsed time:  5460.17 s
#------------------------------------------------------------------------------
#
#Response for player/13368. Successful:  <Response [200]>
#
#Total successful requests:  683
#Completed :  26.27 %
#Elapsed time:  5467.99 s
#------------------------------------------------------------------------------
#
#Response for player/55915. Successful:  <Response [200]>
#
#Total successful requests:  684
#Completed :  26.31 %
#Elapsed time:  5470.84 s
#------------------------------------------------------------------------------
#
#Response for player/42601. Successful:  <Response [200]>
#
#Total successful requests:  685
#Completed :  26.35 %
#Elapsed time:  5477.87 s
#------------------------------------------------------------------------------
#
#Response for player/25056. Successful:  <Response [200]>
#
#Total successful requests:  686
#Completed :  26.38 %
#Elapsed time:  5479.75 s
#------------------------------------------------------------------------------
#
#Response for player/55367. Successful:  <Response [200]>
#
#Total successful requests:  687
#Completed :  26.42 %
#Elapsed time:  5481.27 s
#------------------------------------------------------------------------------
#
#Response for player/8198. Successful:  <Response [200]>
#
#Total successful requests:  688
#Completed :  26.46 %
#Elapsed time:  5483.17 s
#------------------------------------------------------------------------------
#
#Response for player/23865. Successful:  <Response [200]>
#
#Total successful requests:  689
#Completed :  26.50 %
#Elapsed time:  5494.91 s
#------------------------------------------------------------------------------
#
#Response for player/6272. Successful:  <Response [200]>
#
#Total successful requests:  690
#Completed :  26.54 %
#Elapsed time:  5496.89 s
#------------------------------------------------------------------------------
#
#Response for player/19323. Successful:  <Response [200]>
#
#Total successful requests:  691
#Completed :  26.58 %
#Elapsed time:  5510.11 s
#------------------------------------------------------------------------------
#
#Response for player/56219. Successful:  <Response [200]>
#
#Total successful requests:  692
#Completed :  26.62 %
#Elapsed time:  5526.38 s
#------------------------------------------------------------------------------
#
#Response for player/16274. Successful:  <Response [200]>
#
#Total successful requests:  693
#Completed :  26.65 %
#Elapsed time:  5533.60 s
#------------------------------------------------------------------------------
#
#Response for player/30116. Successful:  <Response [200]>
#
#Total successful requests:  694
#Completed :  26.69 %
#Elapsed time:  5535.60 s
#------------------------------------------------------------------------------
#
#Response for player/48454. Successful:  <Response [200]>
#
#Total successful requests:  695
#Completed :  26.73 %
#Elapsed time:  5545.11 s
#------------------------------------------------------------------------------
#
#Response for player/51492. Successful:  <Response [200]>
#
#Total successful requests:  696
#Completed :  26.77 %
#Elapsed time:  5546.22 s
#------------------------------------------------------------------------------
#
#Response for player/232285. Successful:  <Response [200]>
#
#Total successful requests:  697
#Completed :  26.81 %
#Elapsed time:  5549.66 s
#------------------------------------------------------------------------------
#
#Response for player/414971. Successful:  <Response [200]>
#
#Total successful requests:  698
#Completed :  26.85 %
#Elapsed time:  5554.58 s
#------------------------------------------------------------------------------
#
#Response for player/47492. Successful:  <Response [200]>
#
#Total successful requests:  699
#Completed :  26.88 %
#Elapsed time:  5569.25 s
#------------------------------------------------------------------------------
#
#Response for player/4900. Successful:  <Response [200]>
#
#Total successful requests:  700
#Completed :  26.92 %
#Elapsed time:  5576.00 s
#------------------------------------------------------------------------------
#
#Response for player/230558. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  701
#Completed :  26.96 %
#Elapsed time:  5580.74 s
#------------------------------------------------------------------------------
#
#Response for player/30042. Successful:  <Response [200]>
#
#Total successful requests:  702
#Completed :  27.00 %
#Elapsed time:  5590.65 s
#------------------------------------------------------------------------------
#
#Response for player/52912. Successful:  <Response [200]>
#
#Total successful requests:  703
#Completed :  27.04 %
#Elapsed time:  5595.84 s
#------------------------------------------------------------------------------
#
#Response for player/56104. Successful:  <Response [200]>
#
#Total successful requests:  704
#Completed :  27.08 %
#Elapsed time:  5598.75 s
#------------------------------------------------------------------------------
#
#Response for player/4493. Successful:  <Response [200]>
#
#Total successful requests:  705
#Completed :  27.12 %
#Elapsed time:  5601.71 s
#------------------------------------------------------------------------------
#
#Response for player/24251. Successful:  <Response [200]>
#
#Total successful requests:  706
#Completed :  27.15 %
#Elapsed time:  5612.83 s
#------------------------------------------------------------------------------
#
#Response for player/15403. Successful:  <Response [200]>
#
#Total successful requests:  707
#Completed :  27.19 %
#Elapsed time:  5626.13 s
#------------------------------------------------------------------------------
#
#Response for player/55976. Successful:  <Response [200]>
#
#Total successful requests:  708
#Completed :  27.23 %
#Elapsed time:  5629.16 s
#------------------------------------------------------------------------------
#
#Response for player/24776. Successful:  <Response [200]>
#
#Total successful requests:  709
#Completed :  27.27 %
#Elapsed time:  5632.99 s
#------------------------------------------------------------------------------
#
#Response for player/9246. Successful:  <Response [200]>
#
#Total successful requests:  710
#Completed :  27.31 %
#Elapsed time:  5641.03 s
#------------------------------------------------------------------------------
#
#Response for player/51862. Successful:  <Response [200]>
#
#Total successful requests:  711
#Completed :  27.35 %
#Elapsed time:  5644.97 s
#------------------------------------------------------------------------------
#
#Response for player/290948. Successful:  <Response [200]>
#
#Total successful requests:  712
#Completed :  27.38 %
#Elapsed time:  5648.35 s
#------------------------------------------------------------------------------
#
#Response for player/524048. Successful:  <Response [200]>
#
#Total successful requests:  713
#Completed :  27.42 %
#Elapsed time:  5671.18 s
#------------------------------------------------------------------------------
#
#Response for player/440990. Successful:  <Response [200]>
#
#Total successful requests:  714
#Completed :  27.46 %
#Elapsed time:  5679.62 s
#------------------------------------------------------------------------------
#
#Response for player/43539. Successful:  <Response [200]>
#
#Total successful requests:  715
#Completed :  27.50 %
#Elapsed time:  5691.40 s
#------------------------------------------------------------------------------
#
#Response for player/43697. Successful:  <Response [200]>
#
#Total successful requests:  716
#Completed :  27.54 %
#Elapsed time:  5698.34 s
#------------------------------------------------------------------------------
#
#Response for player/10881. Successful:  <Response [200]>
#
#Total successful requests:  717
#Completed :  27.58 %
#Elapsed time:  5702.37 s
#------------------------------------------------------------------------------
#
#Response for player/39940. Successful:  <Response [200]>
#
#Total successful requests:  718
#Completed :  27.62 %
#Elapsed time:  5712.51 s
#------------------------------------------------------------------------------
#
#Response for player/50848. Successful:  <Response [200]>
#
#Total successful requests:  719
#Completed :  27.65 %
#Elapsed time:  5730.46 s
#------------------------------------------------------------------------------
#
#Response for player/422108. Successful:  <Response [200]>
#
#Total successful requests:  720
#Completed :  27.69 %
#Elapsed time:  5745.28 s
#------------------------------------------------------------------------------
#
#Response for player/51050. Successful:  <Response [200]>
#
#Total successful requests:  721
#Completed :  27.73 %
#Elapsed time:  5757.81 s
#------------------------------------------------------------------------------
#
#Response for player/494230. Successful:  <Response [200]>
#
#Total successful requests:  722
#Completed :  27.77 %
#Elapsed time:  5760.04 s
#------------------------------------------------------------------------------
#
#Response for player/420427. Successful:  <Response [200]>
#
#Total successful requests:  723
#Completed :  27.81 %
#Elapsed time:  5761.90 s
#------------------------------------------------------------------------------
#
#Response for player/30018. Successful:  <Response [200]>
#
#Total successful requests:  724
#Completed :  27.85 %
#Elapsed time:  5769.83 s
#------------------------------------------------------------------------------
#
#Response for player/237095. Successful:  <Response [200]>
#
#Total successful requests:  725
#Completed :  27.88 %
#Elapsed time:  5792.53 s
#------------------------------------------------------------------------------
#
#Response for player/36611. Successful:  <Response [200]>
#
#Total successful requests:  726
#Completed :  27.92 %
#Elapsed time:  5795.04 s
#------------------------------------------------------------------------------
#
#Response for player/18256. Successful:  <Response [200]>
#
#Total successful requests:  727
#Completed :  27.96 %
#Elapsed time:  5798.05 s
#------------------------------------------------------------------------------
#
#Response for player/36314. Successful:  <Response [200]>
#
#Total successful requests:  728
#Completed :  28.00 %
#Elapsed time:  5798.84 s
#------------------------------------------------------------------------------
#
#Response for player/5593. Successful:  <Response [200]>
#
#Total successful requests:  729
#Completed :  28.04 %
#Elapsed time:  5807.20 s
#------------------------------------------------------------------------------
#
#Response for player/23704. Successful:  <Response [200]>
#
#Total successful requests:  730
#Completed :  28.08 %
#Elapsed time:  5812.22 s
#------------------------------------------------------------------------------
#
#Response for player/56176. Successful:  <Response [200]>
#
#Total successful requests:  731
#Completed :  28.12 %
#Elapsed time:  5815.60 s
#------------------------------------------------------------------------------
#
#Response for player/212756. Successful:  <Response [200]>
#
#Total successful requests:  732
#Completed :  28.15 %
#Elapsed time:  5820.38 s
#------------------------------------------------------------------------------
#
#Response for player/51786. Successful:  <Response [200]>
#
#Total successful requests:  733
#Completed :  28.19 %
#Elapsed time:  5824.66 s
#------------------------------------------------------------------------------
#
#Response for player/55991. Successful:  <Response [200]>
#
#Total successful requests:  734
#Completed :  28.23 %
#Elapsed time:  5833.93 s
#------------------------------------------------------------------------------
#
#Response for player/23755. Successful:  <Response [200]>
#
#Total successful requests:  735
#Completed :  28.27 %
#Elapsed time:  5842.41 s
#------------------------------------------------------------------------------
#
#Response for player/281653. Successful:  <Response [200]>
#
#Total successful requests:  736
#Completed :  28.31 %
#Elapsed time:  5845.64 s
#------------------------------------------------------------------------------
#
#Response for player/39010. Successful:  <Response [200]>
#
#Total successful requests:  737
#Completed :  28.35 %
#Elapsed time:  5847.67 s
#------------------------------------------------------------------------------
#
#Response for player/23803. Successful:  <Response [200]>
#
#Total successful requests:  738
#Completed :  28.38 %
#Elapsed time:  5860.57 s
#------------------------------------------------------------------------------
#
#Response for player/10653. Successful:  <Response [200]>
#
#Total successful requests:  739
#Completed :  28.42 %
#Elapsed time:  5879.89 s
#------------------------------------------------------------------------------
#
#Response for player/437316. Successful:  <Response [200]>
#
#Total successful requests:  740
#Completed :  28.46 %
#Elapsed time:  5883.95 s
#------------------------------------------------------------------------------
#
#Response for player/23523. Successful:  <Response [200]>
#
#Total successful requests:  741
#Completed :  28.50 %
#Elapsed time:  5895.14 s
#------------------------------------------------------------------------------
#
#Response for player/55663. Successful:  <Response [200]>
#
#Total successful requests:  742
#Completed :  28.54 %
#Elapsed time:  5907.18 s
#------------------------------------------------------------------------------
#
#Response for player/42699. Successful:  <Response [200]>
#
#Total successful requests:  743
#Completed :  28.58 %
#Elapsed time:  5910.04 s
#------------------------------------------------------------------------------
#
#Response for player/47215. Successful:  <Response [200]>
#
#Total successful requests:  744
#Completed :  28.62 %
#Elapsed time:  5915.31 s
#------------------------------------------------------------------------------
#
#Response for player/24974. Successful:  <Response [200]>
#
#Total successful requests:  745
#Completed :  28.65 %
#Elapsed time:  5920.33 s
#------------------------------------------------------------------------------
#
#Response for player/232491. Successful:  <Response [200]>
#
#Total successful requests:  746
#Completed :  28.69 %
#Elapsed time:  5922.81 s
#------------------------------------------------------------------------------
#
#Response for player/53216. Successful:  <Response [200]>
#
#Total successful requests:  747
#Completed :  28.73 %
#Elapsed time:  5928.07 s
#------------------------------------------------------------------------------
#
#Response for player/6547. Successful:  <Response [200]>
#
#Total successful requests:  748
#Completed :  28.77 %
#Elapsed time:  5934.70 s
#------------------------------------------------------------------------------
#
#Response for player/9254. Successful:  <Response [200]>
#
#Total successful requests:  749
#Completed :  28.81 %
#Elapsed time:  5947.01 s
#------------------------------------------------------------------------------
#
#Response for player/55737. Successful:  <Response [200]>
#
#Total successful requests:  750
#Completed :  28.85 %
#Elapsed time:  5950.59 s
#------------------------------------------------------------------------------
#
#Response for player/348054. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  751
#Completed :  28.88 %
#Elapsed time:  5964.26 s
#------------------------------------------------------------------------------
#
#Response for player/40088. Successful:  <Response [200]>
#
#Total successful requests:  752
#Completed :  28.92 %
#Elapsed time:  5969.51 s
#------------------------------------------------------------------------------
#
#Response for player/52430. Successful:  <Response [200]>
#
#Total successful requests:  753
#Completed :  28.96 %
#Elapsed time:  5980.15 s
#------------------------------------------------------------------------------
#
#Response for player/41324. Successful:  <Response [200]>
#
#Total successful requests:  754
#Completed :  29.00 %
#Elapsed time:  5990.94 s
#------------------------------------------------------------------------------
#
#Response for player/22498. Successful:  <Response [200]>
#
#Total successful requests:  755
#Completed :  29.04 %
#Elapsed time:  5995.46 s
#------------------------------------------------------------------------------
#
#Response for player/387435. Successful:  <Response [200]>
#
#Total successful requests:  756
#Completed :  29.08 %
#Elapsed time:  6021.07 s
#------------------------------------------------------------------------------
#
#Response for player/51797. Successful:  <Response [200]>
#
#Total successful requests:  757
#Completed :  29.12 %
#Elapsed time:  6047.38 s
#------------------------------------------------------------------------------
#
#Response for player/37235. Successful:  <Response [200]>
#
#Total successful requests:  758
#Completed :  29.15 %
#Elapsed time:  6055.28 s
#------------------------------------------------------------------------------
#
#Response for player/27641. Successful:  <Response [200]>
#
#Total successful requests:  759
#Completed :  29.19 %
#Elapsed time:  6062.16 s
#------------------------------------------------------------------------------
#
#Response for player/14246. Successful:  <Response [200]>
#
#Total successful requests:  760
#Completed :  29.23 %
#Elapsed time:  6063.44 s
#------------------------------------------------------------------------------
#
#Response for player/56064. Successful:  <Response [200]>
#
#Total successful requests:  761
#Completed :  29.27 %
#Elapsed time:  6064.57 s
#------------------------------------------------------------------------------
#
#Response for player/703323. Successful:  <Response [200]>
#
#Total successful requests:  762
#Completed :  29.31 %
#Elapsed time:  6082.26 s
#------------------------------------------------------------------------------
#
#Response for player/44070. Successful:  <Response [200]>
#
#Total successful requests:  763
#Completed :  29.35 %
#Elapsed time:  6083.29 s
#------------------------------------------------------------------------------
#
#Response for player/596375. Successful:  <Response [200]>
#
#Total successful requests:  764
#Completed :  29.38 %
#Elapsed time:  6084.52 s
#------------------------------------------------------------------------------
#
#Response for player/44098. Successful:  <Response [200]>
#
#Total successful requests:  765
#Completed :  29.42 %
#Elapsed time:  6092.39 s
#------------------------------------------------------------------------------
#
#Response for player/19346. Successful:  <Response [200]>
#
#Total successful requests:  766
#Completed :  29.46 %
#Elapsed time:  6098.54 s
#------------------------------------------------------------------------------
#
#Response for player/51220. Successful:  <Response [200]>
#
#Total successful requests:  767
#Completed :  29.50 %
#Elapsed time:  6105.90 s
#------------------------------------------------------------------------------
#
#Response for player/232438. Successful:  <Response [200]>
#
#Total successful requests:  768
#Completed :  29.54 %
#Elapsed time:  6106.62 s
#------------------------------------------------------------------------------
#
#Response for player/18023. Successful:  <Response [200]>
#
#Total successful requests:  769
#Completed :  29.58 %
#Elapsed time:  6108.97 s
#------------------------------------------------------------------------------
#
#Response for player/43701. Successful:  <Response [200]>
#
#Total successful requests:  770
#Completed :  29.62 %
#Elapsed time:  6110.73 s
#------------------------------------------------------------------------------
#
#Response for player/44486. Successful:  <Response [200]>
#
#Total successful requests:  771
#Completed :  29.65 %
#Elapsed time:  6126.87 s
#------------------------------------------------------------------------------
#
#Response for player/55700. Successful:  <Response [200]>
#
#Total successful requests:  772
#Completed :  29.69 %
#Elapsed time:  6128.28 s
#------------------------------------------------------------------------------
#
#Response for player/38620. Successful:  <Response [200]>
#
#Total successful requests:  773
#Completed :  29.73 %
#Elapsed time:  6133.62 s
#------------------------------------------------------------------------------
#
#Response for player/52441. Successful:  <Response [200]>
#
#Total successful requests:  774
#Completed :  29.77 %
#Elapsed time:  6136.91 s
#------------------------------------------------------------------------------
#
#Response for player/233712. Successful:  <Response [200]>
#
#Total successful requests:  775
#Completed :  29.81 %
#Elapsed time:  6138.37 s
#------------------------------------------------------------------------------
#
#Response for player/922943. Successful:  <Response [200]>
#
#Total successful requests:  776
#Completed :  29.85 %
#Elapsed time:  6141.57 s
#------------------------------------------------------------------------------
#
#Response for player/12454. Successful:  <Response [200]>
#
#Total successful requests:  777
#Completed :  29.88 %
#Elapsed time:  6153.90 s
#------------------------------------------------------------------------------
#
#Response for player/36326. Successful:  <Response [200]>
#
#Total successful requests:  778
#Completed :  29.92 %
#Elapsed time:  6155.21 s
#------------------------------------------------------------------------------
#
#Response for player/30732. Successful:  <Response [200]>
#
#Total successful requests:  779
#Completed :  29.96 %
#Elapsed time:  6156.17 s
#------------------------------------------------------------------------------
#
#Response for player/260036. Successful:  <Response [200]>
#
#Total successful requests:  780
#Completed :  30.00 %
#Elapsed time:  6157.60 s
#------------------------------------------------------------------------------
#
#Response for player/52343. Successful:  <Response [200]>
#
#Total successful requests:  781
#Completed :  30.04 %
#Elapsed time:  6175.46 s
#------------------------------------------------------------------------------
#
#Response for player/629063. Successful:  <Response [200]>
#
#Total successful requests:  782
#Completed :  30.08 %
#Elapsed time:  6182.29 s
#------------------------------------------------------------------------------
#
#Response for player/19364. Successful:  <Response [200]>
#
#Total successful requests:  783
#Completed :  30.12 %
#Elapsed time:  6194.88 s
#------------------------------------------------------------------------------
#
#Response for player/32179. Successful:  <Response [200]>
#
#Total successful requests:  784
#Completed :  30.15 %
#Elapsed time:  6201.33 s
#------------------------------------------------------------------------------
#
#Response for player/56107. Successful:  <Response [200]>
#
#Total successful requests:  785
#Completed :  30.19 %
#Elapsed time:  6212.98 s
#------------------------------------------------------------------------------
#
#Response for player/273439. Successful:  <Response [200]>
#
#Total successful requests:  786
#Completed :  30.23 %
#Elapsed time:  6219.19 s
#------------------------------------------------------------------------------
#
#Response for player/5392. Successful:  <Response [200]>
#
#Total successful requests:  787
#Completed :  30.27 %
#Elapsed time:  6224.19 s
#------------------------------------------------------------------------------
#
#Response for player/51246. Successful:  <Response [200]>
#
#Total successful requests:  788
#Completed :  30.31 %
#Elapsed time:  6231.00 s
#------------------------------------------------------------------------------
#
#Response for player/55324. Successful:  <Response [200]>
#
#Total successful requests:  789
#Completed :  30.35 %
#Elapsed time:  6248.10 s
#------------------------------------------------------------------------------
#
#Response for player/37257. Successful:  <Response [200]>
#
#Total successful requests:  790
#Completed :  30.38 %
#Elapsed time:  6251.22 s
#------------------------------------------------------------------------------
#
#Response for player/35565. Successful:  <Response [200]>
#
#Total successful requests:  791
#Completed :  30.42 %
#Elapsed time:  6268.87 s
#------------------------------------------------------------------------------
#
#Response for player/16318. Successful:  <Response [200]>
#
#Total successful requests:  792
#Completed :  30.46 %
#Elapsed time:  6275.66 s
#------------------------------------------------------------------------------
#
#Response for player/16899. Successful:  <Response [200]>
#
#Total successful requests:  793
#Completed :  30.50 %
#Elapsed time:  6289.55 s
#------------------------------------------------------------------------------
#
#Response for player/25087. Successful:  <Response [200]>
#
#Total successful requests:  794
#Completed :  30.54 %
#Elapsed time:  6292.70 s
#------------------------------------------------------------------------------
#
#Response for player/52622. Successful:  <Response [200]>
#
#Total successful requests:  795
#Completed :  30.58 %
#Elapsed time:  6293.57 s
#------------------------------------------------------------------------------
#
#Response for player/24969. Successful:  <Response [200]>
#
#Total successful requests:  796
#Completed :  30.62 %
#Elapsed time:  6307.24 s
#------------------------------------------------------------------------------
#
#Response for player/574178. Successful:  <Response [200]>
#
#Total successful requests:  797
#Completed :  30.65 %
#Elapsed time:  6314.98 s
#------------------------------------------------------------------------------
#
#Response for player/52063. Successful:  <Response [200]>
#
#Total successful requests:  798
#Completed :  30.69 %
#Elapsed time:  6316.64 s
#------------------------------------------------------------------------------
#
#Response for player/50438. Successful:  <Response [200]>
#
#Total successful requests:  799
#Completed :  30.73 %
#Elapsed time:  6320.85 s
#------------------------------------------------------------------------------
#
#Response for player/52290. Successful:  <Response [200]>
#
#Total successful requests:  800
#Completed :  30.77 %
#Elapsed time:  6327.06 s
#------------------------------------------------------------------------------
#
#Response for page 5 Successful:  <Response [200]> 	=>
#

#list of players:  200
#Response for player/230553. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  801
#Completed :  30.81 %
#Elapsed time:  6481.15 s
#------------------------------------------------------------------------------
#
#Response for player/34078. Successful:  <Response [200]>
#
#Total successful requests:  802
#Completed :  30.85 %
#Elapsed time:  6492.02 s
#------------------------------------------------------------------------------
#
#Response for player/311592. Successful:  <Response [200]>
#
#Total successful requests:  803
#Completed :  30.88 %
#Elapsed time:  6495.12 s
#------------------------------------------------------------------------------
#
#Response for player/308251. Successful:  <Response [200]>
#
#Total successful requests:  804
#Completed :  30.92 %
#Elapsed time:  6506.80 s
#------------------------------------------------------------------------------
#
#Response for player/348024. Successful:  <Response [200]>
#
#Total successful requests:  805
#Completed :  30.96 %
#Elapsed time:  6527.49 s
#------------------------------------------------------------------------------
#
#Response for player/53191. Successful:  <Response [200]>
#
#Total successful requests:  806
#Completed :  31.00 %
#Elapsed time:  6529.22 s
#------------------------------------------------------------------------------
#
#Response for player/24729. Successful:  <Response [200]>
#
#Total successful requests:  807
#Completed :  31.04 %
#Elapsed time:  6552.54 s
#------------------------------------------------------------------------------
#
#Response for player/56031. Successful:  <Response [200]>
#
#Total successful requests:  808
#Completed :  31.08 %
#Elapsed time:  6555.89 s
#------------------------------------------------------------------------------
#
#Response for player/8608. Successful:  <Response [200]>
#
#Total successful requests:  809
#Completed :  31.12 %
#Elapsed time:  6574.05 s
#------------------------------------------------------------------------------
#
#Response for player/4864. Successful:  <Response [200]>
#
#Total successful requests:  810
#Completed :  31.15 %
#Elapsed time:  6584.13 s
#------------------------------------------------------------------------------
#
#Response for player/277911. Successful:  <Response [200]>
#
#Total successful requests:  811
#Completed :  31.19 %
#Elapsed time:  6590.17 s
#------------------------------------------------------------------------------
#
#Response for player/297628. Successful:  <Response [200]>
#
#Total successful requests:  812
#Completed :  31.23 %
#Elapsed time:  6595.41 s
#------------------------------------------------------------------------------
#
#Response for player/228622. Successful:  <Response [200]>
#
#Total successful requests:  813
#Completed :  31.27 %
#Elapsed time:  6598.77 s
#------------------------------------------------------------------------------
#
#Response for player/288211. Successful:  <Response [200]>
#
#Total successful requests:  814
#Completed :  31.31 %
#Elapsed time:  6600.69 s
#------------------------------------------------------------------------------
#
#Response for player/44024. Successful:  <Response [200]>
#
#Total successful requests:  815
#Completed :  31.35 %
#Elapsed time:  6603.04 s
#------------------------------------------------------------------------------
#
#Response for player/55944. Successful:  <Response [200]>
#
#Total successful requests:  816
#Completed :  31.38 %
#Elapsed time:  6605.98 s
#------------------------------------------------------------------------------
#
#Response for player/26325. Successful:  <Response [200]>
#
#Total successful requests:  817
#Completed :  31.42 %
#Elapsed time:  6608.04 s
#------------------------------------------------------------------------------
#
#Response for player/28754. Successful:  <Response [200]>
#
#Total successful requests:  818
#Completed :  31.46 %
#Elapsed time:  6612.02 s
#------------------------------------------------------------------------------
#
#Response for player/13463. Successful:  <Response [200]>
#
#Total successful requests:  819
#Completed :  31.50 %
#Elapsed time:  6616.23 s
#------------------------------------------------------------------------------
#
#Response for player/46538. Successful:  <Response [200]>
#
#Total successful requests:  820
#Completed :  31.54 %
#Elapsed time:  6619.26 s
#------------------------------------------------------------------------------
#
#Response for player/38970. Successful:  <Response [200]>
#
#Total successful requests:  821
#Completed :  31.58 %
#Elapsed time:  6629.49 s
#------------------------------------------------------------------------------
#
#Response for player/227772. Successful:  <Response [200]>
#
#Total successful requests:  822
#Completed :  31.62 %
#Elapsed time:  6637.61 s
#------------------------------------------------------------------------------
#
#Response for player/56154. Successful:  <Response [200]>
#
#Total successful requests:  823
#Completed :  31.65 %
#Elapsed time:  6656.21 s
#------------------------------------------------------------------------------
#
#Response for player/420402. Successful:  <Response [200]>
#
#Total successful requests:  824
#Completed :  31.69 %
#Elapsed time:  6660.07 s
#------------------------------------------------------------------------------
#
#Response for player/11870. Successful:  <Response [200]>
#
#Total successful requests:  825
#Completed :  31.73 %
#Elapsed time:  6665.94 s
#------------------------------------------------------------------------------
#
#Response for player/23860. Successful:  <Response [200]>
#
#Total successful requests:  826
#Completed :  31.77 %
#Elapsed time:  6668.17 s
#------------------------------------------------------------------------------
#
#Response for player/447458. Successful:  <Response [200]>
#
#Total successful requests:  827
#Completed :  31.81 %
#Elapsed time:  6668.95 s
#------------------------------------------------------------------------------
#
#Response for player/638713. Successful:  <Response [200]>
#
#Total successful requests:  828
#Completed :  31.85 %
#Elapsed time:  6670.92 s
#------------------------------------------------------------------------------
#
#Response for player/42066. Successful:  <Response [200]>
#
#Total successful requests:  829
#Completed :  31.88 %
#Elapsed time:  6674.61 s
#------------------------------------------------------------------------------
#
#Response for player/401540. Successful:  <Response [200]>
#
#Total successful requests:  830
#Completed :  31.92 %
#Elapsed time:  6681.06 s
#------------------------------------------------------------------------------
#
#Response for player/38735. Successful:  <Response [200]>
#
#Total successful requests:  831
#Completed :  31.96 %
#Elapsed time:  6685.46 s
#------------------------------------------------------------------------------
#
#Response for player/50802. Successful:  <Response [200]>
#
#Total successful requests:  832
#Completed :  32.00 %
#Elapsed time:  6711.73 s
#------------------------------------------------------------------------------
#
#Response for player/28090. Successful:  <Response [200]>
#
#Total successful requests:  833
#Completed :  32.04 %
#Elapsed time:  6713.31 s
#------------------------------------------------------------------------------
#
#Response for player/5124. Successful:  <Response [200]>
#
#Total successful requests:  834
#Completed :  32.08 %
#Elapsed time:  6717.76 s
#------------------------------------------------------------------------------
#
#Response for player/417381. Successful:  <Response [200]>
#
#Total successful requests:  835
#Completed :  32.12 %
#Elapsed time:  6719.45 s
#------------------------------------------------------------------------------
#
#Response for player/210279. Successful:  <Response [200]>
#
#Total successful requests:  836
#Completed :  32.15 %
#Elapsed time:  6720.92 s
#------------------------------------------------------------------------------
#
#Response for player/50247. Successful:  <Response [200]>
#
#Total successful requests:  837
#Completed :  32.19 %
#Elapsed time:  6723.39 s
#------------------------------------------------------------------------------
#
#Response for player/55280. Successful:  <Response [200]>
#
#Total successful requests:  838
#Completed :  32.23 %
#Elapsed time:  6731.50 s
#------------------------------------------------------------------------------
#
#Response for player/23759. Successful:  <Response [200]>
#
#Total successful requests:  839
#Completed :  32.27 %
#Elapsed time:  6743.38 s
#------------------------------------------------------------------------------
#
#Response for player/37731. Successful:  <Response [200]>
#
#Total successful requests:  840
#Completed :  32.31 %
#Elapsed time:  6745.27 s
#------------------------------------------------------------------------------
#
#Response for player/254114. Successful:  <Response [200]>
#
#Total successful requests:  841
#Completed :  32.35 %
#Elapsed time:  6747.67 s
#------------------------------------------------------------------------------
#
#Response for player/436757. Successful:  <Response [200]>
#
#Total successful requests:  842
#Completed :  32.38 %
#Elapsed time:  6750.18 s
#------------------------------------------------------------------------------
#
#Response for player/292152. Successful:  <Response [200]>
#
#Total successful requests:  843
#Completed :  32.42 %
#Elapsed time:  6755.55 s
#------------------------------------------------------------------------------
#
#Response for player/37698. Successful:  <Response [200]>
#
#Total successful requests:  844
#Completed :  32.46 %
#Elapsed time:  6769.73 s
#------------------------------------------------------------------------------
#
#Response for player/19316. Successful:  <Response [200]>
#
#Total successful requests:  845
#Completed :  32.50 %
#Elapsed time:  6780.88 s
#------------------------------------------------------------------------------
#
#Response for player/10633. Successful:  <Response [200]>
#
#Total successful requests:  846
#Completed :  32.54 %
#Elapsed time:  6783.84 s
#------------------------------------------------------------------------------
#
#Response for player/49552. Successful:  <Response [200]>
#
#Total successful requests:  847
#Completed :  32.58 %
#Elapsed time:  6786.61 s
#------------------------------------------------------------------------------
#
#Response for player/348026. Successful:  <Response [200]>
#
#Total successful requests:  848
#Completed :  32.62 %
#Elapsed time:  6787.48 s
#------------------------------------------------------------------------------
#
#Response for player/38113. Successful:  <Response [200]>
#
#Total successful requests:  849
#Completed :  32.65 %
#Elapsed time:  6788.46 s
#------------------------------------------------------------------------------
#
#Response for player/38249. Successful:  <Response [200]>
#
#Total successful requests:  850
#Completed :  32.69 %
#Elapsed time:  6790.21 s
#------------------------------------------------------------------------------
#
#Response for player/38707. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  851
#Completed :  32.73 %
#Elapsed time:  6803.64 s
#------------------------------------------------------------------------------
#
#Response for player/24725. Successful:  <Response [200]>
#
#Total successful requests:  852
#Completed :  32.77 %
#Elapsed time:  6805.15 s
#------------------------------------------------------------------------------
#
#Response for player/7989. Successful:  <Response [200]>
#
#Total successful requests:  853
#Completed :  32.81 %
#Elapsed time:  6810.41 s
#------------------------------------------------------------------------------
#
#Response for player/16932. Successful:  <Response [200]>
#
#Total successful requests:  854
#Completed :  32.85 %
#Elapsed time:  6812.97 s
#------------------------------------------------------------------------------
#
#Response for player/12450. Successful:  <Response [200]>
#
#Total successful requests:  855
#Completed :  32.88 %
#Elapsed time:  6823.11 s
#------------------------------------------------------------------------------
#
#Response for player/216920. Successful:  <Response [200]>
#
#Total successful requests:  856
#Completed :  32.92 %
#Elapsed time:  6825.92 s
#------------------------------------------------------------------------------
#
#Response for player/32231. Successful:  <Response [200]>
#
#Total successful requests:  857
#Completed :  32.96 %
#Elapsed time:  6834.02 s
#------------------------------------------------------------------------------
#
#Response for player/11931. Successful:  <Response [200]>
#
#Total successful requests:  858
#Completed :  33.00 %
#Elapsed time:  6838.26 s
#------------------------------------------------------------------------------
#
#Response for player/40378. Successful:  <Response [200]>
#
#Total successful requests:  859
#Completed :  33.04 %
#Elapsed time:  6842.08 s
#------------------------------------------------------------------------------
#
#Response for player/4951. Successful:  <Response [200]>
#
#Total successful requests:  860
#Completed :  33.08 %
#Elapsed time:  6844.75 s
#------------------------------------------------------------------------------
#
#Response for player/295644. Successful:  <Response [200]>
#
#Total successful requests:  861
#Completed :  33.12 %
#Elapsed time:  6846.32 s
#------------------------------------------------------------------------------
#
#Response for player/6295. Successful:  <Response [200]>
#
#Total successful requests:  862
#Completed :  33.15 %
#Elapsed time:  6866.36 s
#------------------------------------------------------------------------------
#
#Response for player/25123. Successful:  <Response [200]>
#
#Total successful requests:  863
#Completed :  33.19 %
#Elapsed time:  6884.29 s
#------------------------------------------------------------------------------
#
#Response for player/25613. Successful:  <Response [200]>
#
#Total successful requests:  864
#Completed :  33.23 %
#Elapsed time:  6889.12 s
#------------------------------------------------------------------------------
#
#Response for player/48835. Successful:  <Response [200]>
#
#Total successful requests:  865
#Completed :  33.27 %
#Elapsed time:  6893.30 s
#------------------------------------------------------------------------------
#
#Response for player/51876. Successful:  <Response [200]>
#
#Total successful requests:  866
#Completed :  33.31 %
#Elapsed time:  6901.66 s
#------------------------------------------------------------------------------
#
#Response for player/55705. Successful:  <Response [200]>
#
#Total successful requests:  867
#Completed :  33.35 %
#Elapsed time:  6903.33 s
#------------------------------------------------------------------------------
#
#Response for player/55235. Successful:  <Response [200]>
#
#Total successful requests:  868
#Completed :  33.38 %
#Elapsed time:  6907.53 s
#------------------------------------------------------------------------------
#
#Response for player/248920. Successful:  <Response [200]>
#
#Total successful requests:  869
#Completed :  33.42 %
#Elapsed time:  6919.05 s
#------------------------------------------------------------------------------
#
#Response for player/681305. Successful:  <Response [200]>
#
#Total successful requests:  870
#Completed :  33.46 %
#Elapsed time:  6919.90 s
#------------------------------------------------------------------------------
#
#Response for player/19276. Successful:  <Response [200]>
#
#Total successful requests:  871
#Completed :  33.50 %
#Elapsed time:  6921.29 s
#------------------------------------------------------------------------------
#
#Response for player/55878. Successful:  <Response [200]>
#
#Total successful requests:  872
#Completed :  33.54 %
#Elapsed time:  6929.98 s
#------------------------------------------------------------------------------
#
#Response for player/37248. Successful:  <Response [200]>
#
#Total successful requests:  873
#Completed :  33.58 %
#Elapsed time:  6931.17 s
#------------------------------------------------------------------------------
#
#Response for player/541224. Successful:  <Response [200]>
#
#Total successful requests:  874
#Completed :  33.62 %
#Elapsed time:  6938.79 s
#------------------------------------------------------------------------------
#
#Response for player/41140. Successful:  <Response [200]>
#
#Total successful requests:  875
#Completed :  33.65 %
#Elapsed time:  6955.13 s
#------------------------------------------------------------------------------
#
#Response for player/23811. Successful:  <Response [200]>
#
#Total successful requests:  876
#Completed :  33.69 %
#Elapsed time:  6972.58 s
#------------------------------------------------------------------------------
#
#Response for player/10870. Successful:  <Response [200]>
#
#Total successful requests:  877
#Completed :  33.73 %
#Elapsed time:  6979.52 s
#------------------------------------------------------------------------------
#
#Response for player/25967. Successful:  <Response [200]>
#
#Total successful requests:  878
#Completed :  33.77 %
#Elapsed time:  6986.73 s
#------------------------------------------------------------------------------
#
#Response for player/40591. Successful:  <Response [200]>
#
#Total successful requests:  879
#Completed :  33.81 %
#Elapsed time:  7016.36 s
#------------------------------------------------------------------------------
#
#Response for player/391832. Successful:  <Response [200]>
#
#Total successful requests:  880
#Completed :  33.85 %
#Elapsed time:  7017.37 s
#------------------------------------------------------------------------------
#
#Response for player/17185. Successful:  <Response [200]>
#
#Total successful requests:  881
#Completed :  33.88 %
#Elapsed time:  7020.81 s
#------------------------------------------------------------------------------
#
#Response for player/245490. Successful:  <Response [200]>
#
#Total successful requests:  882
#Completed :  33.92 %
#Elapsed time:  7022.67 s
#------------------------------------------------------------------------------
#
#Response for player/52817. Successful:  <Response [200]>
#
#Total successful requests:  883
#Completed :  33.96 %
#Elapsed time:  7024.26 s
#------------------------------------------------------------------------------
#
#Response for player/27223. Successful:  <Response [200]>
#
#Total successful requests:  884
#Completed :  34.00 %
#Elapsed time:  7031.02 s
#------------------------------------------------------------------------------
#
#Response for player/4561. Successful:  <Response [200]>
#
#Total successful requests:  885
#Completed :  34.04 %
#Elapsed time:  7053.02 s
#------------------------------------------------------------------------------
#
#Response for player/49364. Successful:  <Response [200]>
#
#Total successful requests:  886
#Completed :  34.08 %
#Elapsed time:  7060.85 s
#------------------------------------------------------------------------------
#
#Response for player/51660. Successful:  <Response [200]>
#
#Total successful requests:  887
#Completed :  34.12 %
#Elapsed time:  7064.08 s
#------------------------------------------------------------------------------
#
#Response for player/37095. Successful:  <Response [200]>
#
#Total successful requests:  888
#Completed :  34.15 %
#Elapsed time:  7075.48 s
#------------------------------------------------------------------------------
#
#Response for player/24699. Successful:  <Response [200]>
#
#Total successful requests:  889
#Completed :  34.19 %
#Elapsed time:  7082.41 s
#------------------------------------------------------------------------------
#
#Response for player/414821. Successful:  <Response [200]>
#
#Total successful requests:  890
#Completed :  34.23 %
#Elapsed time:  7094.51 s
#------------------------------------------------------------------------------
#
#Response for player/51651. Successful:  <Response [200]>
#
#Total successful requests:  891
#Completed :  34.27 %
#Elapsed time:  7096.09 s
#------------------------------------------------------------------------------
#
#Response for player/5656. Successful:  <Response [200]>
#
#Total successful requests:  892
#Completed :  34.31 %
#Elapsed time:  7098.83 s
#------------------------------------------------------------------------------
#
#Response for player/259413. Successful:  <Response [200]>
#
#Total successful requests:  893
#Completed :  34.35 %
#Elapsed time:  7105.02 s
#------------------------------------------------------------------------------
#
#Response for player/296597. Successful:  <Response [200]>
#
#Total successful requests:  894
#Completed :  34.38 %
#Elapsed time:  7106.08 s
#------------------------------------------------------------------------------
#
#Response for player/6056. Successful:  <Response [200]>
#
#Total successful requests:  895
#Completed :  34.42 %
#Elapsed time:  7111.01 s
#------------------------------------------------------------------------------
#
#Response for player/414970. Successful:  <Response [200]>
#
#Total successful requests:  896
#Completed :  34.46 %
#Elapsed time:  7112.61 s
#------------------------------------------------------------------------------
#
#Response for player/7666. Successful:  <Response [200]>
#
#Total successful requests:  897
#Completed :  34.50 %
#Elapsed time:  7116.34 s
#------------------------------------------------------------------------------
#
#Response for player/12490. Successful:  <Response [200]>
#
#Total successful requests:  898
#Completed :  34.54 %
#Elapsed time:  7132.32 s
#------------------------------------------------------------------------------
#
#Response for player/32345. Successful:  <Response [200]>
#
#Total successful requests:  899
#Completed :  34.58 %
#Elapsed time:  7162.27 s
#------------------------------------------------------------------------------
#
#Response for player/42630. Successful:  <Response [200]>
#
#Total successful requests:  900
#Completed :  34.62 %
#Elapsed time:  7165.92 s
#------------------------------------------------------------------------------
#
#Response for player/43549. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  901
#Completed :  34.65 %
#Elapsed time:  7176.33 s
#------------------------------------------------------------------------------
#
#Response for player/355583. Successful:  <Response [200]>
#
#Total successful requests:  902
#Completed :  34.69 %
#Elapsed time:  7180.11 s
#------------------------------------------------------------------------------
#
#Response for player/25098. Successful:  <Response [200]>
#
#Total successful requests:  903
#Completed :  34.73 %
#Elapsed time:  7187.64 s
#------------------------------------------------------------------------------
#
#Response for player/35805. Successful:  <Response [200]>
#
#Total successful requests:  904
#Completed :  34.77 %
#Elapsed time:  7189.77 s
#------------------------------------------------------------------------------
#
#Response for player/348129. Successful:  <Response [200]>
#
#Total successful requests:  905
#Completed :  34.81 %
#Elapsed time:  7197.54 s
#------------------------------------------------------------------------------
#
#Response for player/49619. Successful:  <Response [200]>
#
#Total successful requests:  906
#Completed :  34.85 %
#Elapsed time:  7203.45 s
#------------------------------------------------------------------------------
#
#Response for player/52821. Successful:  <Response [200]>
#
#Total successful requests:  907
#Completed :  34.88 %
#Elapsed time:  7209.73 s
#------------------------------------------------------------------------------
#
#Response for player/47190. Successful:  <Response [200]>
#
#Total successful requests:  908
#Completed :  34.92 %
#Elapsed time:  7212.02 s
#------------------------------------------------------------------------------
#
#Response for player/27978. Successful:  <Response [200]>
#
#Total successful requests:  909
#Completed :  34.96 %
#Elapsed time:  7220.26 s
#------------------------------------------------------------------------------
#
#Response for player/37605. Successful:  <Response [200]>
#
#Total successful requests:  910
#Completed :  35.00 %
#Elapsed time:  7223.73 s
#------------------------------------------------------------------------------
#
#Response for player/52675. Successful:  <Response [200]>
#
#Total successful requests:  911
#Completed :  35.04 %
#Elapsed time:  7242.42 s
#------------------------------------------------------------------------------
#
#Response for player/550215. Successful:  <Response [200]>
#
#Total successful requests:  912
#Completed :  35.08 %
#Elapsed time:  7244.17 s
#------------------------------------------------------------------------------
#
#Response for player/364329. Successful:  <Response [200]>
#
#Total successful requests:  913
#Completed :  35.12 %
#Elapsed time:  7247.74 s
#------------------------------------------------------------------------------
#
#Response for player/642519. Successful:  <Response [200]>
#
#Total successful requests:  914
#Completed :  35.15 %
#Elapsed time:  7249.37 s
#------------------------------------------------------------------------------
#
#Response for player/49557. Successful:  <Response [200]>
#
#Total successful requests:  915
#Completed :  35.19 %
#Elapsed time:  7254.01 s
#------------------------------------------------------------------------------
#
#Response for player/50240. Successful:  <Response [200]>
#
#Total successful requests:  916
#Completed :  35.23 %
#Elapsed time:  7257.82 s
#------------------------------------------------------------------------------
#
#Response for player/43271. Successful:  <Response [200]>
#
#Total successful requests:  917
#Completed :  35.27 %
#Elapsed time:  7261.22 s
#------------------------------------------------------------------------------
#
#Response for player/41318. Successful:  <Response [200]>
#
#Total successful requests:  918
#Completed :  35.31 %
#Elapsed time:  7265.00 s
#------------------------------------------------------------------------------
#
#Response for player/38111. Successful:  <Response [200]>
#
#Total successful requests:  919
#Completed :  35.35 %
#Elapsed time:  7281.82 s
#------------------------------------------------------------------------------
#
#Response for player/8954. Successful:  <Response [200]>
#
#Total successful requests:  920
#Completed :  35.38 %
#Elapsed time:  7286.21 s
#------------------------------------------------------------------------------
#
#Response for player/384817. Successful:  <Response [200]>
#
#Total successful requests:  921
#Completed :  35.42 %
#Elapsed time:  7290.90 s
#------------------------------------------------------------------------------
#
#Response for player/37703. Successful:  <Response [200]>
#
#Total successful requests:  922
#Completed :  35.46 %
#Elapsed time:  7297.82 s
#------------------------------------------------------------------------------
#
#Response for player/55714. Successful:  <Response [200]>
#
#Total successful requests:  923
#Completed :  35.50 %
#Elapsed time:  7299.85 s
#------------------------------------------------------------------------------
#
#Response for player/15917. Successful:  <Response [200]>
#
#Total successful requests:  924
#Completed :  35.54 %
#Elapsed time:  7313.98 s
#------------------------------------------------------------------------------
#
#Response for player/4185. Successful:  <Response [200]>
#
#Total successful requests:  925
#Completed :  35.58 %
#Elapsed time:  7316.71 s
#------------------------------------------------------------------------------
#
#Response for player/24839. Successful:  <Response [200]>
#
#Total successful requests:  926
#Completed :  35.62 %
#Elapsed time:  7327.97 s
#------------------------------------------------------------------------------
#
#Response for player/348148. Successful:  <Response [200]>
#
#Total successful requests:  927
#Completed :  35.65 %
#Elapsed time:  7332.65 s
#------------------------------------------------------------------------------
#
#Response for player/41304. Successful:  <Response [200]>
#
#Total successful requests:  928
#Completed :  35.69 %
#Elapsed time:  7348.01 s
#------------------------------------------------------------------------------
#
#Response for player/46592. Successful:  <Response [200]>
#
#Total successful requests:  929
#Completed :  35.73 %
#Elapsed time:  7350.74 s
#------------------------------------------------------------------------------
#
#Response for player/392945. Successful:  <Response [200]>
#
#Total successful requests:  930
#Completed :  35.77 %
#Elapsed time:  7352.12 s
#------------------------------------------------------------------------------
#
#Response for player/40556. Successful:  <Response [200]>
#
#Total successful requests:  931
#Completed :  35.81 %
#Elapsed time:  7367.02 s
#------------------------------------------------------------------------------
#
#Response for player/55562. Successful:  <Response [200]>
#
#Total successful requests:  932
#Completed :  35.85 %
#Elapsed time:  7368.34 s
#------------------------------------------------------------------------------
#
#Response for player/308794. Successful:  <Response [200]>
#
#Total successful requests:  933
#Completed :  35.88 %
#Elapsed time:  7372.36 s
#------------------------------------------------------------------------------
#
#Response for player/534734. Successful:  <Response [200]>
#
#Total successful requests:  934
#Completed :  35.92 %
#Elapsed time:  7373.98 s
#------------------------------------------------------------------------------
#
#Response for player/235524. Successful:  <Response [200]>
#
#Total successful requests:  935
#Completed :  35.96 %
#Elapsed time:  7383.55 s
#------------------------------------------------------------------------------
#
#Response for player/36948. Successful:  <Response [200]>
#
#Total successful requests:  936
#Completed :  36.00 %
#Elapsed time:  7388.99 s
#------------------------------------------------------------------------------
#
#Response for player/49854. Successful:  <Response [200]>
#
#Total successful requests:  937
#Completed :  36.04 %
#Elapsed time:  7390.73 s
#------------------------------------------------------------------------------
#
#Response for player/1093091. Successful:  <Response [200]>
#
#Total successful requests:  938
#Completed :  36.08 %
#Elapsed time:  7394.58 s
#------------------------------------------------------------------------------
#
#Response for player/38989. Successful:  <Response [200]>
#
#Total successful requests:  939
#Completed :  36.12 %
#Elapsed time:  7395.35 s
#------------------------------------------------------------------------------
#
#Response for player/506612. Successful:  <Response [200]>
#
#Total successful requests:  940
#Completed :  36.15 %
#Elapsed time:  7405.02 s
#------------------------------------------------------------------------------
#
#Response for player/38952. Successful:  <Response [200]>
#
#Total successful requests:  941
#Completed :  36.19 %
#Elapsed time:  7406.66 s
#------------------------------------------------------------------------------
#
#Response for player/38133. Successful:  <Response [200]>
#
#Total successful requests:  942
#Completed :  36.23 %
#Elapsed time:  7412.64 s
#------------------------------------------------------------------------------
#
#Response for player/33120. Successful:  <Response [200]>
#
#Total successful requests:  943
#Completed :  36.27 %
#Elapsed time:  7414.32 s
#------------------------------------------------------------------------------
#
#Response for player/1005257. Successful:  <Response [200]>
#
#Total successful requests:  944
#Completed :  36.31 %
#Elapsed time:  7436.70 s
#------------------------------------------------------------------------------
#
#Response for player/25433. Successful:  <Response [200]>
#
#Total successful requests:  945
#Completed :  36.35 %
#Elapsed time:  7450.82 s
#------------------------------------------------------------------------------
#
#Response for player/23691. Successful:  <Response [200]>
#
#Total successful requests:  946
#Completed :  36.38 %
#Elapsed time:  7452.53 s
#------------------------------------------------------------------------------
#
#Response for player/55424. Successful:  <Response [200]>
#
#Total successful requests:  947
#Completed :  36.42 %
#Elapsed time:  7455.23 s
#------------------------------------------------------------------------------
#
#Response for player/55571. Successful:  <Response [200]>
#
#Total successful requests:  948
#Completed :  36.46 %
#Elapsed time:  7456.76 s
#------------------------------------------------------------------------------
#
#Response for player/1125867. Successful:  <Response [200]>
#
#Total successful requests:  949
#Completed :  36.50 %
#Elapsed time:  7458.49 s
#------------------------------------------------------------------------------
#
#Response for player/307653. Successful:  <Response [200]>
#
#Total successful requests:  950
#Completed :  36.54 %
#Elapsed time:  7460.53 s
#------------------------------------------------------------------------------
#
#Response for player/6903. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  951
#Completed :  36.58 %
#Elapsed time:  7470.52 s
#------------------------------------------------------------------------------
#
#Response for player/738445. Successful:  <Response [200]>
#
#Total successful requests:  952
#Completed :  36.62 %
#Elapsed time:  7474.13 s
#------------------------------------------------------------------------------
#
#Response for player/414249. Successful:  <Response [200]>
#
#Total successful requests:  953
#Completed :  36.65 %
#Elapsed time:  7477.70 s
#------------------------------------------------------------------------------
#
#Response for player/268739. Successful:  <Response [200]>
#
#Total successful requests:  954
#Completed :  36.69 %
#Elapsed time:  7479.85 s
#------------------------------------------------------------------------------
#
#Response for player/17134. Successful:  <Response [200]>
#
#Total successful requests:  955
#Completed :  36.73 %
#Elapsed time:  7482.66 s
#------------------------------------------------------------------------------
#
#Response for player/55652. Successful:  <Response [200]>
#
#Total successful requests:  956
#Completed :  36.77 %
#Elapsed time:  7489.69 s
#------------------------------------------------------------------------------
#
#Response for player/308294. Successful:  <Response [200]>
#
#Total successful requests:  957
#Completed :  36.81 %
#Elapsed time:  7493.68 s
#------------------------------------------------------------------------------
#
#Response for player/51211. Successful:  <Response [200]>
#
#Total successful requests:  958
#Completed :  36.85 %
#Elapsed time:  7494.84 s
#------------------------------------------------------------------------------
#
#Response for player/46681. Successful:  <Response [200]>
#
#Total successful requests:  959
#Completed :  36.88 %
#Elapsed time:  7520.46 s
#------------------------------------------------------------------------------
#
#Response for player/42599. Successful:  <Response [200]>
#
#Total successful requests:  960
#Completed :  36.92 %
#Elapsed time:  7525.55 s
#------------------------------------------------------------------------------
#
#Response for player/444135. Successful:  <Response [200]>
#
#Total successful requests:  961
#Completed :  36.96 %
#Elapsed time:  7529.40 s
#------------------------------------------------------------------------------
#
#Response for player/489889. Successful:  <Response [200]>
#
#Total successful requests:  962
#Completed :  37.00 %
#Elapsed time:  7537.15 s
#------------------------------------------------------------------------------
#
#Response for player/48449. Successful:  <Response [200]>
#
#Total successful requests:  963
#Completed :  37.04 %
#Elapsed time:  7540.56 s
#------------------------------------------------------------------------------
#
#Response for player/793457. Successful:  <Response [200]>
#
#Total successful requests:  964
#Completed :  37.08 %
#Elapsed time:  7548.65 s
#------------------------------------------------------------------------------
#
#Response for player/51248. Successful:  <Response [200]>
#
#Total successful requests:  965
#Completed :  37.12 %
#Elapsed time:  7554.64 s
#------------------------------------------------------------------------------
#
#Response for player/554691. Successful:  <Response [200]>
#
#Total successful requests:  966
#Completed :  37.15 %
#Elapsed time:  7574.49 s
#------------------------------------------------------------------------------
#
#Response for player/7946. Successful:  <Response [200]>
#
#Total successful requests:  967
#Completed :  37.19 %
#Elapsed time:  7575.80 s
#------------------------------------------------------------------------------
#
#Response for player/27225. Successful:  <Response [200]>
#
#Total successful requests:  968
#Completed :  37.23 %
#Elapsed time:  7590.15 s
#------------------------------------------------------------------------------
#
#Response for player/10816. Successful:  <Response [200]>
#
#Total successful requests:  969
#Completed :  37.27 %
#Elapsed time:  7606.52 s
#------------------------------------------------------------------------------
#
#Response for player/47232. Successful:  <Response [200]>
#
#Total successful requests:  970
#Completed :  37.31 %
#Elapsed time:  7607.22 s
#------------------------------------------------------------------------------
#
#Response for player/50835. Successful:  <Response [200]>
#
#Total successful requests:  971
#Completed :  37.35 %
#Elapsed time:  7615.39 s
#------------------------------------------------------------------------------
#
#Response for player/25536. Successful:  <Response [200]>
#
#Total successful requests:  972
#Completed :  37.38 %
#Elapsed time:  7618.35 s
#------------------------------------------------------------------------------
#
#Response for player/52833. Successful:  <Response [200]>
#
#Total successful requests:  973
#Completed :  37.42 %
#Elapsed time:  7619.28 s
#------------------------------------------------------------------------------
#
#Response for player/550235. Successful:  <Response [200]>
#
#Total successful requests:  974
#Completed :  37.46 %
#Elapsed time:  7620.58 s
#------------------------------------------------------------------------------
#
#Response for player/524253. Successful:  <Response [200]>
#
#Total successful requests:  975
#Completed :  37.50 %
#Elapsed time:  7646.90 s
#------------------------------------------------------------------------------
#
#Response for player/30077. Successful:  <Response [200]>
#
#Total successful requests:  976
#Completed :  37.54 %
#Elapsed time:  7653.31 s
#------------------------------------------------------------------------------
#
#Response for player/23874. Successful:  <Response [200]>
#
#Total successful requests:  977
#Completed :  37.58 %
#Elapsed time:  7660.67 s
#------------------------------------------------------------------------------
#
#Response for player/629070. Successful:  <Response [200]>
#
#Total successful requests:  978
#Completed :  37.62 %
#Elapsed time:  7687.75 s
#------------------------------------------------------------------------------
#
#Response for player/36299. Successful:  <Response [200]>
#
#Total successful requests:  979
#Completed :  37.65 %
#Elapsed time:  7691.45 s
#------------------------------------------------------------------------------
#
#Response for player/4996. Successful:  <Response [200]>
#
#Total successful requests:  980
#Completed :  37.69 %
#Elapsed time:  7708.41 s
#------------------------------------------------------------------------------
#
#Response for player/17119. Successful:  <Response [200]>
#
#Total successful requests:  981
#Completed :  37.73 %
#Elapsed time:  7719.97 s
#------------------------------------------------------------------------------
#
#Response for player/19469. Successful:  <Response [200]>
#
#Total successful requests:  982
#Completed :  37.77 %
#Elapsed time:  7723.97 s
#------------------------------------------------------------------------------
#
#Response for player/36835. Successful:  <Response [200]>
#
#Total successful requests:  983
#Completed :  37.81 %
#Elapsed time:  7732.79 s
#------------------------------------------------------------------------------
#
#Response for player/55909. Successful:  <Response [200]>
#
#Total successful requests:  984
#Completed :  37.85 %
#Elapsed time:  7735.00 s
#------------------------------------------------------------------------------
#
#Response for player/574287. Successful:  <Response [200]>
#
#Total successful requests:  985
#Completed :  37.88 %
#Elapsed time:  7744.86 s
#------------------------------------------------------------------------------
#
#Response for player/24918. Successful:  <Response [200]>
#
#Total successful requests:  986
#Completed :  37.92 %
#Elapsed time:  7767.63 s
#------------------------------------------------------------------------------
#
#Response for player/37730. Successful:  <Response [200]>
#
#Total successful requests:  987
#Completed :  37.96 %
#Elapsed time:  7769.45 s
#------------------------------------------------------------------------------
#
#Response for player/524249. Successful:  <Response [200]>
#
#Total successful requests:  988
#Completed :  38.00 %
#Elapsed time:  7773.15 s
#------------------------------------------------------------------------------
#
#Response for player/44696. Successful:  <Response [200]>
#
#Total successful requests:  989
#Completed :  38.04 %
#Elapsed time:  7781.40 s
#------------------------------------------------------------------------------
#
#Response for player/343529. Successful:  <Response [200]>
#
#Total successful requests:  990
#Completed :  38.08 %
#Elapsed time:  7783.84 s
#------------------------------------------------------------------------------
#
#Response for player/288992. Successful:  <Response [200]>
#
#Total successful requests:  991
#Completed :  38.12 %
#Elapsed time:  7785.71 s
#------------------------------------------------------------------------------
#
#Response for player/24952. Successful:  <Response [200]>
#
#Total successful requests:  992
#Completed :  38.15 %
#Elapsed time:  7791.62 s
#------------------------------------------------------------------------------
#
#Response for player/37494. Successful:  <Response [200]>
#
#Total successful requests:  993
#Completed :  38.19 %
#Elapsed time:  7801.74 s
#------------------------------------------------------------------------------
#
#Response for player/450860. Successful:  <Response [200]>
#
#Total successful requests:  994
#Completed :  38.23 %
#Elapsed time:  7815.15 s
#------------------------------------------------------------------------------
#
#Response for player/55846. Successful:  <Response [200]>
#
#Total successful requests:  995
#Completed :  38.27 %
#Elapsed time:  7820.60 s
#------------------------------------------------------------------------------
#
#Response for player/51870. Successful:  <Response [200]>
#
#Total successful requests:  996
#Completed :  38.31 %
#Elapsed time:  7821.38 s
#------------------------------------------------------------------------------
#
#Response for player/17102. Successful:  <Response [200]>
#
#Total successful requests:  997
#Completed :  38.35 %
#Elapsed time:  7829.15 s
#------------------------------------------------------------------------------
#
#Response for player/40375. Successful:  <Response [200]>
#
#Total successful requests:  998
#Completed :  38.38 %
#Elapsed time:  7832.71 s
#------------------------------------------------------------------------------
#
#Response for player/16975. Successful:  <Response [200]>
#
#Total successful requests:  999
#Completed :  38.42 %
#Elapsed time:  7838.88 s
#------------------------------------------------------------------------------
#
#Response for player/23799. Successful:  <Response [200]>
#
#Total successful requests:  1000
#Completed :  38.46 %
#Elapsed time:  7852.98 s
#------------------------------------------------------------------------------
#
#Response for page 6 Successful:  <Response [200]> 	=>
#

#list of players:  200
#Response for player/41224. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  1001
#Completed :  38.50 %
#Elapsed time:  7911.05 s
#------------------------------------------------------------------------------
#
#Response for player/24901. Successful:  <Response [200]>
#
#Total successful requests:  1002
#Completed :  38.54 %
#Elapsed time:  7912.79 s
#------------------------------------------------------------------------------
#
#Response for player/16406. Successful:  <Response [200]>
#
#Total successful requests:  1003
#Completed :  38.58 %
#Elapsed time:  7915.24 s
#------------------------------------------------------------------------------
#
#Response for player/32201. Successful:  <Response [200]>
#
#Total successful requests:  1004
#Completed :  38.62 %
#Elapsed time:  7935.96 s
#------------------------------------------------------------------------------
#
#Response for player/477021. Successful:  <Response [200]>
#
#Total successful requests:  1005
#Completed :  38.65 %
#Elapsed time:  7937.33 s
#------------------------------------------------------------------------------
#
#Response for player/341593. Successful:  <Response [200]>
#
#Total successful requests:  1006
#Completed :  38.69 %
#Elapsed time:  7939.10 s
#------------------------------------------------------------------------------
#
#Response for player/52287. Successful:  <Response [200]>
#
#Total successful requests:  1007
#Completed :  38.73 %
#Elapsed time:  7942.58 s
#------------------------------------------------------------------------------
#
#Response for player/32391. Successful:  <Response [200]>
#
#Total successful requests:  1008
#Completed :  38.77 %
#Elapsed time:  7954.67 s
#------------------------------------------------------------------------------
#
#Response for player/21646. Successful:  <Response [200]>
#
#Total successful requests:  1009
#Completed :  38.81 %
#Elapsed time:  7966.07 s
#------------------------------------------------------------------------------
#
#Response for player/681117. Successful:  <Response [200]>
#
#Total successful requests:  1010
#Completed :  38.85 %
#Elapsed time:  7970.66 s
#------------------------------------------------------------------------------
#
#Response for player/52630. Successful:  <Response [200]>
#
#Total successful requests:  1011
#Completed :  38.88 %
#Elapsed time:  7976.48 s
#------------------------------------------------------------------------------
#
#Response for player/38708. Successful:  <Response [200]>
#
#Total successful requests:  1012
#Completed :  38.92 %
#Elapsed time:  7977.44 s
#------------------------------------------------------------------------------
#
#Response for player/372116. Successful:  <Response [200]>
#
#Total successful requests:  1013
#Completed :  38.96 %
#Elapsed time:  7979.09 s
#------------------------------------------------------------------------------
#
#Response for player/36627. Successful:  <Response [200]>
#
#Total successful requests:  1014
#Completed :  39.00 %
#Elapsed time:  7987.66 s
#------------------------------------------------------------------------------
#
#Response for player/48465. Successful:  <Response [200]>
#
#Total successful requests:  1015
#Completed :  39.04 %
#Elapsed time:  8000.24 s
#------------------------------------------------------------------------------
#
#Response for player/52206. Successful:  <Response [200]>
#
#Total successful requests:  1016
#Completed :  39.08 %
#Elapsed time:  8007.89 s
#------------------------------------------------------------------------------
#
#Response for player/24943. Successful:  <Response [200]>
#
#Total successful requests:  1017
#Completed :  39.12 %
#Elapsed time:  8010.61 s
#------------------------------------------------------------------------------
#
#Response for player/48284. Successful:  <Response [200]>
#
#Total successful requests:  1018
#Completed :  39.15 %
#Elapsed time:  8020.44 s
#------------------------------------------------------------------------------
#
#Response for player/24874. Successful:  <Response [200]>
#
#Total successful requests:  1019
#Completed :  39.19 %
#Elapsed time:  8027.25 s
#------------------------------------------------------------------------------
#
#Response for player/438563. Successful:  <Response [200]>
#
#Total successful requests:  1020
#Completed :  39.23 %
#Elapsed time:  8029.50 s
#------------------------------------------------------------------------------
#
#Response for player/6256. Successful:  <Response [200]>
#
#Total successful requests:  1021
#Completed :  39.27 %
#Elapsed time:  8034.95 s
#------------------------------------------------------------------------------
#
#Response for player/50860. Successful:  <Response [200]>
#
#Total successful requests:  1022
#Completed :  39.31 %
#Elapsed time:  8038.06 s
#------------------------------------------------------------------------------
#
#Response for player/425639. Successful:  <Response [200]>
#
#Total successful requests:  1023
#Completed :  39.35 %
#Elapsed time:  8049.22 s
#------------------------------------------------------------------------------
#
#Response for player/25543. Successful:  <Response [200]>
#
#Total successful requests:  1024
#Completed :  39.38 %
#Elapsed time:  8054.71 s
#------------------------------------------------------------------------------
#
#Response for player/26872. Successful:  <Response [200]>
#
#Total successful requests:  1025
#Completed :  39.42 %
#Elapsed time:  8064.54 s
#------------------------------------------------------------------------------
#
#Response for player/362541. Successful:  <Response [200]>
#
#Total successful requests:  1026
#Completed :  39.46 %
#Elapsed time:  8079.08 s
#------------------------------------------------------------------------------
#
#Response for player/332996. Successful:  <Response [200]>
#
#Total successful requests:  1027
#Completed :  39.50 %
#Elapsed time:  8106.41 s
#------------------------------------------------------------------------------
#
#Response for player/30954. Successful:  <Response [200]>
#
#Total successful requests:  1028
#Completed :  39.54 %
#Elapsed time:  8124.39 s
#------------------------------------------------------------------------------
#
#Response for player/16951. Successful:  <Response [200]>
#
#Total successful requests:  1029
#Completed :  39.58 %
#Elapsed time:  8128.92 s
#------------------------------------------------------------------------------
#
#Response for player/13414. Successful:  <Response [200]>
#
#Total successful requests:  1030
#Completed :  39.62 %
#Elapsed time:  8134.38 s
#------------------------------------------------------------------------------
#
#Response for player/4629. Successful:  <Response [200]>
#
#Total successful requests:  1031
#Completed :  39.65 %
#Elapsed time:  8139.59 s
#------------------------------------------------------------------------------
#
#Response for player/261354. Successful:  <Response [200]>
#
#Total successful requests:  1032
#Completed :  39.69 %
#Elapsed time:  8146.88 s
#------------------------------------------------------------------------------
#
#Response for player/36993. Successful:  <Response [200]>
#
#Total successful requests:  1033
#Completed :  39.73 %
#Elapsed time:  8176.73 s
#------------------------------------------------------------------------------
#
#Response for player/41285. Successful:  <Response [200]>
#
#Total successful requests:  1034
#Completed :  39.77 %
#Elapsed time:  8183.14 s
#------------------------------------------------------------------------------
#
#Response for player/19394. Successful:  <Response [200]>
#
#Total successful requests:  1035
#Completed :  39.81 %
#Elapsed time:  8193.91 s
#------------------------------------------------------------------------------
#
#Response for player/353431. Successful:  <Response [200]>
#
#Total successful requests:  1036
#Completed :  39.85 %
#Elapsed time:  8197.04 s
#------------------------------------------------------------------------------
#
#Response for player/235532. Successful:  <Response [200]>
#
#Total successful requests:  1037
#Completed :  39.88 %
#Elapsed time:  8206.50 s
#------------------------------------------------------------------------------
#
#Response for player/27619. Successful:  <Response [200]>
#
#Total successful requests:  1038
#Completed :  39.92 %
#Elapsed time:  8210.62 s
#------------------------------------------------------------------------------
#
#Response for player/50241. Successful:  <Response [200]>
#
#Total successful requests:  1039
#Completed :  39.96 %
#Elapsed time:  8223.60 s
#------------------------------------------------------------------------------
#
#Response for player/474760. Successful:  <Response [200]>
#
#Total successful requests:  1040
#Completed :  40.00 %
#Elapsed time:  8235.98 s
#------------------------------------------------------------------------------
#
#Response for player/5239. Successful:  <Response [200]>
#
#Total successful requests:  1041
#Completed :  40.04 %
#Elapsed time:  8237.21 s
#------------------------------------------------------------------------------
#
#Response for player/49920. Successful:  <Response [200]>
#
#Total successful requests:  1042
#Completed :  40.08 %
#Elapsed time:  8242.18 s
#------------------------------------------------------------------------------
#
#Response for player/38264. Successful:  <Response [200]>
#
#Total successful requests:  1043
#Completed :  40.12 %
#Elapsed time:  8244.59 s
#------------------------------------------------------------------------------
#
#Response for player/8520. Successful:  <Response [200]>
#
#Total successful requests:  1044
#Completed :  40.15 %
#Elapsed time:  8256.38 s
#------------------------------------------------------------------------------
#
#Response for player/44014. Successful:  <Response [200]>
#
#Total successful requests:  1045
#Completed :  40.19 %
#Elapsed time:  8270.75 s
#------------------------------------------------------------------------------
#
#Response for player/28792. Successful:  <Response [200]>
#
#Total successful requests:  1046
#Completed :  40.23 %
#Elapsed time:  8272.52 s
#------------------------------------------------------------------------------
#
#Response for player/37243. Successful:  <Response [200]>
#
#Total successful requests:  1047
#Completed :  40.27 %
#Elapsed time:  8274.47 s
#------------------------------------------------------------------------------
#
#Response for player/46945. Successful:  <Response [200]>
#
#Total successful requests:  1048
#Completed :  40.31 %
#Elapsed time:  8285.59 s
#------------------------------------------------------------------------------
#
#Response for player/24716. Successful:  <Response [200]>
#
#Total successful requests:  1049
#Completed :  40.35 %
#Elapsed time:  8287.72 s
#------------------------------------------------------------------------------
#
#Response for player/427178. Successful:  <Response [200]>
#
#Total successful requests:  1050
#Completed :  40.38 %
#Elapsed time:  8289.71 s
#------------------------------------------------------------------------------
#
#Response for player/12879. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  1051
#Completed :  40.42 %
#Elapsed time:  8309.51 s
#------------------------------------------------------------------------------
#
#Response for player/8990. Successful:  <Response [200]>
#
#Total successful requests:  1052
#Completed :  40.46 %
#Elapsed time:  8313.85 s
#------------------------------------------------------------------------------
#
#Response for player/30112. Successful:  <Response [200]>
#
#Total successful requests:  1053
#Completed :  40.50 %
#Elapsed time:  8318.54 s
#------------------------------------------------------------------------------
#
#Response for player/41046. Successful:  <Response [200]>
#
#Total successful requests:  1054
#Completed :  40.54 %
#Elapsed time:  8333.09 s
#------------------------------------------------------------------------------
#
#Response for player/56059. Successful:  <Response [200]>
#
#Total successful requests:  1055
#Completed :  40.58 %
#Elapsed time:  8336.98 s
#------------------------------------------------------------------------------
#
#Response for player/55782. Successful:  <Response [200]>
#
#Total successful requests:  1056
#Completed :  40.62 %
#Elapsed time:  8339.86 s
#------------------------------------------------------------------------------
#
#Response for player/53230. Successful:  <Response [200]>
#
#Total successful requests:  1057
#Completed :  40.65 %
#Elapsed time:  8347.45 s
#------------------------------------------------------------------------------
#
#Response for player/326632. Successful:  <Response [200]>
#
#Total successful requests:  1058
#Completed :  40.69 %
#Elapsed time:  8350.56 s
#------------------------------------------------------------------------------
#
#Response for player/51865. Successful:  <Response [200]>
#
#Total successful requests:  1059
#Completed :  40.73 %
#Elapsed time:  8353.05 s
#------------------------------------------------------------------------------
#
#Response for player/40618. Successful:  <Response [200]>
#
#Total successful requests:  1060
#Completed :  40.77 %
#Elapsed time:  8355.32 s
#------------------------------------------------------------------------------
#
#Response for player/701215. Successful:  <Response [200]>
#
#Total successful requests:  1061
#Completed :  40.81 %
#Elapsed time:  8362.66 s
#------------------------------------------------------------------------------
#
#Response for player/784369. Successful:  <Response [200]>
#
#Total successful requests:  1062
#Completed :  40.85 %
#Elapsed time:  8363.88 s
#------------------------------------------------------------------------------
#
#Response for player/505120. Successful:  <Response [200]>
#
#Total successful requests:  1063
#Completed :  40.88 %
#Elapsed time:  8374.78 s
#------------------------------------------------------------------------------
#
#Response for player/277912. Successful:  <Response [200]>
#
#Total successful requests:  1064
#Completed :  40.92 %
#Elapsed time:  8379.99 s
#------------------------------------------------------------------------------
#
#Response for player/11724. Successful:  <Response [200]>
#
#Total successful requests:  1065
#Completed :  40.96 %
#Elapsed time:  8383.31 s
#------------------------------------------------------------------------------
#
#Response for player/49554. Successful:  <Response [200]>
#
#Total successful requests:  1066
#Completed :  41.00 %
#Elapsed time:  8390.60 s
#------------------------------------------------------------------------------
#
#Response for player/24711. Successful:  <Response [200]>
#
#Total successful requests:  1067
#Completed :  41.04 %
#Elapsed time:  8395.76 s
#------------------------------------------------------------------------------
#
#Response for player/233400. Successful:  <Response [200]>
#
#Total successful requests:  1068
#Completed :  41.08 %
#Elapsed time:  8402.33 s
#------------------------------------------------------------------------------
#
#Response for player/39091. Successful:  <Response [200]>
#
#Total successful requests:  1069
#Completed :  41.12 %
#Elapsed time:  8406.74 s
#------------------------------------------------------------------------------
#
#Response for player/37532. Successful:  <Response [200]>
#
#Total successful requests:  1070
#Completed :  41.15 %
#Elapsed time:  8434.74 s
#------------------------------------------------------------------------------
#
#Response for player/243942. Successful:  <Response [200]>
#
#Total successful requests:  1071
#Completed :  41.19 %
#Elapsed time:  8438.19 s
#------------------------------------------------------------------------------
#
#Response for player/16362. Successful:  <Response [200]>
#
#Total successful requests:  1072
#Completed :  41.23 %
#Elapsed time:  8440.68 s
#------------------------------------------------------------------------------
#
#Response for player/318842. Successful:  <Response [200]>
#
#Total successful requests:  1073
#Completed :  41.27 %
#Elapsed time:  8442.11 s
#------------------------------------------------------------------------------
#
#Response for player/51300. Successful:  <Response [200]>
#
#Total successful requests:  1074
#Completed :  41.31 %
#Elapsed time:  8445.23 s
#------------------------------------------------------------------------------
#
#Response for player/12909. Successful:  <Response [200]>
#
#Total successful requests:  1075
#Completed :  41.35 %
#Elapsed time:  8454.64 s
#------------------------------------------------------------------------------
#
#Response for player/51885. Successful:  <Response [200]>
#
#Total successful requests:  1076
#Completed :  41.38 %
#Elapsed time:  8462.61 s
#------------------------------------------------------------------------------
#
#Response for player/46189. Successful:  <Response [200]>
#
#Total successful requests:  1077
#Completed :  41.42 %
#Elapsed time:  8463.94 s
#------------------------------------------------------------------------------
#
#Response for player/31820. Successful:  <Response [200]>
#
#Total successful requests:  1078
#Completed :  41.46 %
#Elapsed time:  8466.32 s
#------------------------------------------------------------------------------
#
#Response for player/42647. Successful:  <Response [200]>
#
#Total successful requests:  1079
#Completed :  41.50 %
#Elapsed time:  8467.67 s
#------------------------------------------------------------------------------
#
#Response for player/22365. Successful:  <Response [200]>
#
#Total successful requests:  1080
#Completed :  41.54 %
#Elapsed time:  8481.40 s
#------------------------------------------------------------------------------
#
#Response for player/495964. Successful:  <Response [200]>
#
#Total successful requests:  1081
#Completed :  41.58 %
#Elapsed time:  8486.72 s
#------------------------------------------------------------------------------
#
#Response for player/24996. Successful:  <Response [200]>
#
#Total successful requests:  1082
#Completed :  41.62 %
#Elapsed time:  8493.13 s
#------------------------------------------------------------------------------
#
#Response for player/49178. Successful:  <Response [200]>
#
#Total successful requests:  1083
#Completed :  41.65 %
#Elapsed time:  8496.93 s
#------------------------------------------------------------------------------
#
#Response for player/8224. Successful:  <Response [200]>
#
#Total successful requests:  1084
#Completed :  41.69 %
#Elapsed time:  8498.55 s
#------------------------------------------------------------------------------
#
#Response for player/646173. Successful:  <Response [200]>
#
#Total successful requests:  1085
#Completed :  41.73 %
#Elapsed time:  8509.01 s
#------------------------------------------------------------------------------
#
#Response for player/12850. Successful:  <Response [200]>
#
#Total successful requests:  1086
#Completed :  41.77 %
#Elapsed time:  8511.60 s
#------------------------------------------------------------------------------
#
#Response for player/6453. Successful:  <Response [200]>
#
#Total successful requests:  1087
#Completed :  41.81 %
#Elapsed time:  8514.08 s
#------------------------------------------------------------------------------
#
#Response for player/48456. Successful:  <Response [200]>
#
#Total successful requests:  1088
#Completed :  41.85 %
#Elapsed time:  8515.10 s
#------------------------------------------------------------------------------
#
#Response for player/36952. Successful:  <Response [200]>
#
#Total successful requests:  1089
#Completed :  41.88 %
#Elapsed time:  8517.36 s
#------------------------------------------------------------------------------
#
#Response for player/443150. Successful:  <Response [200]>
#
#Total successful requests:  1090
#Completed :  41.92 %
#Elapsed time:  8528.71 s
#------------------------------------------------------------------------------
#
#Response for player/659081. Successful:  <Response [200]>
#
#Total successful requests:  1091
#Completed :  41.96 %
#Elapsed time:  8530.75 s
#------------------------------------------------------------------------------
#
#Response for player/8942. Successful:  <Response [200]>
#
#Total successful requests:  1092
#Completed :  42.00 %
#Elapsed time:  8532.57 s
#------------------------------------------------------------------------------
#
#Response for player/5685. Successful:  <Response [200]>
#
#Total successful requests:  1093
#Completed :  42.04 %
#Elapsed time:  8535.51 s
#------------------------------------------------------------------------------
#
#Response for player/50742. Successful:  <Response [200]>
#
#Total successful requests:  1094
#Completed :  42.08 %
#Elapsed time:  8541.26 s
#------------------------------------------------------------------------------
#
#Response for player/210283. Successful:  <Response [200]>
#
#Total successful requests:  1095
#Completed :  42.12 %
#Elapsed time:  8544.71 s
#------------------------------------------------------------------------------
#
#Response for player/17025. Successful:  <Response [200]>
#
#Total successful requests:  1096
#Completed :  42.15 %
#Elapsed time:  8548.18 s
#------------------------------------------------------------------------------
#
#Response for player/52823. Successful:  <Response [200]>
#
#Total successful requests:  1097
#Completed :  42.19 %
#Elapsed time:  8549.40 s
#------------------------------------------------------------------------------
#
#Response for player/401537. Successful:  <Response [200]>
#
#Total successful requests:  1098
#Completed :  42.23 %
#Elapsed time:  8569.55 s
#------------------------------------------------------------------------------
#
#Response for player/35673. Successful:  <Response [200]>
#
#Total successful requests:  1099
#Completed :  42.27 %
#Elapsed time:  8581.06 s
#------------------------------------------------------------------------------
#
#Response for player/50840. Successful:  <Response [200]>
#
#Total successful requests:  1100
#Completed :  42.31 %
#Elapsed time:  8592.05 s
#------------------------------------------------------------------------------
#
#Response for player/51437. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  1101
#Completed :  42.35 %
#Elapsed time:  8606.89 s
#------------------------------------------------------------------------------
#
#Response for player/235519. Successful:  <Response [200]>
#
#Total successful requests:  1102
#Completed :  42.38 %
#Elapsed time:  8609.35 s
#------------------------------------------------------------------------------
#
#Response for player/290645. Successful:  <Response [200]>
#
#Total successful requests:  1103
#Completed :  42.42 %
#Elapsed time:  8626.39 s
#------------------------------------------------------------------------------
#
#Response for player/39005. Successful:  <Response [200]>
#
#Total successful requests:  1104
#Completed :  42.46 %
#Elapsed time:  8631.03 s
#------------------------------------------------------------------------------
#
#Response for player/36294. Successful:  <Response [200]>
#
#Total successful requests:  1105
#Completed :  42.50 %
#Elapsed time:  8632.88 s
#------------------------------------------------------------------------------
#
#Response for player/327830. Successful:  <Response [200]>
#
#Total successful requests:  1106
#Completed :  42.54 %
#Elapsed time:  8639.86 s
#------------------------------------------------------------------------------
#
#Response for player/20187. Successful:  <Response [200]>
#
#Total successful requests:  1107
#Completed :  42.58 %
#Elapsed time:  8641.47 s
#------------------------------------------------------------------------------
#
#Response for player/27622. Successful:  <Response [200]>
#
#Total successful requests:  1108
#Completed :  42.62 %
#Elapsed time:  8643.28 s
#------------------------------------------------------------------------------
#
#Response for player/24796. Successful:  <Response [200]>
#
#Total successful requests:  1109
#Completed :  42.65 %
#Elapsed time:  8647.92 s
#------------------------------------------------------------------------------
#
#Response for player/629076. Successful:  <Response [200]>
#
#Total successful requests:  1110
#Completed :  42.69 %
#Elapsed time:  8654.88 s
#------------------------------------------------------------------------------
#
#Response for player/39956. Successful:  <Response [200]>
#
#Total successful requests:  1111
#Completed :  42.73 %
#Elapsed time:  8656.07 s
#------------------------------------------------------------------------------
#
#Response for player/481896. Successful:  <Response [200]>
#
#Total successful requests:  1112
#Completed :  42.77 %
#Elapsed time:  8665.26 s
#------------------------------------------------------------------------------
#
#Response for player/32346. Successful:  <Response [200]>
#
#Total successful requests:  1113
#Completed :  42.81 %
#Elapsed time:  8667.19 s
#------------------------------------------------------------------------------
#
#Response for player/42610. Successful:  <Response [200]>
#
#Total successful requests:  1114
#Completed :  42.85 %
#Elapsed time:  8668.61 s
#------------------------------------------------------------------------------
#
#Response for player/21494. Successful:  <Response [200]>
#
#Total successful requests:  1115
#Completed :  42.88 %
#Elapsed time:  8672.62 s
#------------------------------------------------------------------------------
#
#Response for player/267454. Successful:  <Response [200]>
#
#Total successful requests:  1116
#Completed :  42.92 %
#Elapsed time:  8677.40 s
#------------------------------------------------------------------------------
#
#Response for player/8468. Successful:  <Response [200]>
#
#Total successful requests:  1117
#Completed :  42.96 %
#Elapsed time:  8678.19 s
#------------------------------------------------------------------------------
#
#Response for player/50163. Successful:  <Response [200]>
#
#Total successful requests:  1118
#Completed :  43.00 %
#Elapsed time:  8679.10 s
#------------------------------------------------------------------------------
#
#Response for player/14106. Successful:  <Response [200]>
#
#Total successful requests:  1119
#Completed :  43.04 %
#Elapsed time:  8680.71 s
#------------------------------------------------------------------------------
#
#Response for player/366725. Successful:  <Response [200]>
#
#Total successful requests:  1120
#Completed :  43.08 %
#Elapsed time:  8685.39 s
#------------------------------------------------------------------------------
#
#Response for player/55509. Successful:  <Response [200]>
#
#Total successful requests:  1121
#Completed :  43.12 %
#Elapsed time:  8687.56 s
#------------------------------------------------------------------------------
#
#Response for player/15511. Successful:  <Response [200]>
#
#Total successful requests:  1122
#Completed :  43.15 %
#Elapsed time:  8692.27 s
#------------------------------------------------------------------------------
#
#Response for player/46569. Successful:  <Response [200]>
#
#Total successful requests:  1123
#Completed :  43.19 %
#Elapsed time:  8714.37 s
#------------------------------------------------------------------------------
#
#Response for player/43685. Successful:  <Response [200]>
#
#Total successful requests:  1124
#Completed :  43.23 %
#Elapsed time:  8728.92 s
#------------------------------------------------------------------------------
#
#Response for player/332980. Successful:  <Response [200]>
#
#Total successful requests:  1125
#Completed :  43.27 %
#Elapsed time:  8733.57 s
#------------------------------------------------------------------------------
#
#Response for player/56208. Successful:  <Response [200]>
#
#Total successful requests:  1126
#Completed :  43.31 %
#Elapsed time:  8738.48 s
#------------------------------------------------------------------------------
#
#Response for player/30049. Successful:  <Response [200]>
#
#Total successful requests:  1127
#Completed :  43.35 %
#Elapsed time:  8740.32 s
#------------------------------------------------------------------------------
#
#Response for player/52672. Successful:  <Response [200]>
#
#Total successful requests:  1128
#Completed :  43.38 %
#Elapsed time:  8741.74 s
#------------------------------------------------------------------------------
#
#Response for player/50426. Successful:  <Response [200]>
#
#Total successful requests:  1129
#Completed :  43.42 %
#Elapsed time:  8763.66 s
#------------------------------------------------------------------------------
#
#Response for player/288305. Successful:  <Response [200]>
#
#Total successful requests:  1130
#Completed :  43.46 %
#Elapsed time:  8781.98 s
#------------------------------------------------------------------------------
#
#Response for player/6060. Successful:  <Response [200]>
#
#Total successful requests:  1131
#Completed :  43.50 %
#Elapsed time:  8783.76 s
#------------------------------------------------------------------------------
#
#Response for player/531953. Successful:  <Response [200]>
#
#Total successful requests:  1132
#Completed :  43.54 %
#Elapsed time:  8785.98 s
#------------------------------------------------------------------------------
#
#Response for player/500268. Successful:  <Response [200]>
#
#Total successful requests:  1133
#Completed :  43.58 %
#Elapsed time:  8787.30 s
#------------------------------------------------------------------------------
#
#Response for player/328026. Successful:  <Response [200]>
#
#Total successful requests:  1134
#Completed :  43.62 %
#Elapsed time:  8788.97 s
#------------------------------------------------------------------------------
#
#Response for player/4964. Successful:  <Response [200]>
#
#Total successful requests:  1135
#Completed :  43.65 %
#Elapsed time:  8803.36 s
#------------------------------------------------------------------------------
#
#Response for player/55573. Successful:  <Response [200]>
#
#Total successful requests:  1136
#Completed :  43.69 %
#Elapsed time:  8804.33 s
#------------------------------------------------------------------------------
#
#Response for player/25544. Successful:  <Response [200]>
#
#Total successful requests:  1137
#Completed :  43.73 %
#Elapsed time:  8814.73 s
#------------------------------------------------------------------------------
#
#Response for player/47700. Successful:  <Response [200]>
#
#Total successful requests:  1138
#Completed :  43.77 %
#Elapsed time:  8818.54 s
#------------------------------------------------------------------------------
#
#Response for player/53233. Successful:  <Response [200]>
#
#Total successful requests:  1139
#Completed :  43.81 %
#Elapsed time:  8821.71 s
#------------------------------------------------------------------------------
#
#Response for player/56167. Successful:  <Response [200]>
#
#Total successful requests:  1140
#Completed :  43.85 %
#Elapsed time:  8824.39 s
#------------------------------------------------------------------------------
#
#Response for player/44851. Successful:  <Response [200]>
#
#Total successful requests:  1141
#Completed :  43.88 %
#Elapsed time:  8826.35 s
#------------------------------------------------------------------------------
#
#Response for player/521637. Successful:  <Response [200]>
#
#Total successful requests:  1142
#Completed :  43.92 %
#Elapsed time:  8835.75 s
#------------------------------------------------------------------------------
#
#Response for player/55684. Successful:  <Response [200]>
#
#Total successful requests:  1143
#Completed :  43.96 %
#Elapsed time:  8837.31 s
#------------------------------------------------------------------------------
#
#Response for player/300619. Successful:  <Response [200]>
#
#Total successful requests:  1144
#Completed :  44.00 %
#Elapsed time:  8850.31 s
#------------------------------------------------------------------------------
#
#Response for player/208657. Successful:  <Response [200]>
#
#Total successful requests:  1145
#Completed :  44.04 %
#Elapsed time:  8854.35 s
#------------------------------------------------------------------------------
#
#Response for player/26295. Successful:  <Response [200]>
#
#Total successful requests:  1146
#Completed :  44.08 %
#Elapsed time:  8873.02 s
#------------------------------------------------------------------------------
#
#Response for player/24773. Successful:  <Response [200]>
#
#Total successful requests:  1147
#Completed :  44.12 %
#Elapsed time:  8874.94 s
#------------------------------------------------------------------------------
#
#Response for player/307449. Successful:  <Response [200]>
#
#Total successful requests:  1148
#Completed :  44.15 %
#Elapsed time:  8886.86 s
#------------------------------------------------------------------------------
#
#Response for player/52687. Successful:  <Response [200]>
#
#Total successful requests:  1149
#Completed :  44.19 %
#Elapsed time:  8889.56 s
#------------------------------------------------------------------------------
#
#Response for player/24694. Successful:  <Response [200]>
#
#Total successful requests:  1150
#Completed :  44.23 %
#Elapsed time:  8898.02 s
#------------------------------------------------------------------------------
#
#Response for player/24857. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  1151
#Completed :  44.27 %
#Elapsed time:  8906.01 s
#------------------------------------------------------------------------------
#
#Response for player/26829. Successful:  <Response [200]>
#
#Total successful requests:  1152
#Completed :  44.31 %
#Elapsed time:  8915.17 s
#------------------------------------------------------------------------------
#
#Response for player/42644. Successful:  <Response [200]>
#
#Total successful requests:  1153
#Completed :  44.35 %
#Elapsed time:  8916.79 s
#------------------------------------------------------------------------------
#
#Response for player/36603. Successful:  <Response [200]>
#
#Total successful requests:  1154
#Completed :  44.38 %
#Elapsed time:  8923.50 s
#------------------------------------------------------------------------------
#
#Response for player/52790. Successful:  <Response [200]>
#
#Total successful requests:  1155
#Completed :  44.42 %
#Elapsed time:  8926.36 s
#------------------------------------------------------------------------------
#
#Response for player/20278. Successful:  <Response [200]>
#
#Total successful requests:  1156
#Completed :  44.46 %
#Elapsed time:  8930.75 s
#------------------------------------------------------------------------------
#
#Response for player/36069. Successful:  <Response [200]>
#
#Total successful requests:  1157
#Completed :  44.50 %
#Elapsed time:  8933.53 s
#------------------------------------------------------------------------------
#
#Response for player/39950. Successful:  <Response [200]>
#
#Total successful requests:  1158
#Completed :  44.54 %
#Elapsed time:  8935.23 s
#------------------------------------------------------------------------------
#
#Response for player/55265. Successful:  <Response [200]>
#
#Total successful requests:  1159
#Completed :  44.58 %
#Elapsed time:  8938.48 s
#------------------------------------------------------------------------------
#
#Response for player/55628. Successful:  <Response [200]>
#
#Total successful requests:  1160
#Completed :  44.62 %
#Elapsed time:  8960.37 s
#------------------------------------------------------------------------------
#
#Response for player/52808. Successful:  <Response [200]>
#
#Total successful requests:  1161
#Completed :  44.65 %
#Elapsed time:  8969.00 s
#------------------------------------------------------------------------------
#
#Response for player/26290. Successful:  <Response [200]>
#
#Total successful requests:  1162
#Completed :  44.69 %
#Elapsed time:  8971.91 s
#------------------------------------------------------------------------------
#
#Response for player/39020. Successful:  <Response [200]>
#
#Total successful requests:  1163
#Completed :  44.73 %
#Elapsed time:  8975.00 s
#------------------------------------------------------------------------------
#
#Response for player/470699. Successful:  <Response [200]>
#
#Total successful requests:  1164
#Completed :  44.77 %
#Elapsed time:  8978.20 s
#------------------------------------------------------------------------------
#
#Response for player/12486. Successful:  <Response [200]>
#
#Total successful requests:  1165
#Completed :  44.81 %
#Elapsed time:  8981.32 s
#------------------------------------------------------------------------------
#
#Response for player/414397. Successful:  <Response [200]>
#
#Total successful requests:  1166
#Completed :  44.85 %
#Elapsed time:  8982.32 s
#------------------------------------------------------------------------------
#
#Response for player/43277. Successful:  <Response [200]>
#
#Total successful requests:  1167
#Completed :  44.88 %
#Elapsed time:  9008.80 s
#------------------------------------------------------------------------------
#
#Response for player/30107. Successful:  <Response [200]>
#
#Total successful requests:  1168
#Completed :  44.92 %
#Elapsed time:  9043.29 s
#------------------------------------------------------------------------------
#
#Response for player/6565. Successful:  <Response [200]>
#
#Total successful requests:  1169
#Completed :  44.96 %
#Elapsed time:  9047.93 s
#------------------------------------------------------------------------------
#
#Response for player/677081. Successful:  <Response [200]>
#
#Total successful requests:  1170
#Completed :  45.00 %
#Elapsed time:  9061.73 s
#------------------------------------------------------------------------------
#
#Response for player/10656. Successful:  <Response [200]>
#
#Total successful requests:  1171
#Completed :  45.04 %
#Elapsed time:  9068.60 s
#------------------------------------------------------------------------------
#
#Response for player/919493. Successful:  <Response [200]>
#
#Total successful requests:  1172
#Completed :  45.08 %
#Elapsed time:  9075.67 s
#------------------------------------------------------------------------------
#
#Response for player/11893. Successful:  <Response [200]>
#
#Total successful requests:  1173
#Completed :  45.12 %
#Elapsed time:  9089.07 s
#------------------------------------------------------------------------------
#
#Response for player/28624. Successful:  <Response [200]>
#
#Total successful requests:  1174
#Completed :  45.15 %
#Elapsed time:  9091.48 s
#------------------------------------------------------------------------------
#
#Response for player/28813. Successful:  <Response [200]>
#
#Total successful requests:  1175
#Completed :  45.19 %
#Elapsed time:  9099.59 s
#------------------------------------------------------------------------------
#
#Response for player/257574. Successful:  <Response [200]>
#
#Total successful requests:  1176
#Completed :  45.23 %
#Elapsed time:  9121.52 s
#------------------------------------------------------------------------------
#
#Response for player/16876. Successful:  <Response [200]>
#
#Total successful requests:  1177
#Completed :  45.27 %
#Elapsed time:  9124.93 s
#------------------------------------------------------------------------------
#
#Response for player/42062. Successful:  <Response [200]>
#
#Total successful requests:  1178
#Completed :  45.31 %
#Elapsed time:  9128.13 s
#------------------------------------------------------------------------------
#
#Response for player/4818. Successful:  <Response [200]>
#
#Total successful requests:  1179
#Completed :  45.35 %
#Elapsed time:  9133.66 s
#------------------------------------------------------------------------------
#
#Response for player/539305. Successful:  <Response [200]>
#
#Total successful requests:  1180
#Completed :  45.38 %
#Elapsed time:  9135.55 s
#------------------------------------------------------------------------------
#
#Response for player/52197. Successful:  <Response [200]>
#
#Total successful requests:  1181
#Completed :  45.42 %
#Elapsed time:  9151.61 s
#------------------------------------------------------------------------------
#
#Response for player/333001. Successful:  <Response [200]>
#
#Total successful requests:  1182
#Completed :  45.46 %
#Elapsed time:  9154.63 s
#------------------------------------------------------------------------------
#
#Response for player/40376. Successful:  <Response [200]>
#
#Total successful requests:  1183
#Completed :  45.50 %
#Elapsed time:  9158.15 s
#------------------------------------------------------------------------------
#
#Response for player/23742. Successful:  <Response [200]>
#
#Total successful requests:  1184
#Completed :  45.54 %
#Elapsed time:  9185.86 s
#------------------------------------------------------------------------------
#
#Response for player/233901. Successful:  <Response [200]>
#
#Total successful requests:  1185
#Completed :  45.58 %
#Elapsed time:  9194.60 s
#------------------------------------------------------------------------------
#
#Response for player/55275. Successful:  <Response [200]>
#
#Total successful requests:  1186
#Completed :  45.62 %
#Elapsed time:  9197.75 s
#------------------------------------------------------------------------------
#
#Response for player/348059. Successful:  <Response [200]>
#
#Total successful requests:  1187
#Completed :  45.65 %
#Elapsed time:  9202.53 s
#------------------------------------------------------------------------------
#
#Response for player/42421. Successful:  <Response [200]>
#
#Total successful requests:  1188
#Completed :  45.69 %
#Elapsed time:  9210.05 s
#------------------------------------------------------------------------------
#
#Response for player/55279. Successful:  <Response [200]>
#
#Total successful requests:  1189
#Completed :  45.73 %
#Elapsed time:  9216.08 s
#------------------------------------------------------------------------------
#
#Response for player/20233. Successful:  <Response [200]>
#
#Total successful requests:  1190
#Completed :  45.77 %
#Elapsed time:  9218.62 s
#------------------------------------------------------------------------------
#
#Response for player/794707. Successful:  <Response [200]>
#
#Total successful requests:  1191
#Completed :  45.81 %
#Elapsed time:  9228.07 s
#------------------------------------------------------------------------------
#
#Response for player/319439. Successful:  <Response [200]>
#
#Total successful requests:  1192
#Completed :  45.85 %
#Elapsed time:  9247.54 s
#------------------------------------------------------------------------------
#
#Response for player/459752. Successful:  <Response [200]>
#
#Total successful requests:  1193
#Completed :  45.88 %
#Elapsed time:  9250.47 s
#------------------------------------------------------------------------------
#
#Response for player/696139. Successful:  <Response [200]>
#
#Total successful requests:  1194
#Completed :  45.92 %
#Elapsed time:  9263.93 s
#------------------------------------------------------------------------------
#
#Response for player/19374. Successful:  <Response [200]>
#
#Total successful requests:  1195
#Completed :  45.96 %
#Elapsed time:  9268.45 s
#------------------------------------------------------------------------------
#
#Response for player/10793. Successful:  <Response [200]>
#
#Total successful requests:  1196
#Completed :  46.00 %
#Elapsed time:  9271.67 s
#------------------------------------------------------------------------------
#
#Response for player/23700. Successful:  <Response [200]>
#
#Total successful requests:  1197
#Completed :  46.04 %
#Elapsed time:  9272.44 s
#------------------------------------------------------------------------------
#
#Response for player/232443. Successful:  <Response [200]>
#
#Total successful requests:  1198
#Completed :  46.08 %
#Elapsed time:  9280.41 s
#------------------------------------------------------------------------------
#
#Response for player/55885. Successful:  <Response [200]>
#
#Total successful requests:  1199
#Completed :  46.12 %
#Elapsed time:  9296.93 s
#------------------------------------------------------------------------------
#
#Response for player/45949. Successful:  <Response [200]>
#
#Total successful requests:  1200
#Completed :  46.15 %
#Elapsed time:  9306.61 s
#------------------------------------------------------------------------------
#
#Response for page 7 Successful:  <Response [200]> 	=>
#

#list of players:  200
#Response for player/6261. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  1201
#Completed :  46.19 %
#Elapsed time:  9376.82 s
#------------------------------------------------------------------------------
#
#Response for player/7959. Successful:  <Response [200]>
#
#Total successful requests:  1202
#Completed :  46.23 %
#Elapsed time:  9381.62 s
#------------------------------------------------------------------------------
#
#Response for player/51481. Successful:  <Response [200]>
#
#Total successful requests:  1203
#Completed :  46.27 %
#Elapsed time:  9386.34 s
#------------------------------------------------------------------------------
#
#Response for player/230852. Successful:  <Response [200]>
#
#Total successful requests:  1204
#Completed :  46.31 %
#Elapsed time:  9387.78 s
#------------------------------------------------------------------------------
#
#Response for player/670031. Successful:  <Response [200]>
#
#Total successful requests:  1205
#Completed :  46.35 %
#Elapsed time:  9389.66 s
#------------------------------------------------------------------------------
#
#Response for player/6950. Successful:  <Response [200]>
#
#Total successful requests:  1206
#Completed :  46.38 %
#Elapsed time:  9392.41 s
#------------------------------------------------------------------------------
#
#Response for player/35280. Successful:  <Response [200]>
#
#Total successful requests:  1207
#Completed :  46.42 %
#Elapsed time:  9393.32 s
#------------------------------------------------------------------------------
#
#Response for player/38132. Successful:  <Response [200]>
#
#Total successful requests:  1208
#Completed :  46.46 %
#Elapsed time:  9395.18 s
#------------------------------------------------------------------------------
#
#Response for player/38751. Successful:  <Response [200]>
#
#Total successful requests:  1209
#Completed :  46.50 %
#Elapsed time:  9396.01 s
#------------------------------------------------------------------------------
#
#Response for player/40082. Successful:  <Response [200]>
#
#Total successful requests:  1210
#Completed :  46.54 %
#Elapsed time:  9397.37 s
#------------------------------------------------------------------------------
#
#Response for player/350632. Successful:  <Response [200]>
#
#Total successful requests:  1211
#Completed :  46.58 %
#Elapsed time:  9401.68 s
#------------------------------------------------------------------------------
#
#Response for player/221140. Successful:  <Response [200]>
#
#Total successful requests:  1212
#Completed :  46.62 %
#Elapsed time:  9407.66 s
#------------------------------------------------------------------------------
#
#Response for player/25532. Successful:  <Response [200]>
#
#Total successful requests:  1213
#Completed :  46.65 %
#Elapsed time:  9418.50 s
#------------------------------------------------------------------------------
#
#Response for player/5017. Successful:  <Response [200]>
#
#Total successful requests:  1214
#Completed :  46.69 %
#Elapsed time:  9420.54 s
#------------------------------------------------------------------------------
#
#Response for player/48803. Successful:  <Response [200]>
#
#Total successful requests:  1215
#Completed :  46.73 %
#Elapsed time:  9423.02 s
#------------------------------------------------------------------------------
#
#Response for player/52055. Successful:  <Response [200]>
#
#Total successful requests:  1216
#Completed :  46.77 %
#Elapsed time:  9441.48 s
#------------------------------------------------------------------------------
#
#Response for player/55524. Successful:  <Response [200]>
#
#Total successful requests:  1217
#Completed :  46.81 %
#Elapsed time:  9450.57 s
#------------------------------------------------------------------------------
#
#Response for player/16322. Successful:  <Response [200]>
#
#Total successful requests:  1218
#Completed :  46.85 %
#Elapsed time:  9454.51 s
#------------------------------------------------------------------------------
#
#Response for player/24139. Successful:  <Response [200]>
#
#Total successful requests:  1219
#Completed :  46.88 %
#Elapsed time:  9467.85 s
#------------------------------------------------------------------------------
#
#Response for player/38617. Successful:  <Response [200]>
#
#Total successful requests:  1220
#Completed :  46.92 %
#Elapsed time:  9494.08 s
#------------------------------------------------------------------------------
#
#Response for player/26226. Successful:  <Response [200]>
#
#Total successful requests:  1221
#Completed :  46.96 %
#Elapsed time:  9497.65 s
#------------------------------------------------------------------------------
#
#Response for player/44960. Successful:  <Response [200]>
#
#Total successful requests:  1222
#Completed :  47.00 %
#Elapsed time:  9512.72 s
#------------------------------------------------------------------------------
#
#Response for player/5726. Successful:  <Response [200]>
#
#Total successful requests:  1223
#Completed :  47.04 %
#Elapsed time:  9530.87 s
#------------------------------------------------------------------------------
#
#Response for player/559235. Successful:  <Response [200]>
#
#Total successful requests:  1224
#Completed :  47.08 %
#Elapsed time:  9534.77 s
#------------------------------------------------------------------------------
#
#Response for player/370846. Successful:  <Response [200]>
#
#Total successful requests:  1225
#Completed :  47.12 %
#Elapsed time:  9535.78 s
#------------------------------------------------------------------------------
#
#Response for player/20259. Successful:  <Response [200]>
#
#Total successful requests:  1226
#Completed :  47.15 %
#Elapsed time:  9552.58 s
#------------------------------------------------------------------------------
#
#Response for player/51877. Successful:  <Response [200]>
#
#Total successful requests:  1227
#Completed :  47.19 %
#Elapsed time:  9555.30 s
#------------------------------------------------------------------------------
#
#Response for player/51905. Successful:  <Response [200]>
#
#Total successful requests:  1228
#Completed :  47.23 %
#Elapsed time:  9562.11 s
#------------------------------------------------------------------------------
#
#Response for player/208253. Successful:  <Response [200]>
#
#Total successful requests:  1229
#Completed :  47.27 %
#Elapsed time:  9563.50 s
#------------------------------------------------------------------------------
#
#Response for player/19478. Successful:  <Response [200]>
#
#Total successful requests:  1230
#Completed :  47.31 %
#Elapsed time:  9572.31 s
#------------------------------------------------------------------------------
#
#Response for player/317248. Successful:  <Response [200]>
#
#Total successful requests:  1231
#Completed :  47.35 %
#Elapsed time:  9576.38 s
#------------------------------------------------------------------------------
#
#Response for player/379504. Successful:  <Response [200]>
#
#Total successful requests:  1232
#Completed :  47.38 %
#Elapsed time:  9583.70 s
#------------------------------------------------------------------------------
#
#Response for player/23756. Successful:  <Response [200]>
#
#Total successful requests:  1233
#Completed :  47.42 %
#Elapsed time:  9585.37 s
#------------------------------------------------------------------------------
#
#Response for player/55321. Successful:  <Response [200]>
#
#Total successful requests:  1234
#Completed :  47.46 %
#Elapsed time:  9588.15 s
#------------------------------------------------------------------------------
#
#Response for player/37103. Successful:  <Response [200]>
#
#Total successful requests:  1235
#Completed :  47.50 %
#Elapsed time:  9591.83 s
#------------------------------------------------------------------------------
#
#Response for player/52280. Successful:  <Response [200]>
#
#Total successful requests:  1236
#Completed :  47.54 %
#Elapsed time:  9594.19 s
#------------------------------------------------------------------------------
#
#Response for player/23846. Successful:  <Response [200]>
#
#Total successful requests:  1237
#Completed :  47.58 %
#Elapsed time:  9597.72 s
#------------------------------------------------------------------------------
#
#Response for player/25539. Successful:  <Response [200]>
#
#Total successful requests:  1238
#Completed :  47.62 %
#Elapsed time:  9609.64 s
#------------------------------------------------------------------------------
#
#Response for player/20217. Successful:  <Response [200]>
#
#Total successful requests:  1239
#Completed :  47.65 %
#Elapsed time:  9615.32 s
#------------------------------------------------------------------------------
#
#Response for player/56138. Successful:  <Response [200]>
#
#Total successful requests:  1240
#Completed :  47.69 %
#Elapsed time:  9621.89 s
#------------------------------------------------------------------------------
#
#Response for player/55419. Successful:  <Response [200]>
#
#Total successful requests:  1241
#Completed :  47.73 %
#Elapsed time:  9624.00 s
#------------------------------------------------------------------------------
#
#Response for player/313432. Successful:  <Response [200]>
#
#Total successful requests:  1242
#Completed :  47.77 %
#Elapsed time:  9625.88 s
#------------------------------------------------------------------------------
#
#Response for player/6145. Successful:  <Response [200]>
#
#Total successful requests:  1243
#Completed :  47.81 %
#Elapsed time:  9632.93 s
#------------------------------------------------------------------------------
#
#Response for player/41264. Successful:  <Response [200]>
#
#Total successful requests:  1244
#Completed :  47.85 %
#Elapsed time:  9636.73 s
#------------------------------------------------------------------------------
#
#Response for player/56229. Successful:  <Response [200]>
#
#Total successful requests:  1245
#Completed :  47.88 %
#Elapsed time:  9647.38 s
#------------------------------------------------------------------------------
#
#Response for player/9089. Successful:  <Response [200]>
#
#Total successful requests:  1246
#Completed :  47.92 %
#Elapsed time:  9649.24 s
#------------------------------------------------------------------------------
#
#Response for player/434429. Successful:  <Response [200]>
#
#Total successful requests:  1247
#Completed :  47.96 %
#Elapsed time:  9669.42 s
#------------------------------------------------------------------------------
#
#Response for player/51739. Successful:  <Response [200]>
#
#Total successful requests:  1248
#Completed :  48.00 %
#Elapsed time:  9674.21 s
#------------------------------------------------------------------------------
#
#Response for player/44716. Successful:  <Response [200]>
#
#Total successful requests:  1249
#Completed :  48.04 %
#Elapsed time:  9676.25 s
#------------------------------------------------------------------------------
#
#Response for player/399259. Successful:  <Response [200]>
#
#Total successful requests:  1250
#Completed :  48.08 %
#Elapsed time:  9677.60 s
#------------------------------------------------------------------------------
#
#Response for player/25601. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  1251
#Completed :  48.12 %
#Elapsed time:  9687.32 s
#------------------------------------------------------------------------------
#
#Response for player/55675. Successful:  <Response [200]>
#
#Total successful requests:  1252
#Completed :  48.15 %
#Elapsed time:  9692.59 s
#------------------------------------------------------------------------------
#
#Response for player/38141. Successful:  <Response [200]>
#
#Total successful requests:  1253
#Completed :  48.19 %
#Elapsed time:  9694.44 s
#------------------------------------------------------------------------------
#
#Response for player/23729. Successful:  <Response [200]>
#
#Total successful requests:  1254
#Completed :  48.23 %
#Elapsed time:  9698.76 s
#------------------------------------------------------------------------------
#
#Response for player/701217. Successful:  <Response [200]>
#
#Total successful requests:  1255
#Completed :  48.27 %
#Elapsed time:  9705.52 s
#------------------------------------------------------------------------------
#
#Response for player/345825. Successful:  <Response [200]>
#
#Total successful requests:  1256
#Completed :  48.31 %
#Elapsed time:  9712.25 s
#------------------------------------------------------------------------------
#
#Response for player/51655. Successful:  <Response [200]>
#
#Total successful requests:  1257
#Completed :  48.35 %
#Elapsed time:  9720.21 s
#------------------------------------------------------------------------------
#
#Response for player/45984. Successful:  <Response [200]>
#
#Total successful requests:  1258
#Completed :  48.38 %
#Elapsed time:  9722.93 s
#------------------------------------------------------------------------------
#
#Response for player/943281. Successful:  <Response [200]>
#
#Total successful requests:  1259
#Completed :  48.42 %
#Elapsed time:  9731.28 s
#------------------------------------------------------------------------------
#
#Response for player/26169. Successful:  <Response [200]>
#
#Total successful requests:  1260
#Completed :  48.46 %
#Elapsed time:  9753.32 s
#------------------------------------------------------------------------------
#
#Response for player/526441. Successful:  <Response [200]>
#
#Total successful requests:  1261
#Completed :  48.50 %
#Elapsed time:  9765.45 s
#------------------------------------------------------------------------------
#
#Response for player/8476. Successful:  <Response [200]>
#
#Total successful requests:  1262
#Completed :  48.54 %
#Elapsed time:  9766.70 s
#------------------------------------------------------------------------------
#
#Response for player/552152. Successful:  <Response [200]>
#
#Total successful requests:  1263
#Completed :  48.58 %
#Elapsed time:  9768.12 s
#------------------------------------------------------------------------------
#
#Response for player/37111. Successful:  <Response [200]>
#
#Total successful requests:  1264
#Completed :  48.62 %
#Elapsed time:  9781.35 s
#------------------------------------------------------------------------------
#
#Response for player/931581. Successful:  <Response [200]>
#
#Total successful requests:  1265
#Completed :  48.65 %
#Elapsed time:  9783.25 s
#------------------------------------------------------------------------------
#
#Response for player/311427. Successful:  <Response [200]>
#
#Total successful requests:  1266
#Completed :  48.69 %
#Elapsed time:  9785.10 s
#------------------------------------------------------------------------------
#
#Response for player/25537. Successful:  <Response [200]>
#
#Total successful requests:  1267
#Completed :  48.73 %
#Elapsed time:  9786.56 s
#------------------------------------------------------------------------------
#
#Response for player/55756. Successful:  <Response [200]>
#
#Total successful requests:  1268
#Completed :  48.77 %
#Elapsed time:  9788.19 s
#------------------------------------------------------------------------------
#
#Response for player/14054. Successful:  <Response [200]>
#
#Total successful requests:  1269
#Completed :  48.81 %
#Elapsed time:  9801.07 s
#------------------------------------------------------------------------------
#
#Response for player/23809. Successful:  <Response [200]>
#
#Total successful requests:  1270
#Completed :  48.85 %
#Elapsed time:  9816.83 s
#------------------------------------------------------------------------------
#
#Response for player/55691. Successful:  <Response [200]>
#
#Total successful requests:  1271
#Completed :  48.88 %
#Elapsed time:  9818.90 s
#------------------------------------------------------------------------------
#
#Response for player/50422. Successful:  <Response [200]>
#
#Total successful requests:  1272
#Completed :  48.92 %
#Elapsed time:  9822.61 s
#------------------------------------------------------------------------------
#
#Response for player/25475. Successful:  <Response [200]>
#
#Total successful requests:  1273
#Completed :  48.96 %
#Elapsed time:  9824.08 s
#------------------------------------------------------------------------------
#
#Response for player/24799. Successful:  <Response [200]>
#
#Total successful requests:  1274
#Completed :  49.00 %
#Elapsed time:  9826.82 s
#------------------------------------------------------------------------------
#
#Response for player/33127. Successful:  <Response [200]>
#
#Total successful requests:  1275
#Completed :  49.04 %
#Elapsed time:  9841.45 s
#------------------------------------------------------------------------------
#
#Response for player/38964. Successful:  <Response [200]>
#
#Total successful requests:  1276
#Completed :  49.08 %
#Elapsed time:  9848.99 s
#------------------------------------------------------------------------------
#
#Response for player/343305. Successful:  <Response [200]>
#
#Total successful requests:  1277
#Completed :  49.12 %
#Elapsed time:  9850.23 s
#------------------------------------------------------------------------------
#
#Response for player/47693. Successful:  <Response [200]>
#
#Total successful requests:  1278
#Completed :  49.15 %
#Elapsed time:  9863.21 s
#------------------------------------------------------------------------------
#
#Response for player/27592. Successful:  <Response [200]>
#
#Total successful requests:  1279
#Completed :  49.19 %
#Elapsed time:  9865.25 s
#------------------------------------------------------------------------------
#
#Response for player/320284. Successful:  <Response [200]>
#
#Total successful requests:  1280
#Completed :  49.23 %
#Elapsed time:  9866.71 s
#------------------------------------------------------------------------------
#
#Response for player/55802. Successful:  <Response [200]>
#
#Total successful requests:  1281
#Completed :  49.27 %
#Elapsed time:  9868.29 s
#------------------------------------------------------------------------------
#
#Response for player/38999. Successful:  <Response [200]>
#
#Total successful requests:  1282
#Completed :  49.31 %
#Elapsed time:  9871.12 s
#------------------------------------------------------------------------------
#
#Response for player/23862. Successful:  <Response [200]>
#
#Total successful requests:  1283
#Completed :  49.35 %
#Elapsed time:  9877.07 s
#------------------------------------------------------------------------------
#
#Response for player/12507. Successful:  <Response [200]>
#
#Total successful requests:  1284
#Completed :  49.38 %
#Elapsed time:  9880.56 s
#------------------------------------------------------------------------------
#
#Response for player/52208. Successful:  <Response [200]>
#
#Total successful requests:  1285
#Completed :  49.42 %
#Elapsed time:  9883.83 s
#------------------------------------------------------------------------------
#
#Response for player/52427. Successful:  <Response [200]>
#
#Total successful requests:  1286
#Completed :  49.46 %
#Elapsed time:  9890.22 s
#------------------------------------------------------------------------------
#
#Response for player/17121. Successful:  <Response [200]>
#
#Total successful requests:  1287
#Completed :  49.50 %
#Elapsed time:  9892.56 s
#------------------------------------------------------------------------------
#
#Response for player/1072488. Successful:  <Response [200]>
#
#Total successful requests:  1288
#Completed :  49.54 %
#Elapsed time:  9893.82 s
#------------------------------------------------------------------------------
#
#Response for player/35731. Successful:  <Response [200]>
#
#Total successful requests:  1289
#Completed :  49.58 %
#Elapsed time:  9895.71 s
#------------------------------------------------------------------------------
#
#Response for player/235514. Successful:  <Response [200]>
#
#Total successful requests:  1290
#Completed :  49.62 %
#Elapsed time:  9904.15 s
#------------------------------------------------------------------------------
#
#Response for player/38742. Successful:  <Response [200]>
#
#Total successful requests:  1291
#Completed :  49.65 %
#Elapsed time:  9914.19 s
#------------------------------------------------------------------------------
#
#Response for player/48445. Successful:  <Response [200]>
#
#Total successful requests:  1292
#Completed :  49.69 %
#Elapsed time:  9925.84 s
#------------------------------------------------------------------------------
#
#Response for player/25432. Successful:  <Response [200]>
#
#Total successful requests:  1293
#Completed :  49.73 %
#Elapsed time:  9940.38 s
#------------------------------------------------------------------------------
#
#Response for player/23685. Successful:  <Response [200]>
#
#Total successful requests:  1294
#Completed :  49.77 %
#Elapsed time:  9947.98 s
#------------------------------------------------------------------------------
#
#Response for player/17944. Successful:  <Response [200]>
#
#Total successful requests:  1295
#Completed :  49.81 %
#Elapsed time:  9955.54 s
#------------------------------------------------------------------------------
#
#Response for player/524247. Successful:  <Response [200]>
#
#Total successful requests:  1296
#Completed :  49.85 %
#Elapsed time:  9957.20 s
#------------------------------------------------------------------------------
#
#Response for player/24599. Successful:  <Response [200]>
#
#Total successful requests:  1297
#Completed :  49.88 %
#Elapsed time:  9958.98 s
#------------------------------------------------------------------------------
#
#Response for player/9002. Successful:  <Response [200]>
#
#Total successful requests:  1298
#Completed :  49.92 %
#Elapsed time:  9963.95 s
#------------------------------------------------------------------------------
#
#Response for player/36331. Successful:  <Response [200]>
#
#Total successful requests:  1299
#Completed :  49.96 %
#Elapsed time:  9999.46 s
#------------------------------------------------------------------------------
#
#Response for player/25534. Successful:  <Response [200]>
#
#Total successful requests:  1300
#Completed :  50.00 %
#Elapsed time:  10004.22 s
#------------------------------------------------------------------------------
#
#Response for player/49213. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  1301
#Completed :  50.04 %
#Elapsed time:  10009.45 s
#------------------------------------------------------------------------------
#
#Response for player/25102. Successful:  <Response [200]>
#
#Total successful requests:  1302
#Completed :  50.08 %
#Elapsed time:  10018.83 s
#------------------------------------------------------------------------------
#
#Response for player/42746. Successful:  <Response [200]>
#
#Total successful requests:  1303
#Completed :  50.12 %
#Elapsed time:  10021.47 s
#------------------------------------------------------------------------------
#
#Response for player/43648. Successful:  <Response [200]>
#
#Total successful requests:  1304
#Completed :  50.15 %
#Elapsed time:  10025.74 s
#------------------------------------------------------------------------------
#
#Response for player/51258. Successful:  <Response [200]>
#
#Total successful requests:  1305
#Completed :  50.19 %
#Elapsed time:  10035.00 s
#------------------------------------------------------------------------------
#
#Response for player/44089. Successful:  <Response [200]>
#
#Total successful requests:  1306
#Completed :  50.23 %
#Elapsed time:  10042.01 s
#------------------------------------------------------------------------------
#
#Response for player/25091. Successful:  <Response [200]>
#
#Total successful requests:  1307
#Completed :  50.27 %
#Elapsed time:  10059.57 s
#------------------------------------------------------------------------------
#
#Response for player/48487. Successful:  <Response [200]>
#
#Total successful requests:  1308
#Completed :  50.31 %
#Elapsed time:  10063.64 s
#------------------------------------------------------------------------------
#
#Response for player/422965. Successful:  <Response [200]>
#
#Total successful requests:  1309
#Completed :  50.35 %
#Elapsed time:  10071.95 s
#------------------------------------------------------------------------------
#
#Response for player/308798. Successful:  <Response [200]>
#
#Total successful requests:  1310
#Completed :  50.38 %
#Elapsed time:  10073.77 s
#------------------------------------------------------------------------------
#
#Response for player/303341. Successful:  <Response [200]>
#
#Total successful requests:  1311
#Completed :  50.42 %
#Elapsed time:  10084.55 s
#------------------------------------------------------------------------------
#
#Response for player/22462. Successful:  <Response [200]>
#
#Total successful requests:  1312
#Completed :  50.46 %
#Elapsed time:  10086.28 s
#------------------------------------------------------------------------------
#
#Response for player/365126. Successful:  <Response [200]>
#
#Total successful requests:  1313
#Completed :  50.50 %
#Elapsed time:  10092.59 s
#------------------------------------------------------------------------------
#
#Response for player/530811. Successful:  <Response [200]>
#
#Total successful requests:  1314
#Completed :  50.54 %
#Elapsed time:  10099.25 s
#------------------------------------------------------------------------------
#
#Response for player/45828. Successful:  <Response [200]>
#
#Total successful requests:  1315
#Completed :  50.58 %
#Elapsed time:  10101.03 s
#------------------------------------------------------------------------------
#
#Response for player/24841. Successful:  <Response [200]>
#
#Total successful requests:  1316
#Completed :  50.62 %
#Elapsed time:  10107.70 s
#------------------------------------------------------------------------------
#
#Response for player/447290. Successful:  <Response [200]>
#
#Total successful requests:  1317
#Completed :  50.65 %
#Elapsed time:  10110.44 s
#------------------------------------------------------------------------------
#
#Response for player/7376. Successful:  <Response [200]>
#
#Total successful requests:  1318
#Completed :  50.69 %
#Elapsed time:  10112.28 s
#------------------------------------------------------------------------------
#
#Response for player/5961. Successful:  <Response [200]>
#
#Total successful requests:  1319
#Completed :  50.73 %
#Elapsed time:  10114.80 s
#------------------------------------------------------------------------------
#
#Response for player/56032. Successful:  <Response [200]>
#
#Total successful requests:  1320
#Completed :  50.77 %
#Elapsed time:  10116.65 s
#------------------------------------------------------------------------------
#
#Response for player/46942. Successful:  <Response [200]>
#
#Total successful requests:  1321
#Completed :  50.81 %
#Elapsed time:  10118.15 s
#------------------------------------------------------------------------------
#
#Response for player/272473. Successful:  <Response [200]>
#
#Total successful requests:  1322
#Completed :  50.85 %
#Elapsed time:  10118.98 s
#------------------------------------------------------------------------------
#
#Response for player/919489. Successful:  <Response [200]>
#
#Total successful requests:  1323
#Completed :  50.88 %
#Elapsed time:  10120.90 s
#------------------------------------------------------------------------------
#
#Response for player/34118. Successful:  <Response [200]>
#
#Total successful requests:  1324
#Completed :  50.92 %
#Elapsed time:  10133.43 s
#------------------------------------------------------------------------------
#
#Response for player/56160. Successful:  <Response [200]>
#
#Total successful requests:  1325
#Completed :  50.96 %
#Elapsed time:  10141.35 s
#------------------------------------------------------------------------------
#
#Response for player/25065. Successful:  <Response [200]>
#
#Total successful requests:  1326
#Completed :  51.00 %
#Elapsed time:  10142.67 s
#------------------------------------------------------------------------------
#
#Response for player/36054. Successful:  <Response [200]>
#
#Total successful requests:  1327
#Completed :  51.04 %
#Elapsed time:  10145.58 s
#------------------------------------------------------------------------------
#
#Response for player/25476. Successful:  <Response [200]>
#
#Total successful requests:  1328
#Completed :  51.08 %
#Elapsed time:  10154.48 s
#------------------------------------------------------------------------------
#
#Response for player/55463. Successful:  <Response [200]>
#
#Total successful requests:  1329
#Completed :  51.12 %
#Elapsed time:  10159.83 s
#------------------------------------------------------------------------------
#
#Response for player/384518. Successful:  <Response [200]>
#
#Total successful requests:  1330
#Completed :  51.15 %
#Elapsed time:  10160.49 s
#------------------------------------------------------------------------------
#
#Response for player/55710. Successful:  <Response [200]>
#
#Total successful requests:  1331
#Completed :  51.19 %
#Elapsed time:  10165.99 s
#------------------------------------------------------------------------------
#
#Response for player/33963. Successful:  <Response [200]>
#
#Total successful requests:  1332
#Completed :  51.23 %
#Elapsed time:  10167.45 s
#------------------------------------------------------------------------------
#
#Response for player/213674. Successful:  <Response [200]>
#
#Total successful requests:  1333
#Completed :  51.27 %
#Elapsed time:  10173.92 s
#------------------------------------------------------------------------------
#
#Response for player/26806. Successful:  <Response [200]>
#
#Total successful requests:  1334
#Completed :  51.31 %
#Elapsed time:  10177.79 s
#------------------------------------------------------------------------------
#
#Response for player/56149. Successful:  <Response [200]>
#
#Total successful requests:  1335
#Completed :  51.35 %
#Elapsed time:  10182.05 s
#------------------------------------------------------------------------------
#
#Response for player/8137. Successful:  <Response [200]>
#
#Total successful requests:  1336
#Completed :  51.38 %
#Elapsed time:  10198.06 s
#------------------------------------------------------------------------------
#
#Response for player/376116. Successful:  <Response [200]>
#
#Total successful requests:  1337
#Completed :  51.42 %
#Elapsed time:  10205.91 s
#------------------------------------------------------------------------------
#
#Response for player/4890. Successful:  <Response [200]>
#
#Total successful requests:  1338
#Completed :  51.46 %
#Elapsed time:  10220.55 s
#------------------------------------------------------------------------------
#
#Response for player/6143. Successful:  <Response [200]>
#
#Total successful requests:  1339
#Completed :  51.50 %
#Elapsed time:  10223.04 s
#------------------------------------------------------------------------------
#
#Response for player/47011. Successful:  <Response [200]>
#
#Total successful requests:  1340
#Completed :  51.54 %
#Elapsed time:  10227.60 s
#------------------------------------------------------------------------------
#
#Response for player/547079. Successful:  <Response [200]>
#
#Total successful requests:  1341
#Completed :  51.58 %
#Elapsed time:  10234.54 s
#------------------------------------------------------------------------------
#
#Response for player/50745. Successful:  <Response [200]>
#
#Total successful requests:  1342
#Completed :  51.62 %
#Elapsed time:  10247.25 s
#------------------------------------------------------------------------------
#
#Response for player/297583. Successful:  <Response [200]>
#
#Total successful requests:  1343
#Completed :  51.65 %
#Elapsed time:  10250.84 s
#------------------------------------------------------------------------------
#
#Response for player/51436. Successful:  <Response [200]>
#
#Total successful requests:  1344
#Completed :  51.69 %
#Elapsed time:  10259.47 s
#------------------------------------------------------------------------------
#
#Response for player/326637. Successful:  <Response [200]>
#
#Total successful requests:  1345
#Completed :  51.73 %
#Elapsed time:  10275.38 s
#------------------------------------------------------------------------------
#
#Response for player/7597. Successful:  <Response [200]>
#
#Total successful requests:  1346
#Completed :  51.77 %
#Elapsed time:  10276.81 s
#------------------------------------------------------------------------------
#
#Response for player/342616. Successful:  <Response [200]>
#
#Total successful requests:  1347
#Completed :  51.81 %
#Elapsed time:  10278.74 s
#------------------------------------------------------------------------------
#
#Response for player/406308. Successful:  <Response [200]>
#
#Total successful requests:  1348
#Completed :  51.85 %
#Elapsed time:  10282.29 s
#------------------------------------------------------------------------------
#
#Response for player/6126. Successful:  <Response [200]>
#
#Total successful requests:  1349
#Completed :  51.88 %
#Elapsed time:  10302.75 s
#------------------------------------------------------------------------------
#
#Response for player/698189. Successful:  <Response [200]>
#
#Total successful requests:  1350
#Completed :  51.92 %
#Elapsed time:  10304.80 s
#------------------------------------------------------------------------------
#
#Response for player/32965. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  1351
#Completed :  51.96 %
#Elapsed time:  10308.31 s
#------------------------------------------------------------------------------
#
#Response for player/43654. Successful:  <Response [200]>
#
#Total successful requests:  1352
#Completed :  52.00 %
#Elapsed time:  10326.13 s
#------------------------------------------------------------------------------
#
#Response for player/51782. Successful:  <Response [200]>
#
#Total successful requests:  1353
#Completed :  52.04 %
#Elapsed time:  10341.16 s
#------------------------------------------------------------------------------
#
#Response for player/45963. Successful:  <Response [200]>
#
#Total successful requests:  1354
#Completed :  52.08 %
#Elapsed time:  10358.70 s
#------------------------------------------------------------------------------
#
#Response for player/37714. Successful:  <Response [200]>
#
#Total successful requests:  1355
#Completed :  52.12 %
#Elapsed time:  10362.66 s
#------------------------------------------------------------------------------
#
#Response for player/23788. Successful:  <Response [200]>
#
#Total successful requests:  1356
#Completed :  52.15 %
#Elapsed time:  10373.82 s
#------------------------------------------------------------------------------
#
#Response for player/7594. Successful:  <Response [200]>
#
#Total successful requests:  1357
#Completed :  52.19 %
#Elapsed time:  10376.65 s
#------------------------------------------------------------------------------
#
#Response for player/47539. Successful:  <Response [200]>
#
#Total successful requests:  1358
#Completed :  52.23 %
#Elapsed time:  10378.96 s
#------------------------------------------------------------------------------
#
#Response for player/35933. Successful:  <Response [200]>
#
#Total successful requests:  1359
#Completed :  52.27 %
#Elapsed time:  10429.89 s
#------------------------------------------------------------------------------
#
#Response for player/499592. Successful:  <Response [200]>
#
#Total successful requests:  1360
#Completed :  52.31 %
#Elapsed time:  10432.39 s
#------------------------------------------------------------------------------
#
#Response for player/23758. Successful:  <Response [200]>
#
#Total successful requests:  1361
#Completed :  52.35 %
#Elapsed time:  10435.88 s
#------------------------------------------------------------------------------
#
#Response for player/5679. Successful:  <Response [200]>
#
#Total successful requests:  1362
#Completed :  52.38 %
#Elapsed time:  10436.70 s
#------------------------------------------------------------------------------
#
#Response for player/55610. Successful:  <Response [200]>
#
#Total successful requests:  1363
#Completed :  52.42 %
#Elapsed time:  10439.88 s
#------------------------------------------------------------------------------
#
#Response for player/23702. Successful:  <Response [200]>
#
#Total successful requests:  1364
#Completed :  52.46 %
#Elapsed time:  10445.15 s
#------------------------------------------------------------------------------
#
#Response for player/236779. Successful:  <Response [200]>
#
#Total successful requests:  1365
#Completed :  52.50 %
#Elapsed time:  10448.31 s
#------------------------------------------------------------------------------
#
#Response for player/35713. Successful:  <Response [200]>
#
#Total successful requests:  1366
#Completed :  52.54 %
#Elapsed time:  10455.55 s
#------------------------------------------------------------------------------
#
#Response for player/8487. Successful:  <Response [200]>
#
#Total successful requests:  1367
#Completed :  52.58 %
#Elapsed time:  10460.49 s
#------------------------------------------------------------------------------
#
#Response for player/472153. Successful:  <Response [200]>
#
#Total successful requests:  1368
#Completed :  52.62 %
#Elapsed time:  10462.03 s
#------------------------------------------------------------------------------
#
#Response for player/380956. Successful:  <Response [200]>
#
#Total successful requests:  1369
#Completed :  52.65 %
#Elapsed time:  10468.57 s
#------------------------------------------------------------------------------
#
#Response for player/370040. Successful:  <Response [200]>
#
#Total successful requests:  1370
#Completed :  52.69 %
#Elapsed time:  10470.69 s
#------------------------------------------------------------------------------
#
#Response for player/245287. Successful:  <Response [200]>
#
#Total successful requests:  1371
#Completed :  52.73 %
#Elapsed time:  10473.11 s
#------------------------------------------------------------------------------
#
#Response for player/37102. Successful:  <Response [200]>
#
#Total successful requests:  1372
#Completed :  52.77 %
#Elapsed time:  10475.21 s
#------------------------------------------------------------------------------
#
#Response for player/402992. Successful:  <Response [200]>
#
#Total successful requests:  1373
#Completed :  52.81 %
#Elapsed time:  10480.95 s
#------------------------------------------------------------------------------
#
#Response for player/20257. Successful:  <Response [200]>
#
#Total successful requests:  1374
#Completed :  52.85 %
#Elapsed time:  10481.68 s
#------------------------------------------------------------------------------
#
#Response for player/23760. Successful:  <Response [200]>
#
#Total successful requests:  1375
#Completed :  52.88 %
#Elapsed time:  10485.03 s
#------------------------------------------------------------------------------
#
#Response for player/39008. Successful:  <Response [200]>
#
#Total successful requests:  1376
#Completed :  52.92 %
#Elapsed time:  10487.94 s
#------------------------------------------------------------------------------
#
#Response for player/4582. Successful:  <Response [200]>
#
#Total successful requests:  1377
#Completed :  52.96 %
#Elapsed time:  10490.08 s
#------------------------------------------------------------------------------
#
#Response for player/44682. Successful:  <Response [200]>
#
#Total successful requests:  1378
#Completed :  53.00 %
#Elapsed time:  10495.83 s
#------------------------------------------------------------------------------
#
#Response for player/48996. Successful:  <Response [200]>
#
#Total successful requests:  1379
#Completed :  53.04 %
#Elapsed time:  10499.26 s
#------------------------------------------------------------------------------
#
#Response for player/446807. Successful:  <Response [200]>
#
#Total successful requests:  1380
#Completed :  53.08 %
#Elapsed time:  10501.17 s
#------------------------------------------------------------------------------
#
#Response for player/272279. Successful:  <Response [200]>
#
#Total successful requests:  1381
#Completed :  53.12 %
#Elapsed time:  10503.29 s
#------------------------------------------------------------------------------
#
#Response for player/381734. Successful:  <Response [200]>
#
#Total successful requests:  1382
#Completed :  53.15 %
#Elapsed time:  10505.44 s
#------------------------------------------------------------------------------
#
#Response for player/364300. Successful:  <Response [200]>
#
#Total successful requests:  1383
#Completed :  53.19 %
#Elapsed time:  10509.68 s
#------------------------------------------------------------------------------
#
#Response for player/414973. Successful:  <Response [200]>
#
#Total successful requests:  1384
#Completed :  53.23 %
#Elapsed time:  10514.01 s
#------------------------------------------------------------------------------
#
#Response for player/15383. Successful:  <Response [200]>
#
#Total successful requests:  1385
#Completed :  53.27 %
#Elapsed time:  10520.04 s
#------------------------------------------------------------------------------
#
#Response for player/259551. Successful:  <Response [200]>
#
#Total successful requests:  1386
#Completed :  53.31 %
#Elapsed time:  10526.48 s
#------------------------------------------------------------------------------
#
#Response for player/308515. Successful:  <Response [200]>
#
#Total successful requests:  1387
#Completed :  53.35 %
#Elapsed time:  10542.61 s
#------------------------------------------------------------------------------
#
#Response for player/410765. Successful:  <Response [200]>
#
#Total successful requests:  1388
#Completed :  53.38 %
#Elapsed time:  10546.79 s
#------------------------------------------------------------------------------
#
#Response for player/774223. Successful:  <Response [200]>
#
#Total successful requests:  1389
#Completed :  53.42 %
#Elapsed time:  10555.68 s
#------------------------------------------------------------------------------
#
#Response for player/24721. Successful:  <Response [200]>
#
#Total successful requests:  1390
#Completed :  53.46 %
#Elapsed time:  10557.24 s
#------------------------------------------------------------------------------
#
#Response for player/44465. Successful:  <Response [200]>
#
#Total successful requests:  1391
#Completed :  53.50 %
#Elapsed time:  10565.36 s
#------------------------------------------------------------------------------
#
#Response for player/55360. Successful:  <Response [200]>
#
#Total successful requests:  1392
#Completed :  53.54 %
#Elapsed time:  10567.49 s
#------------------------------------------------------------------------------
#
#Response for player/494847. Successful:  <Response [200]>
#
#Total successful requests:  1393
#Completed :  53.58 %
#Elapsed time:  10569.60 s
#------------------------------------------------------------------------------
#
#Response for player/453289. Successful:  <Response [200]>
#
#Total successful requests:  1394
#Completed :  53.62 %
#Elapsed time:  10578.22 s
#------------------------------------------------------------------------------
#
#Response for player/24923. Successful:  <Response [200]>
#
#Total successful requests:  1395
#Completed :  53.65 %
#Elapsed time:  10579.74 s
#------------------------------------------------------------------------------
#
#Response for player/24230. Successful:  <Response [200]>
#
#Total successful requests:  1396
#Completed :  53.69 %
#Elapsed time:  10602.83 s
#------------------------------------------------------------------------------
#
#Response for player/38129. Successful:  <Response [200]>
#
#Total successful requests:  1397
#Completed :  53.73 %
#Elapsed time:  10614.22 s
#------------------------------------------------------------------------------
#
#Response for player/319746. Successful:  <Response [200]>
#
#Total successful requests:  1398
#Completed :  53.77 %
#Elapsed time:  10626.91 s
#------------------------------------------------------------------------------
#
#Response for player/633426. Successful:  <Response [200]>
#
#Total successful requests:  1399
#Completed :  53.81 %
#Elapsed time:  10629.02 s
#------------------------------------------------------------------------------
#
#Response for player/43919. Successful:  <Response [200]>
#
#Total successful requests:  1400
#Completed :  53.85 %
#Elapsed time:  10635.94 s
#------------------------------------------------------------------------------
#
#Response for page 8 Successful:  <Response [200]> 	=>
#

#list of players:  200
#Response for player/440963. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  1401
#Completed :  53.88 %
#Elapsed time:  10681.31 s
#------------------------------------------------------------------------------
#
#Response for player/38986. Successful:  <Response [200]>
#
#Total successful requests:  1402
#Completed :  53.92 %
#Elapsed time:  10684.24 s
#------------------------------------------------------------------------------
#
#Response for player/4208. Successful:  <Response [200]>
#
#Total successful requests:  1403
#Completed :  53.96 %
#Elapsed time:  10697.91 s
#------------------------------------------------------------------------------
#
#Response for player/279531. Successful:  <Response [200]>
#
#Total successful requests:  1404
#Completed :  54.00 %
#Elapsed time:  10703.23 s
#------------------------------------------------------------------------------
#
#Response for player/51218. Successful:  <Response [200]>
#
#Total successful requests:  1405
#Completed :  54.04 %
#Elapsed time:  10704.81 s
#------------------------------------------------------------------------------
#
#Response for player/52294. Successful:  <Response [200]>
#
#Total successful requests:  1406
#Completed :  54.08 %
#Elapsed time:  10708.35 s
#------------------------------------------------------------------------------
#
#Response for player/38124. Successful:  <Response [200]>
#
#Total successful requests:  1407
#Completed :  54.12 %
#Elapsed time:  10710.64 s
#------------------------------------------------------------------------------
#
#Response for player/42607. Successful:  <Response [200]>
#
#Total successful requests:  1408
#Completed :  54.15 %
#Elapsed time:  10711.44 s
#------------------------------------------------------------------------------
#
#Response for player/52061. Successful:  <Response [200]>
#
#Total successful requests:  1409
#Completed :  54.19 %
#Elapsed time:  10719.48 s
#------------------------------------------------------------------------------
#
#Response for player/212175. Successful:  <Response [200]>
#
#Total successful requests:  1410
#Completed :  54.23 %
#Elapsed time:  10723.91 s
#------------------------------------------------------------------------------
#
#Response for player/52928. Successful:  <Response [200]>
#
#Total successful requests:  1411
#Completed :  54.27 %
#Elapsed time:  10725.56 s
#------------------------------------------------------------------------------
#
#Response for player/784379. Successful:  <Response [200]>
#
#Total successful requests:  1412
#Completed :  54.31 %
#Elapsed time:  10727.55 s
#------------------------------------------------------------------------------
#
#Response for player/25471. Successful:  <Response [200]>
#
#Total successful requests:  1413
#Completed :  54.35 %
#Elapsed time:  10733.18 s
#------------------------------------------------------------------------------
#
#Response for player/37770. Successful:  <Response [200]>
#
#Total successful requests:  1414
#Completed :  54.38 %
#Elapsed time:  10734.56 s
#------------------------------------------------------------------------------
#
#Response for player/25434. Successful:  <Response [200]>
#
#Total successful requests:  1415
#Completed :  54.42 %
#Elapsed time:  10739.31 s
#------------------------------------------------------------------------------
#
#Response for player/39038. Successful:  <Response [200]>
#
#Total successful requests:  1416
#Completed :  54.46 %
#Elapsed time:  10746.48 s
#------------------------------------------------------------------------------
#
#Response for player/48120. Successful:  <Response [200]>
#
#Total successful requests:  1417
#Completed :  54.50 %
#Elapsed time:  10750.15 s
#------------------------------------------------------------------------------
#
#Response for player/36608. Successful:  <Response [200]>
#
#Total successful requests:  1418
#Completed :  54.54 %
#Elapsed time:  10757.12 s
#------------------------------------------------------------------------------
#
#Response for player/51487. Successful:  <Response [200]>
#
#Total successful requests:  1419
#Completed :  54.58 %
#Elapsed time:  10760.02 s
#------------------------------------------------------------------------------
#
#Response for player/332978. Successful:  <Response [200]>
#
#Total successful requests:  1420
#Completed :  54.62 %
#Elapsed time:  10767.36 s
#------------------------------------------------------------------------------
#
#Response for player/56102. Successful:  <Response [200]>
#
#Total successful requests:  1421
#Completed :  54.65 %
#Elapsed time:  10774.40 s
#------------------------------------------------------------------------------
#
#Response for player/559066. Successful:  <Response [200]>
#
#Total successful requests:  1422
#Completed :  54.69 %
#Elapsed time:  10785.70 s
#------------------------------------------------------------------------------
#
#Response for player/25533. Successful:  <Response [200]>
#
#Total successful requests:  1423
#Completed :  54.73 %
#Elapsed time:  10790.41 s
#------------------------------------------------------------------------------
#
#Response for player/1057456. Successful:  <Response [200]>
#
#Total successful requests:  1424
#Completed :  54.77 %
#Elapsed time:  10799.34 s
#------------------------------------------------------------------------------
#
#Response for player/56209. Successful:  <Response [200]>
#
#Total successful requests:  1425
#Completed :  54.81 %
#Elapsed time:  10808.36 s
#------------------------------------------------------------------------------
#
#Response for player/364788. Successful:  <Response [200]>
#
#Total successful requests:  1426
#Completed :  54.85 %
#Elapsed time:  10809.74 s
#------------------------------------------------------------------------------
#
#Response for player/37237. Successful:  <Response [200]>
#
#Total successful requests:  1427
#Completed :  54.88 %
#Elapsed time:  10813.11 s
#------------------------------------------------------------------------------
#
#Response for player/16352. Successful:  <Response [200]>
#
#Total successful requests:  1428
#Completed :  54.92 %
#Elapsed time:  10820.91 s
#------------------------------------------------------------------------------
#
#Response for player/24706. Successful:  <Response [200]>
#
#Total successful requests:  1429
#Completed :  54.96 %
#Elapsed time:  10833.44 s
#------------------------------------------------------------------------------
#
#Response for player/52670. Successful:  <Response [200]>
#
#Total successful requests:  1430
#Completed :  55.00 %
#Elapsed time:  10854.82 s
#------------------------------------------------------------------------------
#
#Response for player/42648. Successful:  <Response [200]>
#
#Total successful requests:  1431
#Completed :  55.04 %
#Elapsed time:  10856.22 s
#------------------------------------------------------------------------------
#
#Response for player/937673. Successful:  <Response [200]>
#
#Total successful requests:  1432
#Completed :  55.08 %
#Elapsed time:  10878.38 s
#------------------------------------------------------------------------------
#
#Response for player/47239. Successful:  <Response [200]>
#
#Total successful requests:  1433
#Completed :  55.12 %
#Elapsed time:  10879.86 s
#------------------------------------------------------------------------------
#
#Response for player/315051. Successful:  <Response [200]>
#
#Total successful requests:  1434
#Completed :  55.15 %
#Elapsed time:  10890.20 s
#------------------------------------------------------------------------------
#
#Response for player/38759. Successful:  <Response [200]>
#
#Total successful requests:  1435
#Completed :  55.19 %
#Elapsed time:  10911.86 s
#------------------------------------------------------------------------------
#
#Response for player/36308. Successful:  <Response [200]>
#
#Total successful requests:  1436
#Completed :  55.23 %
#Elapsed time:  10912.84 s
#------------------------------------------------------------------------------
#
#Response for player/216811. Successful:  <Response [200]>
#
#Total successful requests:  1437
#Completed :  55.27 %
#Elapsed time:  10914.93 s
#------------------------------------------------------------------------------
#
#Response for player/51477. Successful:  <Response [200]>
#
#Total successful requests:  1438
#Completed :  55.31 %
#Elapsed time:  10916.13 s
#------------------------------------------------------------------------------
#
#Response for player/40383. Successful:  <Response [200]>
#
#Total successful requests:  1439
#Completed :  55.35 %
#Elapsed time:  10917.75 s
#------------------------------------------------------------------------------
#
#Response for player/15468. Successful:  <Response [200]>
#
#Total successful requests:  1440
#Completed :  55.38 %
#Elapsed time:  10920.28 s
#------------------------------------------------------------------------------
#
#Response for player/52428. Successful:  <Response [200]>
#
#Total successful requests:  1441
#Completed :  55.42 %
#Elapsed time:  10928.56 s
#------------------------------------------------------------------------------
#
#Response for player/313526. Successful:  <Response [200]>
#
#Total successful requests:  1442
#Completed :  55.46 %
#Elapsed time:  10936.44 s
#------------------------------------------------------------------------------
#
#Response for player/26826. Successful:  <Response [200]>
#
#Total successful requests:  1443
#Completed :  55.50 %
#Elapsed time:  10940.16 s
#------------------------------------------------------------------------------
#
#Response for player/55896. Successful:  <Response [200]>
#
#Total successful requests:  1444
#Completed :  55.54 %
#Elapsed time:  10942.26 s
#------------------------------------------------------------------------------
#
#Response for player/245397. Successful:  <Response [200]>
#
#Total successful requests:  1445
#Completed :  55.58 %
#Elapsed time:  10950.28 s
#------------------------------------------------------------------------------
#
#Response for player/298197. Successful:  <Response [200]>
#
#Total successful requests:  1446
#Completed :  55.62 %
#Elapsed time:  10974.15 s
#------------------------------------------------------------------------------
#
#Response for player/9329. Successful:  <Response [200]>
#
#Total successful requests:  1447
#Completed :  55.65 %
#Elapsed time:  10975.06 s
#------------------------------------------------------------------------------
#
#Response for player/493773. Successful:  <Response [200]>
#
#Total successful requests:  1448
#Completed :  55.69 %
#Elapsed time:  10977.87 s
#------------------------------------------------------------------------------
#
#Response for player/943275. Successful:  <Response [200]>
#
#Total successful requests:  1449
#Completed :  55.73 %
#Elapsed time:  10979.48 s
#------------------------------------------------------------------------------
#
#Response for player/55597. Successful:  <Response [200]>
#
#Total successful requests:  1450
#Completed :  55.77 %
#Elapsed time:  10983.52 s
#------------------------------------------------------------------------------
#
#Response for player/297524. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  1451
#Completed :  55.81 %
#Elapsed time:  10986.07 s
#------------------------------------------------------------------------------
#
#Response for player/779973. Successful:  <Response [200]>
#
#Total successful requests:  1452
#Completed :  55.85 %
#Elapsed time:  11021.92 s
#------------------------------------------------------------------------------
#
#Response for player/24804. Successful:  <Response [200]>
#
#Total successful requests:  1453
#Completed :  55.88 %
#Elapsed time:  11027.73 s
#------------------------------------------------------------------------------
#
#Response for player/440523. Successful:  <Response [200]>
#
#Total successful requests:  1454
#Completed :  55.92 %
#Elapsed time:  11043.81 s
#------------------------------------------------------------------------------
#
#Response for player/8449. Successful:  <Response [200]>
#
#Total successful requests:  1455
#Completed :  55.96 %
#Elapsed time:  11046.05 s
#------------------------------------------------------------------------------
#
#Response for player/51229. Successful:  <Response [200]>
#
#Total successful requests:  1456
#Completed :  56.00 %
#Elapsed time:  11048.87 s
#------------------------------------------------------------------------------
#
#Response for player/55880. Successful:  <Response [200]>
#
#Total successful requests:  1457
#Completed :  56.04 %
#Elapsed time:  11050.32 s
#------------------------------------------------------------------------------
#
#Response for player/23950. Successful:  <Response [200]>
#
#Total successful requests:  1458
#Completed :  56.08 %
#Elapsed time:  11054.41 s
#------------------------------------------------------------------------------
#
#Response for player/330902. Successful:  <Response [200]>
#
#Total successful requests:  1459
#Completed :  56.12 %
#Elapsed time:  11057.80 s
#------------------------------------------------------------------------------
#
#Response for player/25109. Successful:  <Response [200]>
#
#Total successful requests:  1460
#Completed :  56.15 %
#Elapsed time:  11059.44 s
#------------------------------------------------------------------------------
#
#Response for player/459508. Successful:  <Response [200]>
#
#Total successful requests:  1461
#Completed :  56.19 %
#Elapsed time:  11064.67 s
#------------------------------------------------------------------------------
#
#Response for player/24298. Successful:  <Response [200]>
#
#Total successful requests:  1462
#Completed :  56.23 %
#Elapsed time:  11072.61 s
#------------------------------------------------------------------------------
#
#Response for player/16260. Successful:  <Response [200]>
#
#Total successful requests:  1463
#Completed :  56.27 %
#Elapsed time:  11096.78 s
#------------------------------------------------------------------------------
#
#Response for player/308418. Successful:  <Response [200]>
#
#Total successful requests:  1464
#Completed :  56.31 %
#Elapsed time:  11099.38 s
#------------------------------------------------------------------------------
#
#Response for player/42664. Successful:  <Response [200]>
#
#Total successful requests:  1465
#Completed :  56.35 %
#Elapsed time:  11103.17 s
#------------------------------------------------------------------------------
#
#Response for player/47666. Successful:  <Response [200]>
#
#Total successful requests:  1466
#Completed :  56.38 %
#Elapsed time:  11104.78 s
#------------------------------------------------------------------------------
#
#Response for player/36833. Successful:  <Response [200]>
#
#Total successful requests:  1467
#Completed :  56.42 %
#Elapsed time:  11127.24 s
#------------------------------------------------------------------------------
#
#Response for player/28671. Successful:  <Response [200]>
#
#Total successful requests:  1468
#Completed :  56.46 %
#Elapsed time:  11141.31 s
#------------------------------------------------------------------------------
#
#Response for player/55643. Successful:  <Response [200]>
#
#Total successful requests:  1469
#Completed :  56.50 %
#Elapsed time:  11151.10 s
#------------------------------------------------------------------------------
#
#Response for player/46724. Successful:  <Response [200]>
#
#Total successful requests:  1470
#Completed :  56.54 %
#Elapsed time:  11152.57 s
#------------------------------------------------------------------------------
#
#Response for player/55740. Successful:  <Response [200]>
#
#Total successful requests:  1471
#Completed :  56.58 %
#Elapsed time:  11158.55 s
#------------------------------------------------------------------------------
#
#Response for player/50242. Successful:  <Response [200]>
#
#Total successful requests:  1472
#Completed :  56.62 %
#Elapsed time:  11162.59 s
#------------------------------------------------------------------------------
#
#Response for player/585100. Successful:  <Response [200]>
#
#Total successful requests:  1473
#Completed :  56.65 %
#Elapsed time:  11164.17 s
#------------------------------------------------------------------------------
#
#Response for player/25591. Successful:  <Response [200]>
#
#Total successful requests:  1474
#Completed :  56.69 %
#Elapsed time:  11167.63 s
#------------------------------------------------------------------------------
#
#Response for player/4527. Successful:  <Response [200]>
#
#Total successful requests:  1475
#Completed :  56.73 %
#Elapsed time:  11174.02 s
#------------------------------------------------------------------------------
#
#Response for player/15461. Successful:  <Response [200]>
#
#Total successful requests:  1476
#Completed :  56.77 %
#Elapsed time:  11182.43 s
#------------------------------------------------------------------------------
#
#Response for player/15876. Successful:  <Response [200]>
#
#Total successful requests:  1477
#Completed :  56.81 %
#Elapsed time:  11184.90 s
#------------------------------------------------------------------------------
#
#Response for player/37707. Successful:  <Response [200]>
#
#Total successful requests:  1478
#Completed :  56.85 %
#Elapsed time:  11186.26 s
#------------------------------------------------------------------------------
#
#Response for player/41440. Successful:  <Response [200]>
#
#Total successful requests:  1479
#Completed :  56.88 %
#Elapsed time:  11188.21 s
#------------------------------------------------------------------------------
#
#Response for player/32192. Successful:  <Response [200]>
#
#Total successful requests:  1480
#Completed :  56.92 %
#Elapsed time:  11196.64 s
#------------------------------------------------------------------------------
#
#Response for player/52922. Successful:  <Response [200]>
#
#Total successful requests:  1481
#Completed :  56.96 %
#Elapsed time:  11207.83 s
#------------------------------------------------------------------------------
#
#Response for player/23972. Successful:  <Response [200]>
#
#Total successful requests:  1482
#Completed :  57.00 %
#Elapsed time:  11212.93 s
#------------------------------------------------------------------------------
#
#Response for player/35656. Successful:  <Response [200]>
#
#Total successful requests:  1483
#Completed :  57.04 %
#Elapsed time:  11221.43 s
#------------------------------------------------------------------------------
#
#Response for player/230371. Successful:  <Response [200]>
#
#Total successful requests:  1484
#Completed :  57.08 %
#Elapsed time:  11225.35 s
#------------------------------------------------------------------------------
#
#Response for player/40305. Successful:  <Response [200]>
#
#Total successful requests:  1485
#Completed :  57.12 %
#Elapsed time:  11238.82 s
#------------------------------------------------------------------------------
#
#Response for player/55965. Successful:  <Response [200]>
#
#Total successful requests:  1486
#Completed :  57.15 %
#Elapsed time:  11246.34 s
#------------------------------------------------------------------------------
#
#Response for player/55968. Successful:  <Response [200]>
#
#Total successful requests:  1487
#Completed :  57.19 %
#Elapsed time:  11251.27 s
#------------------------------------------------------------------------------
#
#Response for player/571703. Successful:  <Response [200]>
#
#Total successful requests:  1488
#Completed :  57.23 %
#Elapsed time:  11258.29 s
#------------------------------------------------------------------------------
#
#Response for player/55986. Successful:  <Response [200]>
#
#Total successful requests:  1489
#Completed :  57.27 %
#Elapsed time:  11260.06 s
#------------------------------------------------------------------------------
#
#Response for player/49769. Successful:  <Response [200]>
#
#Total successful requests:  1490
#Completed :  57.31 %
#Elapsed time:  11277.24 s
#------------------------------------------------------------------------------
#
#Response for player/633362. Successful:  <Response [200]>
#
#Total successful requests:  1491
#Completed :  57.35 %
#Elapsed time:  11287.88 s
#------------------------------------------------------------------------------
#
#Response for player/22149. Successful:  <Response [200]>
#
#Total successful requests:  1492
#Completed :  57.38 %
#Elapsed time:  11289.76 s
#------------------------------------------------------------------------------
#
#Response for player/315586. Successful:  <Response [200]>
#
#Total successful requests:  1493
#Completed :  57.42 %
#Elapsed time:  11291.53 s
#------------------------------------------------------------------------------
#
#Response for player/8244. Successful:  <Response [200]>
#
#Total successful requests:  1494
#Completed :  57.46 %
#Elapsed time:  11294.11 s
#------------------------------------------------------------------------------
#
#Response for player/25409. Successful:  <Response [200]>
#
#Total successful requests:  1495
#Completed :  57.50 %
#Elapsed time:  11298.23 s
#------------------------------------------------------------------------------
#
#Response for player/36632. Successful:  <Response [200]>
#
#Total successful requests:  1496
#Completed :  57.54 %
#Elapsed time:  11304.66 s
#------------------------------------------------------------------------------
#
#Response for player/806239. Successful:  <Response [200]>
#
#Total successful requests:  1497
#Completed :  57.58 %
#Elapsed time:  11306.56 s
#------------------------------------------------------------------------------
#
#Response for player/10843. Successful:  <Response [200]>
#
#Total successful requests:  1498
#Completed :  57.62 %
#Elapsed time:  11309.03 s
#------------------------------------------------------------------------------
#
#Response for player/28146. Successful:  <Response [200]>
#
#Total successful requests:  1499
#Completed :  57.65 %
#Elapsed time:  11310.74 s
#------------------------------------------------------------------------------
#
#Response for player/51898. Successful:  <Response [200]>
#
#Total successful requests:  1500
#Completed :  57.69 %
#Elapsed time:  11323.48 s
#------------------------------------------------------------------------------
#
#Response for player/310958. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  1501
#Completed :  57.73 %
#Elapsed time:  11328.02 s
#------------------------------------------------------------------------------
#
#Response for player/32540. Successful:  <Response [200]>
#
#Total successful requests:  1502
#Completed :  57.77 %
#Elapsed time:  11345.03 s
#------------------------------------------------------------------------------
#
#Response for player/33816. Successful:  <Response [200]>
#
#Total successful requests:  1503
#Completed :  57.81 %
#Elapsed time:  11346.73 s
#------------------------------------------------------------------------------
#
#Response for player/4508. Successful:  <Response [200]>
#
#Total successful requests:  1504
#Completed :  57.85 %
#Elapsed time:  11350.19 s
#------------------------------------------------------------------------------
#
#Response for player/24875. Successful:  <Response [200]>
#
#Total successful requests:  1505
#Completed :  57.88 %
#Elapsed time:  11358.31 s
#------------------------------------------------------------------------------
#
#Response for player/55485. Successful:  <Response [200]>
#
#Total successful requests:  1506
#Completed :  57.92 %
#Elapsed time:  11360.45 s
#------------------------------------------------------------------------------
#
#Response for player/37251. Successful:  <Response [200]>
#
#Total successful requests:  1507
#Completed :  57.96 %
#Elapsed time:  11362.27 s
#------------------------------------------------------------------------------
#
#Response for player/16281. Successful:  <Response [200]>
#
#Total successful requests:  1508
#Completed :  58.00 %
#Elapsed time:  11365.51 s
#------------------------------------------------------------------------------
#
#Response for player/32257. Successful:  <Response [200]>
#
#Total successful requests:  1509
#Completed :  58.04 %
#Elapsed time:  11366.63 s
#------------------------------------------------------------------------------
#
#Response for player/272262. Successful:  <Response [200]>
#
#Total successful requests:  1510
#Completed :  58.08 %
#Elapsed time:  11368.02 s
#------------------------------------------------------------------------------
#
#Response for player/25115. Successful:  <Response [200]>
#
#Total successful requests:  1511
#Completed :  58.12 %
#Elapsed time:  11375.01 s
#------------------------------------------------------------------------------
#
#Response for player/21650. Successful:  <Response [200]>
#
#Total successful requests:  1512
#Completed :  58.15 %
#Elapsed time:  11376.75 s
#------------------------------------------------------------------------------
#
#Response for player/43751. Successful:  <Response [200]>
#
#Total successful requests:  1513
#Completed :  58.19 %
#Elapsed time:  11378.28 s
#------------------------------------------------------------------------------
#
#Response for player/26853. Successful:  <Response [200]>
#
#Total successful requests:  1514
#Completed :  58.23 %
#Elapsed time:  11391.12 s
#------------------------------------------------------------------------------
#
#Response for player/10754. Successful:  <Response [200]>
#
#Total successful requests:  1515
#Completed :  58.27 %
#Elapsed time:  11392.87 s
#------------------------------------------------------------------------------
#
#Response for player/51639. Successful:  <Response [200]>
#
#Total successful requests:  1516
#Completed :  58.31 %
#Elapsed time:  11394.15 s
#------------------------------------------------------------------------------
#
#Response for player/28770. Successful:  <Response [200]>
#
#Total successful requests:  1517
#Completed :  58.35 %
#Elapsed time:  11401.63 s
#------------------------------------------------------------------------------
#
#Response for player/313430. Successful:  <Response [200]>
#
#Total successful requests:  1518
#Completed :  58.38 %
#Elapsed time:  11404.88 s
#------------------------------------------------------------------------------
#
#Response for player/30923. Successful:  <Response [200]>
#
#Total successful requests:  1519
#Completed :  58.42 %
#Elapsed time:  11407.10 s
#------------------------------------------------------------------------------
#
#Response for player/293031. Successful:  <Response [200]>
#
#Total successful requests:  1520
#Completed :  58.46 %
#Elapsed time:  11409.36 s
#------------------------------------------------------------------------------
#
#Response for player/50245. Successful:  <Response [200]>
#
#Total successful requests:  1521
#Completed :  58.50 %
#Elapsed time:  11411.26 s
#------------------------------------------------------------------------------
#
#Response for player/7319. Successful:  <Response [200]>
#
#Total successful requests:  1522
#Completed :  58.54 %
#Elapsed time:  11414.10 s
#------------------------------------------------------------------------------
#
#Response for player/38252. Successful:  <Response [200]>
#
#Total successful requests:  1523
#Completed :  58.58 %
#Elapsed time:  11423.53 s
#------------------------------------------------------------------------------
#
#Response for player/24888. Successful:  <Response [200]>
#
#Total successful requests:  1524
#Completed :  58.62 %
#Elapsed time:  11428.05 s
#------------------------------------------------------------------------------
#
#Response for player/35390. Successful:  <Response [200]>
#
#Total successful requests:  1525
#Completed :  58.65 %
#Elapsed time:  11439.40 s
#------------------------------------------------------------------------------
#
#Response for player/50791. Successful:  <Response [200]>
#
#Total successful requests:  1526
#Completed :  58.69 %
#Elapsed time:  11444.91 s
#------------------------------------------------------------------------------
#
#Response for player/56268. Successful:  <Response [200]>
#
#Total successful requests:  1527
#Completed :  58.73 %
#Elapsed time:  11446.92 s
#------------------------------------------------------------------------------
#
#Response for player/8566. Successful:  <Response [200]>
#
#Total successful requests:  1528
#Completed :  58.77 %
#Elapsed time:  11448.87 s
#------------------------------------------------------------------------------
#
#Response for player/14024. Successful:  <Response [200]>
#
#Total successful requests:  1529
#Completed :  58.81 %
#Elapsed time:  11449.79 s
#------------------------------------------------------------------------------
#
#Response for player/5779. Successful:  <Response [200]>
#
#Total successful requests:  1530
#Completed :  58.85 %
#Elapsed time:  11462.26 s
#------------------------------------------------------------------------------
#
#Response for player/429981. Successful:  <Response [200]>
#
#Total successful requests:  1531
#Completed :  58.88 %
#Elapsed time:  11475.07 s
#------------------------------------------------------------------------------
#
#Response for player/46790. Successful:  <Response [200]>
#
#Total successful requests:  1532
#Completed :  58.92 %
#Elapsed time:  11485.77 s
#------------------------------------------------------------------------------
#
#Response for player/47255. Successful:  <Response [200]>
#
#Total successful requests:  1533
#Completed :  58.96 %
#Elapsed time:  11493.55 s
#------------------------------------------------------------------------------
#
#Response for player/50809. Successful:  <Response [200]>
#
#Total successful requests:  1534
#Completed :  59.00 %
#Elapsed time:  11494.67 s
#------------------------------------------------------------------------------
#
#Response for player/22392. Successful:  <Response [200]>
#
#Total successful requests:  1535
#Completed :  59.04 %
#Elapsed time:  11526.90 s
#------------------------------------------------------------------------------
#
#Response for player/43692. Successful:  <Response [200]>
#
#Total successful requests:  1536
#Completed :  59.08 %
#Elapsed time:  11530.87 s
#------------------------------------------------------------------------------
#
#Response for player/384525. Successful:  <Response [200]>
#
#Total successful requests:  1537
#Completed :  59.12 %
#Elapsed time:  11532.11 s
#------------------------------------------------------------------------------
#
#Response for player/43860. Successful:  <Response [200]>
#
#Total successful requests:  1538
#Completed :  59.15 %
#Elapsed time:  11542.34 s
#------------------------------------------------------------------------------
#
#Response for player/23848. Successful:  <Response [200]>
#
#Total successful requests:  1539
#Completed :  59.19 %
#Elapsed time:  11544.41 s
#------------------------------------------------------------------------------
#
#Response for player/23768. Successful:  <Response [200]>
#
#Total successful requests:  1540
#Completed :  59.23 %
#Elapsed time:  11547.90 s
#------------------------------------------------------------------------------
#
#Response for player/40170. Successful:  <Response [200]>
#
#Total successful requests:  1541
#Completed :  59.27 %
#Elapsed time:  11552.65 s
#------------------------------------------------------------------------------
#
#Response for player/48804. Successful:  <Response [200]>
#
#Total successful requests:  1542
#Completed :  59.31 %
#Elapsed time:  11558.03 s
#------------------------------------------------------------------------------
#
#Response for player/34211. Successful:  <Response [200]>
#
#Total successful requests:  1543
#Completed :  59.35 %
#Elapsed time:  11558.66 s
#------------------------------------------------------------------------------
#
#Response for player/38737. Successful:  <Response [200]>
#
#Total successful requests:  1544
#Completed :  59.38 %
#Elapsed time:  11561.06 s
#------------------------------------------------------------------------------
#
#Response for player/23956. Successful:  <Response [200]>
#
#Total successful requests:  1545
#Completed :  59.42 %
#Elapsed time:  11561.77 s
#------------------------------------------------------------------------------
#
#Response for player/55633. Successful:  <Response [200]>
#
#Total successful requests:  1546
#Completed :  59.46 %
#Elapsed time:  11573.15 s
#------------------------------------------------------------------------------
#
#Response for player/398439. Successful:  <Response [200]>
#
#Total successful requests:  1547
#Completed :  59.50 %
#Elapsed time:  11581.72 s
#------------------------------------------------------------------------------
#
#Response for player/542023. Successful:  <Response [200]>
#
#Total successful requests:  1548
#Completed :  59.54 %
#Elapsed time:  11583.66 s
#------------------------------------------------------------------------------
#
#Response for player/55666. Successful:  <Response [200]>
#
#Total successful requests:  1549
#Completed :  59.58 %
#Elapsed time:  11586.23 s
#------------------------------------------------------------------------------
#
#Response for player/32130. Successful:  <Response [200]>
#
#Total successful requests:  1550
#Completed :  59.62 %
#Elapsed time:  11587.78 s
#------------------------------------------------------------------------------
#
#Response for player/7314. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  1551
#Completed :  59.65 %
#Elapsed time:  11594.77 s
#------------------------------------------------------------------------------
#
#Response for player/208252. Successful:  <Response [200]>
#
#Total successful requests:  1552
#Completed :  59.69 %
#Elapsed time:  11598.51 s
#------------------------------------------------------------------------------
#
#Response for player/39021. Successful:  <Response [200]>
#
#Total successful requests:  1553
#Completed :  59.73 %
#Elapsed time:  11603.72 s
#------------------------------------------------------------------------------
#
#Response for player/24794. Successful:  <Response [200]>
#
#Total successful requests:  1554
#Completed :  59.77 %
#Elapsed time:  11608.50 s
#------------------------------------------------------------------------------
#
#Response for player/52439. Successful:  <Response [200]>
#
#Total successful requests:  1555
#Completed :  59.81 %
#Elapsed time:  11618.52 s
#------------------------------------------------------------------------------
#
#Response for player/7366. Successful:  <Response [200]>
#
#Total successful requests:  1556
#Completed :  59.85 %
#Elapsed time:  11627.61 s
#------------------------------------------------------------------------------
#
#Response for player/23856. Successful:  <Response [200]>
#
#Total successful requests:  1557
#Completed :  59.88 %
#Elapsed time:  11631.09 s
#------------------------------------------------------------------------------
#
#Response for player/38753. Successful:  <Response [200]>
#
#Total successful requests:  1558
#Completed :  59.92 %
#Elapsed time:  11641.94 s
#------------------------------------------------------------------------------
#
#Response for player/351588. Successful:  <Response [200]>
#
#Total successful requests:  1559
#Completed :  59.96 %
#Elapsed time:  11652.12 s
#------------------------------------------------------------------------------
#
#Response for player/36310. Successful:  <Response [200]>
#
#Total successful requests:  1560
#Completed :  60.00 %
#Elapsed time:  11661.49 s
#------------------------------------------------------------------------------
#
#Response for player/23854. Successful:  <Response [200]>
#
#Total successful requests:  1561
#Completed :  60.04 %
#Elapsed time:  11671.41 s
#------------------------------------------------------------------------------
#
#Response for player/55897. Successful:  <Response [200]>
#
#Total successful requests:  1562
#Completed :  60.08 %
#Elapsed time:  11674.10 s
#------------------------------------------------------------------------------
#
#Response for player/30938. Successful:  <Response [200]>
#
#Total successful requests:  1563
#Completed :  60.12 %
#Elapsed time:  11674.88 s
#------------------------------------------------------------------------------
#
#Response for player/463215. Successful:  <Response [200]>
#
#Total successful requests:  1564
#Completed :  60.15 %
#Elapsed time:  11684.19 s
#------------------------------------------------------------------------------
#
#Response for player/52671. Successful:  <Response [200]>
#
#Total successful requests:  1565
#Completed :  60.19 %
#Elapsed time:  11704.01 s
#------------------------------------------------------------------------------
#
#Response for player/25541. Successful:  <Response [200]>
#
#Total successful requests:  1566
#Completed :  60.23 %
#Elapsed time:  11706.72 s
#------------------------------------------------------------------------------
#
#Response for player/34274. Successful:  <Response [200]>
#
#Total successful requests:  1567
#Completed :  60.27 %
#Elapsed time:  11717.70 s
#------------------------------------------------------------------------------
#
#Response for player/298195. Successful:  <Response [200]>
#
#Total successful requests:  1568
#Completed :  60.31 %
#Elapsed time:  11742.81 s
#------------------------------------------------------------------------------
#
#Response for player/51235. Successful:  <Response [200]>
#
#Total successful requests:  1569
#Completed :  60.35 %
#Elapsed time:  11744.86 s
#------------------------------------------------------------------------------
#
#Response for player/55889. Successful:  <Response [200]>
#
#Total successful requests:  1570
#Completed :  60.38 %
#Elapsed time:  11746.43 s
#------------------------------------------------------------------------------
#
#Response for player/48967. Successful:  <Response [200]>
#
#Total successful requests:  1571
#Completed :  60.42 %
#Elapsed time:  11753.36 s
#------------------------------------------------------------------------------
#
#Response for player/30030. Successful:  <Response [200]>
#
#Total successful requests:  1572
#Completed :  60.46 %
#Elapsed time:  11754.29 s
#------------------------------------------------------------------------------
#
#Response for player/31107. Successful:  <Response [200]>
#
#Total successful requests:  1573
#Completed :  60.50 %
#Elapsed time:  11761.74 s
#------------------------------------------------------------------------------
#
#Response for player/626111. Successful:  <Response [200]>
#
#Total successful requests:  1574
#Completed :  60.54 %
#Elapsed time:  11762.55 s
#------------------------------------------------------------------------------
#
#Response for player/20206. Successful:  <Response [200]>
#
#Total successful requests:  1575
#Completed :  60.58 %
#Elapsed time:  11770.43 s
#------------------------------------------------------------------------------
#
#Response for player/20363. Successful:  <Response [200]>
#
#Total successful requests:  1576
#Completed :  60.62 %
#Elapsed time:  11776.15 s
#------------------------------------------------------------------------------
#
#Response for player/24846. Successful:  <Response [200]>
#
#Total successful requests:  1577
#Completed :  60.65 %
#Elapsed time:  11778.37 s
#------------------------------------------------------------------------------
#
#Response for player/56255. Successful:  <Response [200]>
#
#Total successful requests:  1578
#Completed :  60.69 %
#Elapsed time:  11783.01 s
#------------------------------------------------------------------------------
#
#Response for player/39026. Successful:  <Response [200]>
#
#Total successful requests:  1579
#Completed :  60.73 %
#Elapsed time:  11785.85 s
#------------------------------------------------------------------------------
#
#Response for player/245288. Successful:  <Response [200]>
#
#Total successful requests:  1580
#Completed :  60.77 %
#Elapsed time:  11795.72 s
#------------------------------------------------------------------------------
#
#Response for player/5396. Successful:  <Response [200]>
#
#Total successful requests:  1581
#Completed :  60.81 %
#Elapsed time:  11805.09 s
#------------------------------------------------------------------------------
#
#Response for player/6460. Successful:  <Response [200]>
#
#Total successful requests:  1582
#Completed :  60.85 %
#Elapsed time:  11806.76 s
#------------------------------------------------------------------------------
#
#Response for player/272465. Successful:  <Response [200]>
#
#Total successful requests:  1583
#Completed :  60.88 %
#Elapsed time:  11810.36 s
#------------------------------------------------------------------------------
#
#Response for player/38251. Successful:  <Response [200]>
#
#Total successful requests:  1584
#Completed :  60.92 %
#Elapsed time:  11815.47 s
#------------------------------------------------------------------------------
#
#Response for player/12877. Successful:  <Response [200]>
#
#Total successful requests:  1585
#Completed :  60.96 %
#Elapsed time:  11818.79 s
#------------------------------------------------------------------------------
#
#Response for player/5629. Successful:  <Response [200]>
#
#Total successful requests:  1586
#Completed :  61.00 %
#Elapsed time:  11830.67 s
#------------------------------------------------------------------------------
#
#Response for player/37263. Successful:  <Response [200]>
#
#Total successful requests:  1587
#Completed :  61.04 %
#Elapsed time:  11836.72 s
#------------------------------------------------------------------------------
#
#Response for player/23961. Successful:  <Response [200]>
#
#Total successful requests:  1588
#Completed :  61.08 %
#Elapsed time:  11854.59 s
#------------------------------------------------------------------------------
#
#Response for player/974109. Successful:  <Response [200]>
#
#Total successful requests:  1589
#Completed :  61.12 %
#Elapsed time:  11858.22 s
#------------------------------------------------------------------------------
#
#Response for player/279810. Successful:  <Response [200]>
#
#Total successful requests:  1590
#Completed :  61.15 %
#Elapsed time:  11863.75 s
#------------------------------------------------------------------------------
#
#Response for player/42636. Successful:  <Response [200]>
#
#Total successful requests:  1591
#Completed :  61.19 %
#Elapsed time:  11868.59 s
#------------------------------------------------------------------------------
#
#Response for player/1072470. Successful:  <Response [200]>
#
#Total successful requests:  1592
#Completed :  61.23 %
#Elapsed time:  11875.70 s
#------------------------------------------------------------------------------
#
#Response for player/538506. Successful:  <Response [200]>
#
#Total successful requests:  1593
#Completed :  61.27 %
#Elapsed time:  11877.04 s
#------------------------------------------------------------------------------
#
#Response for player/8432. Successful:  <Response [200]>
#
#Total successful requests:  1594
#Completed :  61.31 %
#Elapsed time:  11882.46 s
#------------------------------------------------------------------------------
#
#Response for player/498875. Successful:  <Response [200]>
#
#Total successful requests:  1595
#Completed :  61.35 %
#Elapsed time:  11896.97 s
#------------------------------------------------------------------------------
#
#Response for player/303349. Successful:  <Response [200]>
#
#Total successful requests:  1596
#Completed :  61.38 %
#Elapsed time:  11904.02 s
#------------------------------------------------------------------------------
#
#Response for player/37222. Successful:  <Response [200]>
#
#Total successful requests:  1597
#Completed :  61.42 %
#Elapsed time:  11906.76 s
#------------------------------------------------------------------------------
#
#Response for player/25905. Successful:  <Response [200]>
#
#Total successful requests:  1598
#Completed :  61.46 %
#Elapsed time:  11928.91 s
#------------------------------------------------------------------------------
#
#Response for player/960361. Successful:  <Response [200]>
#
#Total successful requests:  1599
#Completed :  61.50 %
#Elapsed time:  11933.41 s
#------------------------------------------------------------------------------
#
#Response for player/232442. Successful:  <Response [200]>
#
#Total successful requests:  1600
#Completed :  61.54 %
#Elapsed time:  11938.32 s
#------------------------------------------------------------------------------
#
#Response for page 9 Successful:  <Response [200]> 	=>
#

#list of players:  200
#Response for player/24784. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  1601
#Completed :  61.58 %
#Elapsed time:  11983.15 s
#------------------------------------------------------------------------------
#
#Response for player/7360. Successful:  <Response [200]>
#
#Total successful requests:  1602
#Completed :  61.62 %
#Elapsed time:  11984.74 s
#------------------------------------------------------------------------------
#
#Response for player/960035. Successful:  <Response [200]>
#
#Total successful requests:  1603
#Completed :  61.65 %
#Elapsed time:  11985.55 s
#------------------------------------------------------------------------------
#
#Response for player/8220. Successful:  <Response [200]>
#
#Total successful requests:  1604
#Completed :  61.69 %
#Elapsed time:  11987.37 s
#------------------------------------------------------------------------------
#
#Response for player/55271. Successful:  <Response [200]>
#
#Total successful requests:  1605
#Completed :  61.73 %
#Elapsed time:  11996.73 s
#------------------------------------------------------------------------------
#
#Response for player/28010. Successful:  <Response [200]>
#
#Total successful requests:  1606
#Completed :  61.77 %
#Elapsed time:  12009.35 s
#------------------------------------------------------------------------------
#
#Response for player/48460. Successful:  <Response [200]>
#
#Total successful requests:  1607
#Completed :  61.81 %
#Elapsed time:  12014.33 s
#------------------------------------------------------------------------------
#
#Response for player/5385. Successful:  <Response [200]>
#
#Total successful requests:  1608
#Completed :  61.85 %
#Elapsed time:  12016.25 s
#------------------------------------------------------------------------------
#
#Response for player/40572. Successful:  <Response [200]>
#
#Total successful requests:  1609
#Completed :  61.88 %
#Elapsed time:  12042.56 s
#------------------------------------------------------------------------------
#
#Response for player/355107. Successful:  <Response [200]>
#
#Total successful requests:  1610
#Completed :  61.92 %
#Elapsed time:  12050.54 s
#------------------------------------------------------------------------------
#
#Response for player/16320. Successful:  <Response [200]>
#
#Total successful requests:  1611
#Completed :  61.96 %
#Elapsed time:  12062.23 s
#------------------------------------------------------------------------------
#
#Response for player/6534. Successful:  <Response [200]>
#
#Total successful requests:  1612
#Completed :  62.00 %
#Elapsed time:  12067.25 s
#------------------------------------------------------------------------------
#
#Response for player/7083. Successful:  <Response [200]>
#
#Total successful requests:  1613
#Completed :  62.04 %
#Elapsed time:  12078.88 s
#------------------------------------------------------------------------------
#
#Response for player/1159641. Successful:  <Response [200]>
#
#Total successful requests:  1614
#Completed :  62.08 %
#Elapsed time:  12080.22 s
#------------------------------------------------------------------------------
#
#Response for player/300629. Successful:  <Response [200]>
#
#Total successful requests:  1615
#Completed :  62.12 %
#Elapsed time:  12087.70 s
#------------------------------------------------------------------------------
#
#Response for player/25612. Successful:  <Response [200]>
#
#Total successful requests:  1616
#Completed :  62.15 %
#Elapsed time:  12090.94 s
#------------------------------------------------------------------------------
#
#Response for player/24945. Successful:  <Response [200]>
#
#Total successful requests:  1617
#Completed :  62.19 %
#Elapsed time:  12094.02 s
#------------------------------------------------------------------------------
#
#Response for player/21431. Successful:  <Response [200]>
#
#Total successful requests:  1618
#Completed :  62.23 %
#Elapsed time:  12096.61 s
#------------------------------------------------------------------------------
#
#Response for player/47850. Successful:  <Response [200]>
#
#Total successful requests:  1619
#Completed :  62.27 %
#Elapsed time:  12098.52 s
#------------------------------------------------------------------------------
#
#Response for player/23977. Successful:  <Response [200]>
#
#Total successful requests:  1620
#Completed :  62.31 %
#Elapsed time:  12101.40 s
#------------------------------------------------------------------------------
#
#Response for player/414990. Successful:  <Response [200]>
#
#Total successful requests:  1621
#Completed :  62.35 %
#Elapsed time:  12103.82 s
#------------------------------------------------------------------------------
#
#Response for player/23765. Successful:  <Response [200]>
#
#Total successful requests:  1622
#Completed :  62.38 %
#Elapsed time:  12113.87 s
#------------------------------------------------------------------------------
#
#Response for player/32966. Successful:  <Response [200]>
#
#Total successful requests:  1623
#Completed :  62.42 %
#Elapsed time:  12116.53 s
#------------------------------------------------------------------------------
#
#Response for player/596664. Successful:  <Response [200]>
#
#Total successful requests:  1624
#Completed :  62.46 %
#Elapsed time:  12121.01 s
#------------------------------------------------------------------------------
#
#Response for player/49477. Successful:  <Response [200]>
#
#Total successful requests:  1625
#Completed :  62.50 %
#Elapsed time:  12123.40 s
#------------------------------------------------------------------------------
#
#Response for player/16925. Successful:  <Response [200]>
#
#Total successful requests:  1626
#Completed :  62.54 %
#Elapsed time:  12124.11 s
#------------------------------------------------------------------------------
#
#Response for player/25538. Successful:  <Response [200]>
#
#Total successful requests:  1627
#Completed :  62.58 %
#Elapsed time:  12128.03 s
#------------------------------------------------------------------------------
#
#Response for player/392944. Successful:  <Response [200]>
#
#Total successful requests:  1628
#Completed :  62.62 %
#Elapsed time:  12134.03 s
#------------------------------------------------------------------------------
#
#Response for player/31778. Successful:  <Response [200]>
#
#Total successful requests:  1629
#Completed :  62.65 %
#Elapsed time:  12148.25 s
#------------------------------------------------------------------------------
#
#Response for player/42106. Successful:  <Response [200]>
#
#Total successful requests:  1630
#Completed :  62.69 %
#Elapsed time:  12153.01 s
#------------------------------------------------------------------------------
#
#Response for player/247008. Successful:  <Response [200]>
#
#Total successful requests:  1631
#Completed :  62.73 %
#Elapsed time:  12155.40 s
#------------------------------------------------------------------------------
#
#Response for player/24010. Successful:  <Response [200]>
#
#Total successful requests:  1632
#Completed :  62.77 %
#Elapsed time:  12157.85 s
#------------------------------------------------------------------------------
#
#Response for player/38745. Successful:  <Response [200]>
#
#Total successful requests:  1633
#Completed :  62.81 %
#Elapsed time:  12165.26 s
#------------------------------------------------------------------------------
#
#Response for player/288284. Successful:  <Response [200]>
#
#Total successful requests:  1634
#Completed :  62.85 %
#Elapsed time:  12167.82 s
#------------------------------------------------------------------------------
#
#Response for player/55525. Successful:  <Response [200]>
#
#Total successful requests:  1635
#Completed :  62.88 %
#Elapsed time:  12169.57 s
#------------------------------------------------------------------------------
#
#Response for player/713811. Successful:  <Response [200]>
#
#Total successful requests:  1636
#Completed :  62.92 %
#Elapsed time:  12171.42 s
#------------------------------------------------------------------------------
#
#Response for player/370535. Successful:  <Response [200]>
#
#Total successful requests:  1637
#Completed :  62.96 %
#Elapsed time:  12173.41 s
#------------------------------------------------------------------------------
#
#Response for player/56094. Successful:  <Response [200]>
#
#Total successful requests:  1638
#Completed :  63.00 %
#Elapsed time:  12174.78 s
#------------------------------------------------------------------------------
#
#Response for player/42641. Successful:  <Response [200]>
#
#Total successful requests:  1639
#Completed :  63.04 %
#Elapsed time:  12180.15 s
#------------------------------------------------------------------------------
#
#Response for player/526492. Successful:  <Response [200]>
#
#Total successful requests:  1640
#Completed :  63.08 %
#Elapsed time:  12181.96 s
#------------------------------------------------------------------------------
#
#Response for player/38749. Successful:  <Response [200]>
#
#Total successful requests:  1641
#Completed :  63.12 %
#Elapsed time:  12187.10 s
#------------------------------------------------------------------------------
#
#Response for player/717099. Successful:  <Response [200]>
#
#Total successful requests:  1642
#Completed :  63.15 %
#Elapsed time:  12188.07 s
#------------------------------------------------------------------------------
#
#Response for player/49043. Successful:  <Response [200]>
#
#Total successful requests:  1643
#Completed :  63.19 %
#Elapsed time:  12189.97 s
#------------------------------------------------------------------------------
#
#Response for player/6474. Successful:  <Response [200]>
#
#Total successful requests:  1644
#Completed :  63.23 %
#Elapsed time:  12199.06 s
#------------------------------------------------------------------------------
#
#Response for player/25540. Successful:  <Response [200]>
#
#Total successful requests:  1645
#Completed :  63.27 %
#Elapsed time:  12200.53 s
#------------------------------------------------------------------------------
#
#Response for player/247009. Successful:  <Response [200]>
#
#Total successful requests:  1646
#Completed :  63.31 %
#Elapsed time:  12202.64 s
#------------------------------------------------------------------------------
#
#Response for player/49863. Successful:  <Response [200]>
#
#Total successful requests:  1647
#Completed :  63.35 %
#Elapsed time:  12214.01 s
#------------------------------------------------------------------------------
#
#Response for player/42879. Successful:  <Response [200]>
#
#Total successful requests:  1648
#Completed :  63.38 %
#Elapsed time:  12233.30 s
#------------------------------------------------------------------------------
#
#Response for player/7619. Successful:  <Response [200]>
#
#Total successful requests:  1649
#Completed :  63.42 %
#Elapsed time:  12245.57 s
#------------------------------------------------------------------------------
#
#Response for player/24726. Successful:  <Response [200]>
#
#Total successful requests:  1650
#Completed :  63.46 %
#Elapsed time:  12247.54 s
#------------------------------------------------------------------------------
#
#Response for player/21598. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  1651
#Completed :  63.50 %
#Elapsed time:  12255.20 s
#------------------------------------------------------------------------------
#
#Response for player/437005. Successful:  <Response [200]>
#
#Total successful requests:  1652
#Completed :  63.54 %
#Elapsed time:  12265.26 s
#------------------------------------------------------------------------------
#
#Response for player/524845. Successful:  <Response [200]>
#
#Total successful requests:  1653
#Completed :  63.58 %
#Elapsed time:  12267.74 s
#------------------------------------------------------------------------------
#
#Response for player/23713. Successful:  <Response [200]>
#
#Total successful requests:  1654
#Completed :  63.62 %
#Elapsed time:  12278.24 s
#------------------------------------------------------------------------------
#
#Response for player/4999. Successful:  <Response [200]>
#
#Total successful requests:  1655
#Completed :  63.65 %
#Elapsed time:  12285.50 s
#------------------------------------------------------------------------------
#
#Response for player/29976. Successful:  <Response [200]>
#
#Total successful requests:  1656
#Completed :  63.69 %
#Elapsed time:  12288.27 s
#------------------------------------------------------------------------------
#
#Response for player/919527. Successful:  <Response [200]>
#
#Total successful requests:  1657
#Completed :  63.73 %
#Elapsed time:  12290.25 s
#------------------------------------------------------------------------------
#
#Response for player/56056. Successful:  <Response [200]>
#
#Total successful requests:  1658
#Completed :  63.77 %
#Elapsed time:  12291.72 s
#------------------------------------------------------------------------------
#
#Response for player/308691. Successful:  <Response [200]>
#
#Total successful requests:  1659
#Completed :  63.81 %
#Elapsed time:  12299.60 s
#------------------------------------------------------------------------------
#
#Response for player/23824. Successful:  <Response [200]>
#
#Total successful requests:  1660
#Completed :  63.85 %
#Elapsed time:  12313.15 s
#------------------------------------------------------------------------------
#
#Response for player/38608. Successful:  <Response [200]>
#
#Total successful requests:  1661
#Completed :  63.88 %
#Elapsed time:  12321.09 s
#------------------------------------------------------------------------------
#
#Response for player/22144. Successful:  <Response [200]>
#
#Total successful requests:  1662
#Completed :  63.92 %
#Elapsed time:  12328.80 s
#------------------------------------------------------------------------------
#
#Response for player/25023. Successful:  <Response [200]>
#
#Total successful requests:  1663
#Completed :  63.96 %
#Elapsed time:  12330.66 s
#------------------------------------------------------------------------------
#
#Response for player/50874. Successful:  <Response [200]>
#
#Total successful requests:  1664
#Completed :  64.00 %
#Elapsed time:  12341.59 s
#------------------------------------------------------------------------------
#
#Response for player/43871. Successful:  <Response [200]>
#
#Total successful requests:  1665
#Completed :  64.04 %
#Elapsed time:  12343.99 s
#------------------------------------------------------------------------------
#
#Response for player/25879. Successful:  <Response [200]>
#
#Total successful requests:  1666
#Completed :  64.08 %
#Elapsed time:  12350.65 s
#------------------------------------------------------------------------------
#
#Response for player/26257. Successful:  <Response [200]>
#
#Total successful requests:  1667
#Completed :  64.12 %
#Elapsed time:  12362.70 s
#------------------------------------------------------------------------------
#
#Response for player/39015. Successful:  <Response [200]>
#
#Total successful requests:  1668
#Completed :  64.15 %
#Elapsed time:  12365.07 s
#------------------------------------------------------------------------------
#
#Response for player/39019. Successful:  <Response [200]>
#
#Total successful requests:  1669
#Completed :  64.19 %
#Elapsed time:  12366.25 s
#------------------------------------------------------------------------------
#
#Response for player/8590. Successful:  <Response [200]>
#
#Total successful requests:  1670
#Completed :  64.23 %
#Elapsed time:  12369.06 s
#------------------------------------------------------------------------------
#
#Response for player/430246. Successful:  <Response [200]>
#
#Total successful requests:  1671
#Completed :  64.27 %
#Elapsed time:  12374.49 s
#------------------------------------------------------------------------------
#
#Response for player/36606. Successful:  <Response [200]>
#
#Total successful requests:  1672
#Completed :  64.31 %
#Elapsed time:  12391.43 s
#------------------------------------------------------------------------------
#
#Response for player/267414. Successful:  <Response [200]>
#
#Total successful requests:  1673
#Completed :  64.35 %
#Elapsed time:  12398.41 s
#------------------------------------------------------------------------------
#
#Response for player/12923. Successful:  <Response [200]>
#
#Total successful requests:  1674
#Completed :  64.38 %
#Elapsed time:  12399.54 s
#------------------------------------------------------------------------------
#
#Response for player/302875. Successful:  <Response [200]>
#
#Total successful requests:  1675
#Completed :  64.42 %
#Elapsed time:  12418.39 s
#------------------------------------------------------------------------------
#
#Response for player/24703. Successful:  <Response [200]>
#
#Total successful requests:  1676
#Completed :  64.46 %
#Elapsed time:  12419.53 s
#------------------------------------------------------------------------------
#
#Response for player/55584. Successful:  <Response [200]>
#
#Total successful requests:  1677
#Completed :  64.50 %
#Elapsed time:  12428.25 s
#------------------------------------------------------------------------------
#
#Response for player/41411. Successful:  <Response [200]>
#
#Total successful requests:  1678
#Completed :  64.54 %
#Elapsed time:  12429.90 s
#------------------------------------------------------------------------------
#
#Response for player/7302. Successful:  <Response [200]>
#
#Total successful requests:  1679
#Completed :  64.58 %
#Elapsed time:  12445.14 s
#------------------------------------------------------------------------------
#
#Response for player/24171. Successful:  <Response [200]>
#
#Total successful requests:  1680
#Completed :  64.62 %
#Elapsed time:  12463.35 s
#------------------------------------------------------------------------------
#
#Response for player/247007. Successful:  <Response [200]>
#
#Total successful requests:  1681
#Completed :  64.65 %
#Elapsed time:  12465.56 s
#------------------------------------------------------------------------------
#
#Response for player/49487. Successful:  <Response [200]>
#
#Total successful requests:  1682
#Completed :  64.69 %
#Elapsed time:  12467.78 s
#------------------------------------------------------------------------------
#
#Response for player/30151. Successful:  <Response [200]>
#
#Total successful requests:  1683
#Completed :  64.73 %
#Elapsed time:  12482.91 s
#------------------------------------------------------------------------------
#
#Response for player/6549. Successful:  <Response [200]>
#
#Total successful requests:  1684
#Completed :  64.77 %
#Elapsed time:  12502.09 s
#------------------------------------------------------------------------------
#
#Response for player/55692. Successful:  <Response [200]>
#
#Total successful requests:  1685
#Completed :  64.81 %
#Elapsed time:  12502.82 s
#------------------------------------------------------------------------------
#
#Response for player/653033. Successful:  <Response [200]>
#
#Total successful requests:  1686
#Completed :  64.85 %
#Elapsed time:  12509.19 s
#------------------------------------------------------------------------------
#
#Response for player/625964. Successful:  <Response [200]>
#
#Total successful requests:  1687
#Completed :  64.88 %
#Elapsed time:  12523.65 s
#------------------------------------------------------------------------------
#
#Response for player/35939. Successful:  <Response [200]>
#
#Total successful requests:  1688
#Completed :  64.92 %
#Elapsed time:  12534.61 s
#------------------------------------------------------------------------------
#
#Response for player/3943. Successful:  <Response [200]>
#
#Total successful requests:  1689
#Completed :  64.96 %
#Elapsed time:  12538.31 s
#------------------------------------------------------------------------------
#
#Response for player/670013. Successful:  <Response [200]>
#
#Total successful requests:  1690
#Completed :  65.00 %
#Elapsed time:  12540.34 s
#------------------------------------------------------------------------------
#
#Response for player/44138. Successful:  <Response [200]>
#
#Total successful requests:  1691
#Completed :  65.04 %
#Elapsed time:  12543.13 s
#------------------------------------------------------------------------------
#
#Response for player/297517. Successful:  <Response [200]>
#
#Total successful requests:  1692
#Completed :  65.08 %
#Elapsed time:  12546.57 s
#------------------------------------------------------------------------------
#
#Response for player/33044. Successful:  <Response [200]>
#
#Total successful requests:  1693
#Completed :  65.12 %
#Elapsed time:  12557.54 s
#------------------------------------------------------------------------------
#
#Response for player/7612. Successful:  <Response [200]>
#
#Total successful requests:  1694
#Completed :  65.15 %
#Elapsed time:  12571.55 s
#------------------------------------------------------------------------------
#
#Response for player/467420. Successful:  <Response [200]>
#
#Total successful requests:  1695
#Completed :  65.19 %
#Elapsed time:  12576.96 s
#------------------------------------------------------------------------------
#
#Response for player/1126253. Successful:  <Response [200]>
#
#Total successful requests:  1696
#Completed :  65.23 %
#Elapsed time:  12589.94 s
#------------------------------------------------------------------------------
#
#Response for player/26875. Successful:  <Response [200]>
#
#Total successful requests:  1697
#Completed :  65.27 %
#Elapsed time:  12593.96 s
#------------------------------------------------------------------------------
#
#Response for player/49097. Successful:  <Response [200]>
#
#Total successful requests:  1698
#Completed :  65.31 %
#Elapsed time:  12606.84 s
#------------------------------------------------------------------------------
#
#Response for player/15485. Successful:  <Response [200]>
#
#Total successful requests:  1699
#Completed :  65.35 %
#Elapsed time:  12617.12 s
#------------------------------------------------------------------------------
#
#Response for player/222320. Successful:  <Response [200]>
#
#Total successful requests:  1700
#Completed :  65.38 %
#Elapsed time:  12618.84 s
#------------------------------------------------------------------------------
#
#Response for player/55579. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  1701
#Completed :  65.42 %
#Elapsed time:  12628.47 s
#------------------------------------------------------------------------------
#
#Response for player/49767. Successful:  <Response [200]>
#
#Total successful requests:  1702
#Completed :  65.46 %
#Elapsed time:  12629.30 s
#------------------------------------------------------------------------------
#
#Response for player/25481. Successful:  <Response [200]>
#
#Total successful requests:  1703
#Completed :  65.50 %
#Elapsed time:  12643.48 s
#------------------------------------------------------------------------------
#
#Response for player/429738. Successful:  <Response [200]>
#
#Total successful requests:  1704
#Completed :  65.54 %
#Elapsed time:  12650.70 s
#------------------------------------------------------------------------------
#
#Response for player/537119. Successful:  <Response [200]>
#
#Total successful requests:  1705
#Completed :  65.58 %
#Elapsed time:  12652.14 s
#------------------------------------------------------------------------------
#
#Response for player/7898. Successful:  <Response [200]>
#
#Total successful requests:  1706
#Completed :  65.62 %
#Elapsed time:  12656.72 s
#------------------------------------------------------------------------------
#
#Response for player/42661. Successful:  <Response [200]>
#
#Total successful requests:  1707
#Completed :  65.65 %
#Elapsed time:  12657.84 s
#------------------------------------------------------------------------------
#
#Response for player/55774. Successful:  <Response [200]>
#
#Total successful requests:  1708
#Completed :  65.69 %
#Elapsed time:  12658.87 s
#------------------------------------------------------------------------------
#
#Response for player/8256. Successful:  <Response [200]>
#
#Total successful requests:  1709
#Completed :  65.73 %
#Elapsed time:  12668.78 s
#------------------------------------------------------------------------------
#
#Response for player/48102. Successful:  <Response [200]>
#
#Total successful requests:  1710
#Completed :  65.77 %
#Elapsed time:  12676.33 s
#------------------------------------------------------------------------------
#
#Response for player/8453. Successful:  <Response [200]>
#
#Total successful requests:  1711
#Completed :  65.81 %
#Elapsed time:  12685.75 s
#------------------------------------------------------------------------------
#
#Response for player/9042. Successful:  <Response [200]>
#
#Total successful requests:  1712
#Completed :  65.85 %
#Elapsed time:  12689.92 s
#------------------------------------------------------------------------------
#
#Response for player/36303. Successful:  <Response [200]>
#
#Total successful requests:  1713
#Completed :  65.88 %
#Elapsed time:  12698.34 s
#------------------------------------------------------------------------------
#
#Response for player/24136. Successful:  <Response [200]>
#
#Total successful requests:  1714
#Completed :  65.92 %
#Elapsed time:  12703.38 s
#------------------------------------------------------------------------------
#
#Response for player/51479. Successful:  <Response [200]>
#
#Total successful requests:  1715
#Completed :  65.96 %
#Elapsed time:  12710.48 s
#------------------------------------------------------------------------------
#
#Response for player/1036191. Successful:  <Response [200]>
#
#Total successful requests:  1716
#Completed :  66.00 %
#Elapsed time:  12716.82 s
#------------------------------------------------------------------------------
#
#Response for player/11914. Successful:  <Response [200]>
#
#Total successful requests:  1717
#Completed :  66.04 %
#Elapsed time:  12723.57 s
#------------------------------------------------------------------------------
#
#Response for player/718553. Successful:  <Response [200]>
#
#Total successful requests:  1718
#Completed :  66.08 %
#Elapsed time:  12725.11 s
#------------------------------------------------------------------------------
#
#Response for player/465783. Successful:  <Response [200]>
#
#Total successful requests:  1719
#Completed :  66.12 %
#Elapsed time:  12727.79 s
#------------------------------------------------------------------------------
#
#Response for player/14152. Successful:  <Response [200]>
#
#Total successful requests:  1720
#Completed :  66.15 %
#Elapsed time:  12729.78 s
#------------------------------------------------------------------------------
#
#Response for player/55522. Successful:  <Response [200]>
#
#Total successful requests:  1721
#Completed :  66.19 %
#Elapsed time:  12734.17 s
#------------------------------------------------------------------------------
#
#Response for player/52931. Successful:  <Response [200]>
#
#Total successful requests:  1722
#Completed :  66.23 %
#Elapsed time:  12744.00 s
#------------------------------------------------------------------------------
#
#Response for player/348109. Successful:  <Response [200]>
#
#Total successful requests:  1723
#Completed :  66.27 %
#Elapsed time:  12750.06 s
#------------------------------------------------------------------------------
#
#Response for player/23795. Successful:  <Response [200]>
#
#Total successful requests:  1724
#Completed :  66.31 %
#Elapsed time:  12752.32 s
#------------------------------------------------------------------------------
#
#Response for player/24768. Successful:  <Response [200]>
#
#Total successful requests:  1725
#Completed :  66.35 %
#Elapsed time:  12756.60 s
#------------------------------------------------------------------------------
#
#Response for player/48844. Successful:  <Response [200]>
#
#Total successful requests:  1726
#Completed :  66.38 %
#Elapsed time:  12758.99 s
#------------------------------------------------------------------------------
#
#Response for player/5941. Successful:  <Response [200]>
#
#Total successful requests:  1727
#Completed :  66.42 %
#Elapsed time:  12762.36 s
#------------------------------------------------------------------------------
#
#Response for player/40580. Successful:  <Response [200]>
#
#Total successful requests:  1728
#Completed :  66.46 %
#Elapsed time:  12769.12 s
#------------------------------------------------------------------------------
#
#Response for player/24603. Successful:  <Response [200]>
#
#Total successful requests:  1729
#Completed :  66.50 %
#Elapsed time:  12777.51 s
#------------------------------------------------------------------------------
#
#Response for player/49849. Successful:  <Response [200]>
#
#Total successful requests:  1730
#Completed :  66.54 %
#Elapsed time:  12782.62 s
#------------------------------------------------------------------------------
#
#Response for player/553821. Successful:  <Response [200]>
#
#Total successful requests:  1731
#Completed :  66.58 %
#Elapsed time:  12784.17 s
#------------------------------------------------------------------------------
#
#Response for player/8264. Successful:  <Response [200]>
#
#Total successful requests:  1732
#Completed :  66.62 %
#Elapsed time:  12793.16 s
#------------------------------------------------------------------------------
#
#Response for player/24978. Successful:  <Response [200]>
#
#Total successful requests:  1733
#Completed :  66.65 %
#Elapsed time:  12796.98 s
#------------------------------------------------------------------------------
#
#Response for player/51643. Successful:  <Response [200]>
#
#Total successful requests:  1734
#Completed :  66.69 %
#Elapsed time:  12799.71 s
#------------------------------------------------------------------------------
#
#Response for player/232730. Successful:  <Response [200]>
#
#Total successful requests:  1735
#Completed :  66.73 %
#Elapsed time:  12802.01 s
#------------------------------------------------------------------------------
#
#Response for player/41058. Successful:  <Response [200]>
#
#Total successful requests:  1736
#Completed :  66.77 %
#Elapsed time:  12805.65 s
#------------------------------------------------------------------------------
#
#Response for player/1158100. Successful:  <Response [200]>
#
#Total successful requests:  1737
#Completed :  66.81 %
#Elapsed time:  12809.09 s
#------------------------------------------------------------------------------
#
#Response for player/31025. Successful:  <Response [200]>
#
#Total successful requests:  1738
#Completed :  66.85 %
#Elapsed time:  12811.12 s
#------------------------------------------------------------------------------
#
#Response for player/43275. Successful:  <Response [200]>
#
#Total successful requests:  1739
#Completed :  66.88 %
#Elapsed time:  12813.42 s
#------------------------------------------------------------------------------
#
#Response for player/1127317. Successful:  <Response [200]>
#
#Total successful requests:  1740
#Completed :  66.92 %
#Elapsed time:  12816.59 s
#------------------------------------------------------------------------------
#
#Response for player/547092. Successful:  <Response [200]>
#
#Total successful requests:  1741
#Completed :  66.96 %
#Elapsed time:  12837.43 s
#------------------------------------------------------------------------------
#
#Response for player/324358. Successful:  <Response [200]>
#
#Total successful requests:  1742
#Completed :  67.00 %
#Elapsed time:  12839.07 s
#------------------------------------------------------------------------------
#
#Response for player/37002. Successful:  <Response [200]>
#
#Total successful requests:  1743
#Completed :  67.04 %
#Elapsed time:  12843.01 s
#------------------------------------------------------------------------------
#
#Response for player/208755. Successful:  <Response [200]>
#
#Total successful requests:  1744
#Completed :  67.08 %
#Elapsed time:  12853.15 s
#------------------------------------------------------------------------------
#
#Response for player/467426. Successful:  <Response [200]>
#
#Total successful requests:  1745
#Completed :  67.12 %
#Elapsed time:  12859.18 s
#------------------------------------------------------------------------------
#
#Response for player/49236. Successful:  <Response [200]>
#
#Total successful requests:  1746
#Completed :  67.15 %
#Elapsed time:  12867.75 s
#------------------------------------------------------------------------------
#
#Response for player/235521. Successful:  <Response [200]>
#
#Total successful requests:  1747
#Completed :  67.19 %
#Elapsed time:  12869.85 s
#------------------------------------------------------------------------------
#
#Response for player/24807. Successful:  <Response [200]>
#
#Total successful requests:  1748
#Completed :  67.23 %
#Elapsed time:  12871.33 s
#------------------------------------------------------------------------------
#
#Response for player/277955. Successful:  <Response [200]>
#
#Total successful requests:  1749
#Completed :  67.27 %
#Elapsed time:  12875.93 s
#------------------------------------------------------------------------------
#
#Response for player/6270. Successful:  <Response [200]>
#
#Total successful requests:  1750
#Completed :  67.31 %
#Elapsed time:  12877.90 s
#------------------------------------------------------------------------------
#
#Response for player/41301. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  1751
#Completed :  67.35 %
#Elapsed time:  12883.56 s
#------------------------------------------------------------------------------
#
#Response for player/41310. Successful:  <Response [200]>
#
#Total successful requests:  1752
#Completed :  67.38 %
#Elapsed time:  12903.14 s
#------------------------------------------------------------------------------
#
#Response for player/216996. Successful:  <Response [200]>
#
#Total successful requests:  1753
#Completed :  67.42 %
#Elapsed time:  12905.13 s
#------------------------------------------------------------------------------
#
#Response for player/448243. Successful:  <Response [200]>
#
#Total successful requests:  1754
#Completed :  67.46 %
#Elapsed time:  12910.08 s
#------------------------------------------------------------------------------
#
#Response for player/34085. Successful:  <Response [200]>
#
#Total successful requests:  1755
#Completed :  67.50 %
#Elapsed time:  12914.22 s
#------------------------------------------------------------------------------
#
#Response for player/1156690. Successful:  <Response [200]>
#
#Total successful requests:  1756
#Completed :  67.54 %
#Elapsed time:  12917.50 s
#------------------------------------------------------------------------------
#
#Response for player/443263. Successful:  <Response [200]>
#
#Total successful requests:  1757
#Completed :  67.58 %
#Elapsed time:  12928.41 s
#------------------------------------------------------------------------------
#
#Response for player/8231. Successful:  <Response [200]>
#
#Total successful requests:  1758
#Completed :  67.62 %
#Elapsed time:  12940.95 s
#------------------------------------------------------------------------------
#
#Response for player/43703. Successful:  <Response [200]>
#
#Total successful requests:  1759
#Completed :  67.65 %
#Elapsed time:  12953.28 s
#------------------------------------------------------------------------------
#
#Response for player/39821. Successful:  <Response [200]>
#
#Total successful requests:  1760
#Completed :  67.69 %
#Elapsed time:  12965.05 s
#------------------------------------------------------------------------------
#
#Response for player/495551. Successful:  <Response [200]>
#
#Total successful requests:  1761
#Completed :  67.73 %
#Elapsed time:  12968.92 s
#------------------------------------------------------------------------------
#
#Response for player/36950. Successful:  <Response [200]>
#
#Total successful requests:  1762
#Completed :  67.77 %
#Elapsed time:  12980.18 s
#------------------------------------------------------------------------------
#
#Response for player/37220. Successful:  <Response [200]>
#
#Total successful requests:  1763
#Completed :  67.81 %
#Elapsed time:  12985.29 s
#------------------------------------------------------------------------------
#
#Response for player/52048. Successful:  <Response [200]>
#
#Total successful requests:  1764
#Completed :  67.85 %
#Elapsed time:  12987.54 s
#------------------------------------------------------------------------------
#
#Response for player/646175. Successful:  <Response [200]>
#
#Total successful requests:  1765
#Completed :  67.88 %
#Elapsed time:  12989.33 s
#------------------------------------------------------------------------------
#
#Response for player/30182. Successful:  <Response [200]>
#
#Total successful requests:  1766
#Completed :  67.92 %
#Elapsed time:  12992.22 s
#------------------------------------------------------------------------------
#
#Response for player/56017. Successful:  <Response [200]>
#
#Total successful requests:  1767
#Completed :  67.96 %
#Elapsed time:  12997.06 s
#------------------------------------------------------------------------------
#
#Response for player/18655. Successful:  <Response [200]>
#
#Total successful requests:  1768
#Completed :  68.00 %
#Elapsed time:  13005.20 s
#------------------------------------------------------------------------------
#
#Response for player/42323. Successful:  <Response [200]>
#
#Total successful requests:  1769
#Completed :  68.04 %
#Elapsed time:  13006.57 s
#------------------------------------------------------------------------------
#
#Response for player/46976. Successful:  <Response [200]>
#
#Total successful requests:  1770
#Completed :  68.08 %
#Elapsed time:  13008.15 s
#------------------------------------------------------------------------------
#
#Response for player/47184. Successful:  <Response [200]>
#
#Total successful requests:  1771
#Completed :  68.12 %
#Elapsed time:  13016.21 s
#------------------------------------------------------------------------------
#
#Response for player/38418. Successful:  <Response [200]>
#
#Total successful requests:  1772
#Completed :  68.15 %
#Elapsed time:  13017.64 s
#------------------------------------------------------------------------------
#
#Response for player/56188. Successful:  <Response [200]>
#
#Total successful requests:  1773
#Completed :  68.19 %
#Elapsed time:  13022.47 s
#------------------------------------------------------------------------------
#
#Response for player/24798. Successful:  <Response [200]>
#
#Total successful requests:  1774
#Completed :  68.23 %
#Elapsed time:  13028.48 s
#------------------------------------------------------------------------------
#
#Response for player/24825. Successful:  <Response [200]>
#
#Total successful requests:  1775
#Completed :  68.27 %
#Elapsed time:  13036.17 s
#------------------------------------------------------------------------------
#
#Response for player/43550. Successful:  <Response [200]>
#
#Total successful requests:  1776
#Completed :  68.31 %
#Elapsed time:  13055.31 s
#------------------------------------------------------------------------------
#
#Response for player/291088. Successful:  <Response [200]>
#
#Total successful requests:  1777
#Completed :  68.35 %
#Elapsed time:  13060.50 s
#------------------------------------------------------------------------------
#
#Response for player/25547. Successful:  <Response [200]>
#
#Total successful requests:  1778
#Completed :  68.38 %
#Elapsed time:  13063.13 s
#------------------------------------------------------------------------------
#
#Response for player/9121. Successful:  <Response [200]>
#
#Total successful requests:  1779
#Completed :  68.42 %
#Elapsed time:  13064.14 s
#------------------------------------------------------------------------------
#
#Response for player/51292. Successful:  <Response [200]>
#
#Total successful requests:  1780
#Completed :  68.46 %
#Elapsed time:  13069.03 s
#------------------------------------------------------------------------------
#
#Response for player/418617. Successful:  <Response [200]>
#
#Total successful requests:  1781
#Completed :  68.50 %
#Elapsed time:  13074.50 s
#------------------------------------------------------------------------------
#
#Response for player/51793. Successful:  <Response [200]>
#
#Total successful requests:  1782
#Completed :  68.54 %
#Elapsed time:  13076.19 s
#------------------------------------------------------------------------------
#
#Response for player/49212. Successful:  <Response [200]>
#
#Total successful requests:  1783
#Completed :  68.58 %
#Elapsed time:  13077.83 s
#------------------------------------------------------------------------------
#
#Response for player/267724. Successful:  <Response [200]>
#
#Total successful requests:  1784
#Completed :  68.62 %
#Elapsed time:  13090.76 s
#------------------------------------------------------------------------------
#
#Response for player/24913. Successful:  <Response [200]>
#
#Total successful requests:  1785
#Completed :  68.65 %
#Elapsed time:  13093.89 s
#------------------------------------------------------------------------------
#
#Response for player/56038. Successful:  <Response [200]>
#
#Total successful requests:  1786
#Completed :  68.69 %
#Elapsed time:  13095.63 s
#------------------------------------------------------------------------------
#
#Response for player/23770. Successful:  <Response [200]>
#
#Total successful requests:  1787
#Completed :  68.73 %
#Elapsed time:  13102.20 s
#------------------------------------------------------------------------------
#
#Response for player/1058510. Successful:  <Response [200]>
#
#Total successful requests:  1788
#Completed :  68.77 %
#Elapsed time:  13110.23 s
#------------------------------------------------------------------------------
#
#Response for player/42616. Successful:  <Response [200]>
#
#Total successful requests:  1789
#Completed :  68.81 %
#Elapsed time:  13115.47 s
#------------------------------------------------------------------------------
#
#Response for player/42646. Successful:  <Response [200]>
#
#Total successful requests:  1790
#Completed :  68.85 %
#Elapsed time:  13143.08 s
#------------------------------------------------------------------------------
#
#Response for player/317252. Successful:  <Response [200]>
#
#Total successful requests:  1791
#Completed :  68.88 %
#Elapsed time:  13144.92 s
#------------------------------------------------------------------------------
#
#Response for player/8076. Successful:  <Response [200]>
#
#Total successful requests:  1792
#Completed :  68.92 %
#Elapsed time:  13154.00 s
#------------------------------------------------------------------------------
#
#Response for player/9074. Successful:  <Response [200]>
#
#Total successful requests:  1793
#Completed :  68.96 %
#Elapsed time:  13159.47 s
#------------------------------------------------------------------------------
#
#Response for player/24124. Successful:  <Response [200]>
#
#Total successful requests:  1794
#Completed :  69.00 %
#Elapsed time:  13164.26 s
#------------------------------------------------------------------------------
#
#Response for player/5420. Successful:  <Response [200]>
#
#Total successful requests:  1795
#Completed :  69.04 %
#Elapsed time:  13166.71 s
#------------------------------------------------------------------------------
#
#Response for player/1104703. Successful:  <Response [200]>
#
#Total successful requests:  1796
#Completed :  69.08 %
#Elapsed time:  13182.70 s
#------------------------------------------------------------------------------
#
#Response for player/24154. Successful:  <Response [200]>
#
#Total successful requests:  1797
#Completed :  69.12 %
#Elapsed time:  13191.62 s
#------------------------------------------------------------------------------
#
#Response for player/24920. Successful:  <Response [200]>
#
#Total successful requests:  1798
#Completed :  69.15 %
#Elapsed time:  13194.87 s
#------------------------------------------------------------------------------
#
#Response for player/236489. Successful:  <Response [200]>
#
#Total successful requests:  1799
#Completed :  69.19 %
#Elapsed time:  13202.73 s
#------------------------------------------------------------------------------
#
#Response for player/37701. Successful:  <Response [200]>
#
#Total successful requests:  1800
#Completed :  69.23 %
#Elapsed time:  13206.72 s
#------------------------------------------------------------------------------
#
#Response for page 0 Successful:  <Response [200]> 	=>
#

#list of players:  200
#Response for player/42051. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  1801
#Completed :  69.27 %
#Elapsed time:  13289.24 s
#------------------------------------------------------------------------------
#
#Response for player/38060. Successful:  <Response [200]>
#
#Total successful requests:  1802
#Completed :  69.31 %
#Elapsed time:  13298.18 s
#------------------------------------------------------------------------------
#
#Response for player/49852. Successful:  <Response [200]>
#
#Total successful requests:  1803
#Completed :  69.35 %
#Elapsed time:  13317.06 s
#------------------------------------------------------------------------------
#
#Response for player/46780. Successful:  <Response [200]>
#
#Total successful requests:  1804
#Completed :  69.38 %
#Elapsed time:  13329.81 s
#------------------------------------------------------------------------------
#
#Response for player/56066. Successful:  <Response [200]>
#
#Total successful requests:  1805
#Completed :  69.42 %
#Elapsed time:  13333.74 s
#------------------------------------------------------------------------------
#
#Response for player/56118. Successful:  <Response [200]>
#
#Total successful requests:  1806
#Completed :  69.46 %
#Elapsed time:  13342.11 s
#------------------------------------------------------------------------------
#
#Response for player/38409. Successful:  <Response [200]>
#
#Total successful requests:  1807
#Completed :  69.50 %
#Elapsed time:  13355.96 s
#------------------------------------------------------------------------------
#
#Response for player/402245. Successful:  <Response [200]>
#
#Total successful requests:  1808
#Completed :  69.54 %
#Elapsed time:  13373.80 s
#------------------------------------------------------------------------------
#
#Response for player/24689. Successful:  <Response [200]>
#
#Total successful requests:  1809
#Completed :  69.58 %
#Elapsed time:  13377.71 s
#------------------------------------------------------------------------------
#
#Response for player/51108. Successful:  <Response [200]>
#
#Total successful requests:  1810
#Completed :  69.62 %
#Elapsed time:  13384.25 s
#------------------------------------------------------------------------------
#
#Response for player/25429. Successful:  <Response [200]>
#
#Total successful requests:  1811
#Completed :  69.65 %
#Elapsed time:  13386.26 s
#------------------------------------------------------------------------------
#
#Response for player/26815. Successful:  <Response [200]>
#
#Total successful requests:  1812
#Completed :  69.69 %
#Elapsed time:  13388.89 s
#------------------------------------------------------------------------------
#
#Response for player/51899. Successful:  <Response [200]>
#
#Total successful requests:  1813
#Completed :  69.73 %
#Elapsed time:  13391.49 s
#------------------------------------------------------------------------------
#
#Response for player/320281. Successful:  <Response [200]>
#
#Total successful requests:  1814
#Completed :  69.77 %
#Elapsed time:  13397.78 s
#------------------------------------------------------------------------------
#
#Response for player/52300. Successful:  <Response [200]>
#
#Total successful requests:  1815
#Completed :  69.81 %
#Elapsed time:  13400.09 s
#------------------------------------------------------------------------------
#
#Response for player/541991. Successful:  <Response [200]>
#
#Total successful requests:  1816
#Completed :  69.85 %
#Elapsed time:  13418.18 s
#------------------------------------------------------------------------------
#
#Response for player/46075. Successful:  <Response [200]>
#
#Total successful requests:  1817
#Completed :  69.88 %
#Elapsed time:  13428.29 s
#------------------------------------------------------------------------------
#
#Response for player/25883. Successful:  <Response [200]>
#
#Total successful requests:  1818
#Completed :  69.92 %
#Elapsed time:  13431.40 s
#------------------------------------------------------------------------------
#
#Response for player/38120. Successful:  <Response [200]>
#
#Total successful requests:  1819
#Completed :  69.96 %
#Elapsed time:  13435.97 s
#------------------------------------------------------------------------------
#
#Response for player/33151. Successful:  <Response [200]>
#
#Total successful requests:  1820
#Completed :  70.00 %
#Elapsed time:  13449.92 s
#------------------------------------------------------------------------------
#
#Response for player/553800. Successful:  <Response [200]>
#
#Total successful requests:  1821
#Completed :  70.04 %
#Elapsed time:  13456.53 s
#------------------------------------------------------------------------------
#
#Response for player/39121. Successful:  <Response [200]>
#
#Total successful requests:  1822
#Completed :  70.08 %
#Elapsed time:  13458.63 s
#------------------------------------------------------------------------------
#
#Response for player/48809. Successful:  <Response [200]>
#
#Total successful requests:  1823
#Completed :  70.12 %
#Elapsed time:  13469.82 s
#------------------------------------------------------------------------------
#
#Response for player/14127. Successful:  <Response [200]>
#
#Total successful requests:  1824
#Completed :  70.15 %
#Elapsed time:  13480.20 s
#------------------------------------------------------------------------------
#
#Response for player/623104. Successful:  <Response [200]>
#
#Total successful requests:  1825
#Completed :  70.19 %
#Elapsed time:  13482.42 s
#------------------------------------------------------------------------------
#
#Response for player/41481. Successful:  <Response [200]>
#
#Total successful requests:  1826
#Completed :  70.23 %
#Elapsed time:  13486.40 s
#------------------------------------------------------------------------------
#
#Response for player/56101. Successful:  <Response [200]>
#
#Total successful requests:  1827
#Completed :  70.27 %
#Elapsed time:  13490.15 s
#------------------------------------------------------------------------------
#
#Response for player/38609. Successful:  <Response [200]>
#
#Total successful requests:  1828
#Completed :  70.31 %
#Elapsed time:  13491.69 s
#------------------------------------------------------------------------------
#
#Response for player/475281. Successful:  <Response [200]>
#
#Total successful requests:  1829
#Completed :  70.35 %
#Elapsed time:  13494.16 s
#------------------------------------------------------------------------------
#
#Response for player/22363. Successful:  <Response [200]>
#
#Total successful requests:  1830
#Completed :  70.38 %
#Elapsed time:  13505.55 s
#------------------------------------------------------------------------------
#
#Response for player/39881. Successful:  <Response [200]>
#
#Total successful requests:  1831
#Completed :  70.42 %
#Elapsed time:  13509.86 s
#------------------------------------------------------------------------------
#
#Response for player/26293. Successful:  <Response [200]>
#
#Total successful requests:  1832
#Completed :  70.46 %
#Elapsed time:  13515.25 s
#------------------------------------------------------------------------------
#
#Response for player/227712. Successful:  <Response [200]>
#
#Total successful requests:  1833
#Completed :  70.50 %
#Elapsed time:  13535.82 s
#------------------------------------------------------------------------------
#
#Response for player/446101. Successful:  <Response [200]>
#
#Total successful requests:  1834
#Completed :  70.54 %
#Elapsed time:  13540.36 s
#------------------------------------------------------------------------------
#
#Response for player/800675. Successful:  <Response [200]>
#
#Total successful requests:  1835
#Completed :  70.58 %
#Elapsed time:  13542.37 s
#------------------------------------------------------------------------------
#
#Response for player/23879. Successful:  <Response [200]>
#
#Total successful requests:  1836
#Completed :  70.62 %
#Elapsed time:  13543.47 s
#------------------------------------------------------------------------------
#
#Response for player/49624. Successful:  <Response [200]>
#
#Total successful requests:  1837
#Completed :  70.65 %
#Elapsed time:  13553.63 s
#------------------------------------------------------------------------------
#
#Response for player/23781. Successful:  <Response [200]>
#
#Total successful requests:  1838
#Completed :  70.69 %
#Elapsed time:  13557.38 s
#------------------------------------------------------------------------------
#
#Response for player/38404. Successful:  <Response [200]>
#
#Total successful requests:  1839
#Completed :  70.73 %
#Elapsed time:  13558.22 s
#------------------------------------------------------------------------------
#
#Response for player/401057. Successful:  <Response [200]>
#
#Total successful requests:  1840
#Completed :  70.77 %
#Elapsed time:  13564.72 s
#------------------------------------------------------------------------------
#
#Response for player/509107. Successful:  <Response [200]>
#
#Total successful requests:  1841
#Completed :  70.81 %
#Elapsed time:  13566.37 s
#------------------------------------------------------------------------------
#
#Response for player/22520. Successful:  <Response [200]>
#
#Total successful requests:  1842
#Completed :  70.85 %
#Elapsed time:  13569.02 s
#------------------------------------------------------------------------------
#
#Response for player/4923. Successful:  <Response [200]>
#
#Total successful requests:  1843
#Completed :  70.88 %
#Elapsed time:  13576.56 s
#------------------------------------------------------------------------------
#
#Response for player/45437. Successful:  <Response [200]>
#
#Total successful requests:  1844
#Completed :  70.92 %
#Elapsed time:  13580.95 s
#------------------------------------------------------------------------------
#
#Response for player/15380. Successful:  <Response [200]>
#
#Total successful requests:  1845
#Completed :  70.96 %
#Elapsed time:  13588.33 s
#------------------------------------------------------------------------------
#
#Response for player/25877. Successful:  <Response [200]>
#
#Total successful requests:  1846
#Completed :  71.00 %
#Elapsed time:  13602.40 s
#------------------------------------------------------------------------------
#
#Response for player/306982. Successful:  <Response [200]>
#
#Total successful requests:  1847
#Completed :  71.04 %
#Elapsed time:  13605.18 s
#------------------------------------------------------------------------------
#
#Response for player/23780. Successful:  <Response [200]>
#
#Total successful requests:  1848
#Completed :  71.08 %
#Elapsed time:  13611.01 s
#------------------------------------------------------------------------------
#
#Response for player/55602. Successful:  <Response [200]>
#
#Total successful requests:  1849
#Completed :  71.12 %
#Elapsed time:  13616.95 s
#------------------------------------------------------------------------------
#
#Response for player/629058. Successful:  <Response [200]>
#
#Total successful requests:  1850
#Completed :  71.15 %
#Elapsed time:  13624.21 s
#------------------------------------------------------------------------------
#
#Response for player/25106. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  1851
#Completed :  71.19 %
#Elapsed time:  13640.21 s
#------------------------------------------------------------------------------
#
#Response for player/276539. Successful:  <Response [200]>
#
#Total successful requests:  1852
#Completed :  71.23 %
#Elapsed time:  13642.12 s
#------------------------------------------------------------------------------
#
#Response for player/42428. Successful:  <Response [200]>
#
#Total successful requests:  1853
#Completed :  71.27 %
#Elapsed time:  13646.57 s
#------------------------------------------------------------------------------
#
#Response for player/52995. Successful:  <Response [200]>
#
#Total successful requests:  1854
#Completed :  71.31 %
#Elapsed time:  13654.52 s
#------------------------------------------------------------------------------
#
#Response for player/33958. Successful:  <Response [200]>
#
#Total successful requests:  1855
#Completed :  71.35 %
#Elapsed time:  13655.93 s
#------------------------------------------------------------------------------
#
#Response for player/52932. Successful:  <Response [200]>
#
#Total successful requests:  1856
#Completed :  71.38 %
#Elapsed time:  13657.77 s
#------------------------------------------------------------------------------
#
#Response for player/888455. Successful:  <Response [200]>
#
#Total successful requests:  1857
#Completed :  71.42 %
#Elapsed time:  13660.31 s
#------------------------------------------------------------------------------
#
#Response for player/50852. Successful:  <Response [200]>
#
#Total successful requests:  1858
#Completed :  71.46 %
#Elapsed time:  13665.24 s
#------------------------------------------------------------------------------
#
#Response for player/364343. Successful:  <Response [200]>
#
#Total successful requests:  1859
#Completed :  71.50 %
#Elapsed time:  13673.46 s
#------------------------------------------------------------------------------
#
#Response for player/12461. Successful:  <Response [200]>
#
#Total successful requests:  1860
#Completed :  71.54 %
#Elapsed time:  13679.37 s
#------------------------------------------------------------------------------
#
#Response for player/24897. Successful:  <Response [200]>
#
#Total successful requests:  1861
#Completed :  71.58 %
#Elapsed time:  13699.26 s
#------------------------------------------------------------------------------
#
#Response for player/52051. Successful:  <Response [200]>
#
#Total successful requests:  1862
#Completed :  71.62 %
#Elapsed time:  13713.51 s
#------------------------------------------------------------------------------
#
#Response for player/1161022. Successful:  <Response [200]>
#
#Total successful requests:  1863
#Completed :  71.65 %
#Elapsed time:  13720.67 s
#------------------------------------------------------------------------------
#
#Response for player/30157. Successful:  <Response [200]>
#
#Total successful requests:  1864
#Completed :  71.69 %
#Elapsed time:  13721.87 s
#------------------------------------------------------------------------------
#
#Response for player/55591. Successful:  <Response [200]>
#
#Total successful requests:  1865
#Completed :  71.73 %
#Elapsed time:  13730.85 s
#------------------------------------------------------------------------------
#
#Response for player/274921. Successful:  <Response [200]>
#
#Total successful requests:  1866
#Completed :  71.77 %
#Elapsed time:  13740.19 s
#------------------------------------------------------------------------------
#
#Response for player/49861. Successful:  <Response [200]>
#
#Total successful requests:  1867
#Completed :  71.81 %
#Elapsed time:  13744.71 s
#------------------------------------------------------------------------------
#
#Response for player/43041. Successful:  <Response [200]>
#
#Total successful requests:  1868
#Completed :  71.85 %
#Elapsed time:  13754.41 s
#------------------------------------------------------------------------------
#
#Response for player/25113. Successful:  <Response [200]>
#
#Total successful requests:  1869
#Completed :  71.88 %
#Elapsed time:  13757.18 s
#------------------------------------------------------------------------------
#
#Response for player/380974. Successful:  <Response [200]>
#
#Total successful requests:  1870
#Completed :  71.92 %
#Elapsed time:  13766.64 s
#------------------------------------------------------------------------------
#
#Response for player/22380. Successful:  <Response [200]>
#
#Total successful requests:  1871
#Completed :  71.96 %
#Elapsed time:  13771.37 s
#------------------------------------------------------------------------------
#
#Response for player/450075. Successful:  <Response [200]>
#
#Total successful requests:  1872
#Completed :  72.00 %
#Elapsed time:  13772.94 s
#------------------------------------------------------------------------------
#
#Response for player/310519. Successful:  <Response [200]>
#
#Total successful requests:  1873
#Completed :  72.04 %
#Elapsed time:  13780.76 s
#------------------------------------------------------------------------------
#
#Response for player/625383. Successful:  <Response [200]>
#
#Total successful requests:  1874
#Completed :  72.08 %
#Elapsed time:  13783.61 s
#------------------------------------------------------------------------------
#
#Response for player/51485. Successful:  <Response [200]>
#
#Total successful requests:  1875
#Completed :  72.12 %
#Elapsed time:  13790.92 s
#------------------------------------------------------------------------------
#
#Response for player/37255. Successful:  <Response [200]>
#
#Total successful requests:  1876
#Completed :  72.15 %
#Elapsed time:  13802.35 s
#------------------------------------------------------------------------------
#
#Response for player/55938. Successful:  <Response [200]>
#
#Total successful requests:  1877
#Completed :  72.19 %
#Elapsed time:  13804.02 s
#------------------------------------------------------------------------------
#
#Response for player/55551. Successful:  <Response [200]>
#
#Total successful requests:  1878
#Completed :  72.23 %
#Elapsed time:  13811.12 s
#------------------------------------------------------------------------------
#
#Response for player/52413. Successful:  <Response [200]>
#
#Total successful requests:  1879
#Completed :  72.27 %
#Elapsed time:  13831.27 s
#------------------------------------------------------------------------------
#
#Response for player/220613. Successful:  <Response [200]>
#
#Total successful requests:  1880
#Completed :  72.31 %
#Elapsed time:  13832.99 s
#------------------------------------------------------------------------------
#
#Response for player/42624. Successful:  <Response [200]>
#
#Total successful requests:  1881
#Completed :  72.35 %
#Elapsed time:  13834.57 s
#------------------------------------------------------------------------------
#
#Response for player/34019. Successful:  <Response [200]>
#
#Total successful requests:  1882
#Completed :  72.38 %
#Elapsed time:  13844.33 s
#------------------------------------------------------------------------------
#
#Response for player/873769. Successful:  <Response [200]>
#
#Total successful requests:  1883
#Completed :  72.42 %
#Elapsed time:  13873.18 s
#------------------------------------------------------------------------------
#
#Response for player/25606. Successful:  <Response [200]>
#
#Total successful requests:  1884
#Completed :  72.46 %
#Elapsed time:  13880.27 s
#------------------------------------------------------------------------------
#
#Response for player/43307. Successful:  <Response [200]>
#
#Total successful requests:  1885
#Completed :  72.50 %
#Elapsed time:  13886.58 s
#------------------------------------------------------------------------------
#
#Response for player/492924. Successful:  <Response [200]>
#
#Total successful requests:  1886
#Completed :  72.54 %
#Elapsed time:  13891.80 s
#------------------------------------------------------------------------------
#
#Response for player/50855. Successful:  <Response [200]>
#
#Total successful requests:  1887
#Completed :  72.58 %
#Elapsed time:  13909.21 s
#------------------------------------------------------------------------------
#
#Response for player/43707. Successful:  <Response [200]>
#
#Total successful requests:  1888
#Completed :  72.62 %
#Elapsed time:  13921.57 s
#------------------------------------------------------------------------------
#
#Response for player/36179. Successful:  <Response [200]>
#
#Total successful requests:  1889
#Completed :  72.65 %
#Elapsed time:  13923.37 s
#------------------------------------------------------------------------------
#
#Response for player/662973. Successful:  <Response [200]>
#
#Total successful requests:  1890
#Completed :  72.69 %
#Elapsed time:  13931.24 s
#------------------------------------------------------------------------------
#
#Response for player/48993. Successful:  <Response [200]>
#
#Total successful requests:  1891
#Completed :  72.73 %
#Elapsed time:  13940.91 s
#------------------------------------------------------------------------------
#
#Response for player/494133. Successful:  <Response [200]>
#
#Total successful requests:  1892
#Completed :  72.77 %
#Elapsed time:  13942.21 s
#------------------------------------------------------------------------------
#
#Response for player/14236. Successful:  <Response [200]>
#
#Total successful requests:  1893
#Completed :  72.81 %
#Elapsed time:  13954.02 s
#------------------------------------------------------------------------------
#
#Response for player/24227. Successful:  <Response [200]>
#
#Total successful requests:  1894
#Completed :  72.85 %
#Elapsed time:  13959.66 s
#------------------------------------------------------------------------------
#
#Response for player/40567. Successful:  <Response [200]>
#
#Total successful requests:  1895
#Completed :  72.88 %
#Elapsed time:  13964.45 s
#------------------------------------------------------------------------------
#
#Response for player/24695. Successful:  <Response [200]>
#
#Total successful requests:  1896
#Completed :  72.92 %
#Elapsed time:  13972.65 s
#------------------------------------------------------------------------------
#
#Response for player/49206. Successful:  <Response [200]>
#
#Total successful requests:  1897
#Completed :  72.96 %
#Elapsed time:  13975.99 s
#------------------------------------------------------------------------------
#
#Response for player/52210. Successful:  <Response [200]>
#
#Total successful requests:  1898
#Completed :  73.00 %
#Elapsed time:  13984.92 s
#------------------------------------------------------------------------------
#
#Response for player/37530. Successful:  <Response [200]>
#
#Total successful requests:  1899
#Completed :  73.04 %
#Elapsed time:  13986.35 s
#------------------------------------------------------------------------------
#
#Response for player/1077309. Successful:  <Response [200]>
#
#Total successful requests:  1900
#Completed :  73.08 %
#Elapsed time:  13991.13 s
#------------------------------------------------------------------------------
#
#Response for player/16262. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  1901
#Completed :  73.12 %
#Elapsed time:  14002.60 s
#------------------------------------------------------------------------------
#
#Response for player/470917. Successful:  <Response [200]>
#
#Total successful requests:  1902
#Completed :  73.15 %
#Elapsed time:  14013.73 s
#------------------------------------------------------------------------------
#
#Response for player/784373. Successful:  <Response [200]>
#
#Total successful requests:  1903
#Completed :  73.19 %
#Elapsed time:  14038.51 s
#------------------------------------------------------------------------------
#
#Response for player/56070. Successful:  <Response [200]>
#
#Total successful requests:  1904
#Completed :  73.23 %
#Elapsed time:  14061.86 s
#------------------------------------------------------------------------------
#
#Response for player/20193. Successful:  <Response [200]>
#
#Total successful requests:  1905
#Completed :  73.27 %
#Elapsed time:  14067.39 s
#------------------------------------------------------------------------------
#
#Response for player/387845. Successful:  <Response [200]>
#
#Total successful requests:  1906
#Completed :  73.31 %
#Elapsed time:  14073.05 s
#------------------------------------------------------------------------------
#
#Response for player/43909. Successful:  <Response [200]>
#
#Total successful requests:  1907
#Completed :  73.35 %
#Elapsed time:  14077.08 s
#------------------------------------------------------------------------------
#
#Response for player/36180. Successful:  <Response [200]>
#
#Total successful requests:  1908
#Completed :  73.38 %
#Elapsed time:  14088.29 s
#------------------------------------------------------------------------------
#
#Response for player/25880. Successful:  <Response [200]>
#
#Total successful requests:  1909
#Completed :  73.42 %
#Elapsed time:  14096.58 s
#------------------------------------------------------------------------------
#
#Response for player/519070. Successful:  <Response [200]>
#
#Total successful requests:  1910
#Completed :  73.46 %
#Elapsed time:  14103.60 s
#------------------------------------------------------------------------------
#
#Response for player/482478. Successful:  <Response [200]>
#
#Total successful requests:  1911
#Completed :  73.50 %
#Elapsed time:  14123.58 s
#------------------------------------------------------------------------------
#
#Response for player/49013. Successful:  <Response [200]>
#
#Total successful requests:  1912
#Completed :  73.54 %
#Elapsed time:  14131.37 s
#------------------------------------------------------------------------------
#
#Response for player/23816. Successful:  <Response [200]>
#
#Total successful requests:  1913
#Completed :  73.58 %
#Elapsed time:  14141.73 s
#------------------------------------------------------------------------------
#
#Response for player/55933. Successful:  <Response [200]>
#
#Total successful requests:  1914
#Completed :  73.62 %
#Elapsed time:  14143.74 s
#------------------------------------------------------------------------------
#
#Response for player/15522. Successful:  <Response [200]>
#
#Total successful requests:  1915
#Completed :  73.65 %
#Elapsed time:  14149.62 s
#------------------------------------------------------------------------------
#
#Response for player/784375. Successful:  <Response [200]>
#
#Total successful requests:  1916
#Completed :  73.69 %
#Elapsed time:  14168.19 s
#------------------------------------------------------------------------------
#
#Response for player/24149. Successful:  <Response [200]>
#
#Total successful requests:  1917
#Completed :  73.73 %
#Elapsed time:  14174.92 s
#------------------------------------------------------------------------------
#
#Response for player/466610. Successful:  <Response [200]>
#
#Total successful requests:  1918
#Completed :  73.77 %
#Elapsed time:  14181.39 s
#------------------------------------------------------------------------------
#
#Response for player/6518. Successful:  <Response [200]>
#
#Total successful requests:  1919
#Completed :  73.81 %
#Elapsed time:  14196.76 s
#------------------------------------------------------------------------------
#
#Response for player/827051. Successful:  <Response [200]>
#
#Total successful requests:  1920
#Completed :  73.85 %
#Elapsed time:  14213.39 s
#------------------------------------------------------------------------------
#
#Response for player/7002. Successful:  <Response [200]>
#
#Total successful requests:  1921
#Completed :  73.88 %
#Elapsed time:  14255.79 s
#------------------------------------------------------------------------------
#
#Response for player/24770. Successful:  <Response [200]>
#
#Total successful requests:  1922
#Completed :  73.92 %
#Elapsed time:  14261.76 s
#------------------------------------------------------------------------------
#
#Response for player/38253. Successful:  <Response [200]>
#
#Total successful requests:  1923
#Completed :  73.96 %
#Elapsed time:  14268.99 s
#------------------------------------------------------------------------------
#
#Response for player/342182. Successful:  <Response [200]>
#
#Total successful requests:  1924
#Completed :  74.00 %
#Elapsed time:  14273.88 s
#------------------------------------------------------------------------------
#
#Response for player/1070173. Successful:  <Response [200]>
#
#Total successful requests:  1925
#Completed :  74.04 %
#Elapsed time:  14276.04 s
#------------------------------------------------------------------------------
#
#Response for player/671823. Successful:  <Response [200]>
#
#Total successful requests:  1926
#Completed :  74.08 %
#Elapsed time:  14287.11 s
#------------------------------------------------------------------------------
#
#Response for player/34086. Successful:  <Response [200]>
#
#Total successful requests:  1927
#Completed :  74.12 %
#Elapsed time:  14288.34 s
#------------------------------------------------------------------------------
#
#Response for player/807535. Successful:  <Response [200]>
#
#Total successful requests:  1928
#Completed :  74.15 %
#Elapsed time:  14298.12 s
#------------------------------------------------------------------------------
#
#Response for player/8526. Successful:  <Response [200]>
#
#Total successful requests:  1929
#Completed :  74.19 %
#Elapsed time:  14303.55 s
#------------------------------------------------------------------------------
#
#Response for player/48117. Successful:  <Response [200]>
#
#Total successful requests:  1930
#Completed :  74.23 %
#Elapsed time:  14304.41 s
#------------------------------------------------------------------------------
#
#Response for player/498440. Successful:  <Response [200]>
#
#Total successful requests:  1931
#Completed :  74.27 %
#Elapsed time:  14306.71 s
#------------------------------------------------------------------------------
#
#Response for player/244639. Successful:  <Response [200]>
#
#Total successful requests:  1932
#Completed :  74.31 %
#Elapsed time:  14317.24 s
#------------------------------------------------------------------------------
#
#Response for player/5569. Successful:  <Response [200]>
#
#Total successful requests:  1933
#Completed :  74.35 %
#Elapsed time:  14320.72 s
#------------------------------------------------------------------------------
#
#Response for player/55518. Successful:  <Response [200]>
#
#Total successful requests:  1934
#Completed :  74.38 %
#Elapsed time:  14327.55 s
#------------------------------------------------------------------------------
#
#Response for player/307234. Successful:  <Response [200]>
#
#Total successful requests:  1935
#Completed :  74.42 %
#Elapsed time:  14328.70 s
#------------------------------------------------------------------------------
#
#Response for player/40577. Successful:  <Response [200]>
#
#Total successful requests:  1936
#Completed :  74.46 %
#Elapsed time:  14333.67 s
#------------------------------------------------------------------------------
#
#Response for player/24613. Successful:  <Response [200]>
#
#Total successful requests:  1937
#Completed :  74.50 %
#Elapsed time:  14334.81 s
#------------------------------------------------------------------------------
#
#Response for player/16370. Successful:  <Response [200]>
#
#Total successful requests:  1938
#Completed :  74.54 %
#Elapsed time:  14343.72 s
#------------------------------------------------------------------------------
#
#Response for player/41261. Successful:  <Response [200]>
#
#Total successful requests:  1939
#Completed :  74.58 %
#Elapsed time:  14345.68 s
#------------------------------------------------------------------------------
#
#Response for player/41299. Successful:  <Response [200]>
#
#Total successful requests:  1940
#Completed :  74.62 %
#Elapsed time:  14347.17 s
#------------------------------------------------------------------------------
#
#Response for player/1005369. Successful:  <Response [200]>
#
#Total successful requests:  1941
#Completed :  74.65 %
#Elapsed time:  14361.98 s
#------------------------------------------------------------------------------
#
#Response for player/304735. Successful:  <Response [200]>
#
#Total successful requests:  1942
#Completed :  74.69 %
#Elapsed time:  14369.04 s
#------------------------------------------------------------------------------
#
#Response for player/56040. Successful:  <Response [200]>
#
#Total successful requests:  1943
#Completed :  74.73 %
#Elapsed time:  14383.37 s
#------------------------------------------------------------------------------
#
#Response for player/331375. Successful:  <Response [200]>
#
#Total successful requests:  1944
#Completed :  74.77 %
#Elapsed time:  14387.08 s
#------------------------------------------------------------------------------
#
#Response for player/56096. Successful:  <Response [200]>
#
#Total successful requests:  1945
#Completed :  74.81 %
#Elapsed time:  14391.02 s
#------------------------------------------------------------------------------
#
#Response for player/20235. Successful:  <Response [200]>
#
#Total successful requests:  1946
#Completed :  74.85 %
#Elapsed time:  14417.90 s
#------------------------------------------------------------------------------
#
#Response for player/303420. Successful:  <Response [200]>
#
#Total successful requests:  1947
#Completed :  74.88 %
#Elapsed time:  14425.91 s
#------------------------------------------------------------------------------
#
#Response for player/23793. Successful:  <Response [200]>
#
#Total successful requests:  1948
#Completed :  74.92 %
#Elapsed time:  14448.21 s
#------------------------------------------------------------------------------
#
#Response for player/21611. Successful:  <Response [200]>
#
#Total successful requests:  1949
#Completed :  74.96 %
#Elapsed time:  14452.80 s
#------------------------------------------------------------------------------
#
#Response for player/35627. Successful:  <Response [200]>
#
#Total successful requests:  1950
#Completed :  75.00 %
#Elapsed time:  14454.34 s
#------------------------------------------------------------------------------
#
#Response for player/463217. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  1951
#Completed :  75.04 %
#Elapsed time:  14458.34 s
#------------------------------------------------------------------------------
#
#Response for player/22361. Successful:  <Response [200]>
#
#Total successful requests:  1952
#Completed :  75.08 %
#Elapsed time:  14462.82 s
#------------------------------------------------------------------------------
#
#Response for player/348154. Successful:  <Response [200]>
#
#Total successful requests:  1953
#Completed :  75.12 %
#Elapsed time:  14468.59 s
#------------------------------------------------------------------------------
#
#Response for player/518097. Successful:  <Response [200]>
#
#Total successful requests:  1954
#Completed :  75.15 %
#Elapsed time:  14477.06 s
#------------------------------------------------------------------------------
#
#Response for player/25598. Successful:  <Response [200]>
#
#Total successful requests:  1955
#Completed :  75.19 %
#Elapsed time:  14492.49 s
#------------------------------------------------------------------------------
#
#Response for player/39011. Successful:  <Response [200]>
#
#Total successful requests:  1956
#Completed :  75.23 %
#Elapsed time:  14498.98 s
#------------------------------------------------------------------------------
#
#Response for player/48321. Successful:  <Response [200]>
#
#Total successful requests:  1957
#Completed :  75.27 %
#Elapsed time:  14502.76 s
#------------------------------------------------------------------------------
#
#Response for player/9323. Successful:  <Response [200]>
#
#Total successful requests:  1958
#Completed :  75.31 %
#Elapsed time:  14508.82 s
#------------------------------------------------------------------------------
#
#Response for player/10712. Successful:  <Response [200]>
#
#Total successful requests:  1959
#Completed :  75.35 %
#Elapsed time:  14515.11 s
#------------------------------------------------------------------------------
#
#Response for player/211855. Successful:  <Response [200]>
#
#Total successful requests:  1960
#Completed :  75.38 %
#Elapsed time:  14534.17 s
#------------------------------------------------------------------------------
#
#Response for player/23863. Successful:  <Response [200]>
#
#Total successful requests:  1961
#Completed :  75.42 %
#Elapsed time:  14551.30 s
#------------------------------------------------------------------------------
#
#Response for player/55406. Successful:  <Response [200]>
#
#Total successful requests:  1962
#Completed :  75.46 %
#Elapsed time:  14576.44 s
#------------------------------------------------------------------------------
#
#Response for player/252869. Successful:  <Response [200]>
#
#Total successful requests:  1963
#Completed :  75.50 %
#Elapsed time:  14589.30 s
#------------------------------------------------------------------------------
#
#Response for player/428366. Successful:  <Response [200]>
#
#Total successful requests:  1964
#Completed :  75.54 %
#Elapsed time:  14606.58 s
#------------------------------------------------------------------------------
#
#Response for player/6472. Successful:  <Response [200]>
#
#Total successful requests:  1965
#Completed :  75.58 %
#Elapsed time:  14621.48 s
#------------------------------------------------------------------------------
#
#Response for player/41282. Successful:  <Response [200]>
#
#Total successful requests:  1966
#Completed :  75.62 %
#Elapsed time:  14642.85 s
#------------------------------------------------------------------------------
#
#Response for player/42044. Successful:  <Response [200]>
#
#Total successful requests:  1967
#Completed :  75.65 %
#Elapsed time:  14650.93 s
#------------------------------------------------------------------------------
#
#Response for player/806241. Successful:  <Response [200]>
#
#Total successful requests:  1968
#Completed :  75.69 %
#Elapsed time:  14654.35 s
#------------------------------------------------------------------------------
#
#Response for player/55669. Successful:  <Response [200]>
#
#Total successful requests:  1969
#Completed :  75.73 %
#Elapsed time:  14657.24 s
#------------------------------------------------------------------------------
#
#Response for player/23887. Successful:  <Response [200]>
#
#Total successful requests:  1970
#Completed :  75.77 %
#Elapsed time:  14684.97 s
#------------------------------------------------------------------------------
#
#Response for player/38711. Successful:  <Response [200]>
#
#Total successful requests:  1971
#Completed :  75.81 %
#Elapsed time:  14696.36 s
#------------------------------------------------------------------------------
#
#Response for player/38920. Successful:  <Response [200]>
#
#Total successful requests:  1972
#Completed :  75.85 %
#Elapsed time:  14703.03 s
#------------------------------------------------------------------------------
#
#Response for player/56165. Successful:  <Response [200]>
#
#Total successful requests:  1973
#Completed :  75.88 %
#Elapsed time:  14707.73 s
#------------------------------------------------------------------------------
#
#Response for player/38966. Successful:  <Response [200]>
#
#Total successful requests:  1974
#Completed :  75.92 %
#Elapsed time:  14711.51 s
#------------------------------------------------------------------------------
#
#Response for player/222728. Successful:  <Response [200]>
#
#Total successful requests:  1975
#Completed :  75.96 %
#Elapsed time:  14717.96 s
#------------------------------------------------------------------------------
#
#Response for player/437927. Successful:  <Response [200]>
#
#Total successful requests:  1976
#Completed :  76.00 %
#Elapsed time:  14725.89 s
#------------------------------------------------------------------------------
#
#Response for player/51431. Successful:  <Response [200]>
#
#Total successful requests:  1977
#Completed :  76.04 %
#Elapsed time:  14739.73 s
#------------------------------------------------------------------------------
#
#Response for player/36590. Successful:  <Response [200]>
#
#Total successful requests:  1978
#Completed :  76.08 %
#Elapsed time:  14743.95 s
#------------------------------------------------------------------------------
#
#Response for player/4151. Successful:  <Response [200]>
#
#Total successful requests:  1979
#Completed :  76.12 %
#Elapsed time:  14747.43 s
#------------------------------------------------------------------------------
#
#Response for player/26966. Successful:  <Response [200]>
#
#Total successful requests:  1980
#Completed :  76.15 %
#Elapsed time:  14751.35 s
#------------------------------------------------------------------------------
#
#Response for player/10839. Successful:  <Response [200]>
#
#Total successful requests:  1981
#Completed :  76.19 %
#Elapsed time:  14756.47 s
#------------------------------------------------------------------------------
#
#Response for player/36825. Successful:  <Response [200]>
#
#Total successful requests:  1982
#Completed :  76.23 %
#Elapsed time:  14760.65 s
#------------------------------------------------------------------------------
#
#Response for player/51784. Successful:  <Response [200]>
#
#Total successful requests:  1983
#Completed :  76.27 %
#Elapsed time:  14762.28 s
#------------------------------------------------------------------------------
#
#Response for player/537124. Successful:  <Response [200]>
#
#Total successful requests:  1984
#Completed :  76.31 %
#Elapsed time:  14769.16 s
#------------------------------------------------------------------------------
#
#Response for player/37245. Successful:  <Response [200]>
#
#Total successful requests:  1985
#Completed :  76.35 %
#Elapsed time:  14778.52 s
#------------------------------------------------------------------------------
#
#Response for player/52076. Successful:  <Response [200]>
#
#Total successful requests:  1986
#Completed :  76.38 %
#Elapsed time:  14780.53 s
#------------------------------------------------------------------------------
#
#Response for player/23777. Successful:  <Response [200]>
#
#Total successful requests:  1987
#Completed :  76.42 %
#Elapsed time:  14784.13 s
#------------------------------------------------------------------------------
#
#Response for player/6235. Successful:  <Response [200]>
#
#Total successful requests:  1988
#Completed :  76.46 %
#Elapsed time:  14793.38 s
#------------------------------------------------------------------------------
#
#Response for player/49634. Successful:  <Response [200]>
#
#Total successful requests:  1989
#Completed :  76.50 %
#Elapsed time:  14795.71 s
#------------------------------------------------------------------------------
#
#Response for player/25955. Successful:  <Response [200]>
#
#Total successful requests:  1990
#Completed :  76.54 %
#Elapsed time:  14801.66 s
#------------------------------------------------------------------------------
#
#Response for player/23900. Successful:  <Response [200]>
#
#Total successful requests:  1991
#Completed :  76.58 %
#Elapsed time:  14812.33 s
#------------------------------------------------------------------------------
#
#Response for player/260519. Successful:  <Response [200]>
#
#Total successful requests:  1992
#Completed :  76.62 %
#Elapsed time:  14819.93 s
#------------------------------------------------------------------------------
#
#Response for player/43776. Successful:  <Response [200]>
#
#Total successful requests:  1993
#Completed :  76.65 %
#Elapsed time:  14834.46 s
#------------------------------------------------------------------------------
#
#Response for player/25556. Successful:  <Response [200]>
#
#Total successful requests:  1994
#Completed :  76.69 %
#Elapsed time:  14842.55 s
#------------------------------------------------------------------------------
#
#Response for player/278496. Successful:  <Response [200]>
#
#Total successful requests:  1995
#Completed :  76.73 %
#Elapsed time:  14846.48 s
#------------------------------------------------------------------------------
#
#Response for player/55276. Successful:  <Response [200]>
#
#Total successful requests:  1996
#Completed :  76.77 %
#Elapsed time:  14851.06 s
#------------------------------------------------------------------------------
#
#Response for player/447261. Successful:  <Response [200]>
#
#Total successful requests:  1997
#Completed :  76.81 %
#Elapsed time:  14855.09 s
#------------------------------------------------------------------------------
#
#Response for player/40043. Successful:  <Response [200]>
#
#Total successful requests:  1998
#Completed :  76.85 %
#Elapsed time:  14861.88 s
#------------------------------------------------------------------------------
#
#Response for player/4916. Successful:  <Response [200]>
#
#Total successful requests:  1999
#Completed :  76.88 %
#Elapsed time:  14863.52 s
#------------------------------------------------------------------------------
#
#Response for player/36826. Successful:  <Response [200]>
#
#Total successful requests:  2000
#Completed :  76.92 %
#Elapsed time:  14867.46 s
#------------------------------------------------------------------------------
#
#Response for page 1 Successful:  <Response [200]> 	=>
#

#list of players:  200
#Response for player/48450. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  2001
#Completed :  76.96 %
#Elapsed time:  14925.59 s
#------------------------------------------------------------------------------
#
#Response for player/290727. Successful:  <Response [200]>
#
#Total successful requests:  2002
#Completed :  77.00 %
#Elapsed time:  14932.41 s
#------------------------------------------------------------------------------
#
#Response for player/55882. Successful:  <Response [200]>
#
#Total successful requests:  2003
#Completed :  77.04 %
#Elapsed time:  14940.17 s
#------------------------------------------------------------------------------
#
#Response for player/45419. Successful:  <Response [200]>
#
#Total successful requests:  2004
#Completed :  77.08 %
#Elapsed time:  14943.50 s
#------------------------------------------------------------------------------
#
#Response for player/25535. Successful:  <Response [200]>
#
#Total successful requests:  2005
#Completed :  77.12 %
#Elapsed time:  14958.09 s
#------------------------------------------------------------------------------
#
#Response for player/40880. Successful:  <Response [200]>
#
#Total successful requests:  2006
#Completed :  77.15 %
#Elapsed time:  14965.79 s
#------------------------------------------------------------------------------
#
#Response for player/6022. Successful:  <Response [200]>
#
#Total successful requests:  2007
#Completed :  77.19 %
#Elapsed time:  14967.69 s
#------------------------------------------------------------------------------
#
#Response for player/38005. Successful:  <Response [200]>
#
#Total successful requests:  2008
#Completed :  77.23 %
#Elapsed time:  14973.05 s
#------------------------------------------------------------------------------
#
#Response for player/23962. Successful:  <Response [200]>
#
#Total successful requests:  2009
#Completed :  77.27 %
#Elapsed time:  14982.80 s
#------------------------------------------------------------------------------
#
#Response for player/24261. Successful:  <Response [200]>
#
#Total successful requests:  2010
#Completed :  77.31 %
#Elapsed time:  14990.82 s
#------------------------------------------------------------------------------
#
#Response for player/232444. Successful:  <Response [200]>
#
#Total successful requests:  2011
#Completed :  77.35 %
#Elapsed time:  14996.92 s
#------------------------------------------------------------------------------
#
#Response for player/25604. Successful:  <Response [200]>
#
#Total successful requests:  2012
#Completed :  77.38 %
#Elapsed time:  15008.67 s
#------------------------------------------------------------------------------
#
#Response for player/377639. Successful:  <Response [200]>
#
#Total successful requests:  2013
#Completed :  77.42 %
#Elapsed time:  15029.81 s
#------------------------------------------------------------------------------
#
#Response for player/307652. Successful:  <Response [200]>
#
#Total successful requests:  2014
#Completed :  77.46 %
#Elapsed time:  15040.76 s
#------------------------------------------------------------------------------
#
#Response for player/364302. Successful:  <Response [200]>
#
#Total successful requests:  2015
#Completed :  77.50 %
#Elapsed time:  15064.28 s
#------------------------------------------------------------------------------
#
#Response for player/1072485. Successful:  <Response [200]>
#
#Total successful requests:  2016
#Completed :  77.54 %
#Elapsed time:  15068.84 s
#------------------------------------------------------------------------------
#
#Response for player/696143. Successful:  <Response [200]>
#
#Total successful requests:  2017
#Completed :  77.58 %
#Elapsed time:  15089.46 s
#------------------------------------------------------------------------------
#
#Response for player/585083. Successful:  <Response [200]>
#
#Total successful requests:  2018
#Completed :  77.62 %
#Elapsed time:  15092.57 s
#------------------------------------------------------------------------------
#
#Response for player/373439. Successful:  <Response [200]>
#
#Total successful requests:  2019
#Completed :  77.65 %
#Elapsed time:  15098.80 s
#------------------------------------------------------------------------------
#
#Response for player/56238. Successful:  <Response [200]>
#
#Total successful requests:  2020
#Completed :  77.69 %
#Elapsed time:  15108.25 s
#------------------------------------------------------------------------------
#
#Response for player/25132. Successful:  <Response [200]>
#
#Total successful requests:  2021
#Completed :  77.73 %
#Elapsed time:  15122.06 s
#------------------------------------------------------------------------------
#
#Response for player/940593. Successful:  <Response [200]>
#
#Total successful requests:  2022
#Completed :  77.77 %
#Elapsed time:  15138.82 s
#------------------------------------------------------------------------------
#
#Response for player/39006. Successful:  <Response [200]>
#
#Total successful requests:  2023
#Completed :  77.81 %
#Elapsed time:  15156.58 s
#------------------------------------------------------------------------------
#
#Response for player/431909. Successful:  <Response [200]>
#
#Total successful requests:  2024
#Completed :  77.85 %
#Elapsed time:  15168.16 s
#------------------------------------------------------------------------------
#
#Response for player/764321. Successful:  <Response [200]>
#
#Total successful requests:  2025
#Completed :  77.88 %
#Elapsed time:  15179.13 s
#------------------------------------------------------------------------------
#
#Response for player/24837. Successful:  <Response [200]>
#
#Total successful requests:  2026
#Completed :  77.92 %
#Elapsed time:  15185.63 s
#------------------------------------------------------------------------------
#
#Response for player/24844. Successful:  <Response [200]>
#
#Total successful requests:  2027
#Completed :  77.96 %
#Elapsed time:  15194.75 s
#------------------------------------------------------------------------------
#
#Response for player/4534. Successful:  <Response [200]>
#
#Total successful requests:  2028
#Completed :  78.00 %
#Elapsed time:  15200.76 s
#------------------------------------------------------------------------------
#
#Response for player/27591. Successful:  <Response [200]>
#
#Total successful requests:  2029
#Completed :  78.04 %
#Elapsed time:  15211.42 s
#------------------------------------------------------------------------------
#
#Response for player/5139. Successful:  <Response [200]>
#
#Total successful requests:  2030
#Completed :  78.08 %
#Elapsed time:  15217.49 s
#------------------------------------------------------------------------------
#
#Response for player/40369. Successful:  <Response [200]>
#
#Total successful requests:  2031
#Completed :  78.12 %
#Elapsed time:  15218.65 s
#------------------------------------------------------------------------------
#
#Response for player/14302. Successful:  <Response [200]>
#
#Total successful requests:  2032
#Completed :  78.15 %
#Elapsed time:  15225.20 s
#------------------------------------------------------------------------------
#
#Response for player/422871. Successful:  <Response [200]>
#
#Total successful requests:  2033
#Completed :  78.19 %
#Elapsed time:  15226.45 s
#------------------------------------------------------------------------------
#
#Response for player/49359. Successful:  <Response [200]>
#
#Total successful requests:  2034
#Completed :  78.23 %
#Elapsed time:  15228.41 s
#------------------------------------------------------------------------------
#
#Response for player/539548. Successful:  <Response [200]>
#
#Total successful requests:  2035
#Completed :  78.27 %
#Elapsed time:  15232.37 s
#------------------------------------------------------------------------------
#
#Response for player/30149. Successful:  <Response [200]>
#
#Total successful requests:  2036
#Completed :  78.31 %
#Elapsed time:  15235.95 s
#------------------------------------------------------------------------------
#
#Response for player/6452. Successful:  <Response [200]>
#
#Total successful requests:  2037
#Completed :  78.35 %
#Elapsed time:  15256.22 s
#------------------------------------------------------------------------------
#
#Response for player/398513. Successful:  <Response [200]>
#
#Total successful requests:  2038
#Completed :  78.38 %
#Elapsed time:  15261.53 s
#------------------------------------------------------------------------------
#
#Response for player/50205. Successful:  <Response [200]>
#
#Total successful requests:  2039
#Completed :  78.42 %
#Elapsed time:  15265.97 s
#------------------------------------------------------------------------------
#
#Response for player/33152. Successful:  <Response [200]>
#
#Total successful requests:  2040
#Completed :  78.46 %
#Elapsed time:  15269.81 s
#------------------------------------------------------------------------------
#
#Response for player/547085. Successful:  <Response [200]>
#
#Total successful requests:  2041
#Completed :  78.50 %
#Elapsed time:  15287.39 s
#------------------------------------------------------------------------------
#
#Response for player/33952. Successful:  <Response [200]>
#
#Total successful requests:  2042
#Completed :  78.54 %
#Elapsed time:  15288.67 s
#------------------------------------------------------------------------------
#
#Response for player/24129. Successful:  <Response [200]>
#
#Total successful requests:  2043
#Completed :  78.58 %
#Elapsed time:  15295.54 s
#------------------------------------------------------------------------------
#
#Response for player/21548. Successful:  <Response [200]>
#
#Total successful requests:  2044
#Completed :  78.62 %
#Elapsed time:  15297.50 s
#------------------------------------------------------------------------------
#
#Response for player/8176. Successful:  <Response [200]>
#
#Total successful requests:  2045
#Completed :  78.65 %
#Elapsed time:  15299.00 s
#------------------------------------------------------------------------------
#
#Response for player/25121. Successful:  <Response [200]>
#
#Total successful requests:  2046
#Completed :  78.69 %
#Elapsed time:  15321.72 s
#------------------------------------------------------------------------------
#
#Response for player/43735. Successful:  <Response [200]>
#
#Total successful requests:  2047
#Completed :  78.73 %
#Elapsed time:  15325.08 s
#------------------------------------------------------------------------------
#
#Response for player/8845. Successful:  <Response [200]>
#
#Total successful requests:  2048
#Completed :  78.77 %
#Elapsed time:  15328.25 s
#------------------------------------------------------------------------------
#
#Response for player/429748. Successful:  <Response [200]>
#
#Total successful requests:  2049
#Completed :  78.81 %
#Elapsed time:  15336.99 s
#------------------------------------------------------------------------------
#
#Response for player/39012. Successful:  <Response [200]>
#
#Total successful requests:  2050
#Completed :  78.85 %
#Elapsed time:  15344.02 s
#------------------------------------------------------------------------------
#
#Response for player/226493. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  2051
#Completed :  78.88 %
#Elapsed time:  15367.14 s
#------------------------------------------------------------------------------
#
#Response for player/51251. Successful:  <Response [200]>
#
#Total successful requests:  2052
#Completed :  78.92 %
#Elapsed time:  15368.97 s
#------------------------------------------------------------------------------
#
#Response for player/556749. Successful:  <Response [200]>
#
#Total successful requests:  2053
#Completed :  78.96 %
#Elapsed time:  15372.19 s
#------------------------------------------------------------------------------
#
#Response for player/48453. Successful:  <Response [200]>
#
#Total successful requests:  2054
#Completed :  79.00 %
#Elapsed time:  15378.21 s
#------------------------------------------------------------------------------
#
#Response for player/24891. Successful:  <Response [200]>
#
#Total successful requests:  2055
#Completed :  79.04 %
#Elapsed time:  15379.65 s
#------------------------------------------------------------------------------
#
#Response for player/5472. Successful:  <Response [200]>
#
#Total successful requests:  2056
#Completed :  79.08 %
#Elapsed time:  15393.59 s
#------------------------------------------------------------------------------
#
#Response for player/29646. Successful:  <Response [200]>
#
#Total successful requests:  2057
#Completed :  79.12 %
#Elapsed time:  15397.02 s
#------------------------------------------------------------------------------
#
#Response for player/41026. Successful:  <Response [200]>
#
#Total successful requests:  2058
#Completed :  79.15 %
#Elapsed time:  15407.76 s
#------------------------------------------------------------------------------
#
#Response for player/29998. Successful:  <Response [200]>
#
#Total successful requests:  2059
#Completed :  79.19 %
#Elapsed time:  15418.57 s
#------------------------------------------------------------------------------
#
#Response for player/25129. Successful:  <Response [200]>
#
#Total successful requests:  2060
#Completed :  79.23 %
#Elapsed time:  15421.16 s
#------------------------------------------------------------------------------
#
#Response for player/23779. Successful:  <Response [200]>
#
#Total successful requests:  2061
#Completed :  79.27 %
#Elapsed time:  15447.79 s
#------------------------------------------------------------------------------
#
#Response for player/245373. Successful:  <Response [200]>
#
#Total successful requests:  2062
#Completed :  79.31 %
#Elapsed time:  15468.43 s
#------------------------------------------------------------------------------
#
#Response for player/25105. Successful:  <Response [200]>
#
#Total successful requests:  2063
#Completed :  79.35 %
#Elapsed time:  15483.19 s
#------------------------------------------------------------------------------
#
#Response for player/42632. Successful:  <Response [200]>
#
#Total successful requests:  2064
#Completed :  79.38 %
#Elapsed time:  15494.15 s
#------------------------------------------------------------------------------
#
#Response for player/56098. Successful:  <Response [200]>
#
#Total successful requests:  2065
#Completed :  79.42 %
#Elapsed time:  15494.91 s
#------------------------------------------------------------------------------
#
#Response for player/458897. Successful:  <Response [200]>
#
#Total successful requests:  2066
#Completed :  79.46 %
#Elapsed time:  15496.66 s
#------------------------------------------------------------------------------
#
#Response for player/34109. Successful:  <Response [200]>
#
#Total successful requests:  2067
#Completed :  79.50 %
#Elapsed time:  15505.25 s
#------------------------------------------------------------------------------
#
#Response for player/23792. Successful:  <Response [200]>
#
#Total successful requests:  2068
#Completed :  79.54 %
#Elapsed time:  15506.87 s
#------------------------------------------------------------------------------
#
#Response for player/53153. Successful:  <Response [200]>
#
#Total successful requests:  2069
#Completed :  79.58 %
#Elapsed time:  15553.79 s
#------------------------------------------------------------------------------
#
#Response for player/38760. Successful:  <Response [200]>
#
#Total successful requests:  2070
#Completed :  79.62 %
#Elapsed time:  15555.99 s
#------------------------------------------------------------------------------
#
#Response for player/38755. Successful:  <Response [200]>
#
#Total successful requests:  2071
#Completed :  79.65 %
#Elapsed time:  15560.43 s
#------------------------------------------------------------------------------
#
#Response for player/8466. Successful:  <Response [200]>
#
#Total successful requests:  2072
#Completed :  79.69 %
#Elapsed time:  15561.66 s
#------------------------------------------------------------------------------
#
#Response for player/942645. Successful:  <Response [200]>
#
#Total successful requests:  2073
#Completed :  79.73 %
#Elapsed time:  15581.08 s
#------------------------------------------------------------------------------
#
#Response for player/4127. Successful:  <Response [200]>
#
#Total successful requests:  2074
#Completed :  79.77 %
#Elapsed time:  15587.80 s
#------------------------------------------------------------------------------
#
#Response for player/446548. Successful:  <Response [200]>
#
#Total successful requests:  2075
#Completed :  79.81 %
#Elapsed time:  15591.58 s
#------------------------------------------------------------------------------
#
#Response for player/36312. Successful:  <Response [200]>
#
#Total successful requests:  2076
#Completed :  79.85 %
#Elapsed time:  15595.99 s
#------------------------------------------------------------------------------
#
#Response for player/873205. Successful:  <Response [200]>
#
#Total successful requests:  2077
#Completed :  79.88 %
#Elapsed time:  15597.26 s
#------------------------------------------------------------------------------
#
#Response for player/412321. Successful:  <Response [200]>
#
#Total successful requests:  2078
#Completed :  79.92 %
#Elapsed time:  15604.01 s
#------------------------------------------------------------------------------
#
#Response for player/28149. Successful:  <Response [200]>
#
#Total successful requests:  2079
#Completed :  79.96 %
#Elapsed time:  15610.60 s
#------------------------------------------------------------------------------
#
#Response for player/48457. Successful:  <Response [200]>
#
#Total successful requests:  2080
#Completed :  80.00 %
#Elapsed time:  15614.37 s
#------------------------------------------------------------------------------
#
#Response for player/48458. Successful:  <Response [200]>
#
#Total successful requests:  2081
#Completed :  80.04 %
#Elapsed time:  15619.65 s
#------------------------------------------------------------------------------
#
#Response for player/28107. Successful:  <Response [200]>
#
#Total successful requests:  2082
#Completed :  80.08 %
#Elapsed time:  15623.48 s
#------------------------------------------------------------------------------
#
#Response for player/36839. Successful:  <Response [200]>
#
#Total successful requests:  2083
#Completed :  80.12 %
#Elapsed time:  15639.24 s
#------------------------------------------------------------------------------
#
#Response for player/40104. Successful:  <Response [200]>
#
#Total successful requests:  2084
#Completed :  80.15 %
#Elapsed time:  15642.84 s
#------------------------------------------------------------------------------
#
#Response for player/40113. Successful:  <Response [200]>
#
#Total successful requests:  2085
#Completed :  80.19 %
#Elapsed time:  15651.10 s
#------------------------------------------------------------------------------
#
#Response for player/25964. Successful:  <Response [200]>
#
#Total successful requests:  2086
#Completed :  80.23 %
#Elapsed time:  15655.53 s
#------------------------------------------------------------------------------
#
#Response for player/37241. Successful:  <Response [200]>
#
#Total successful requests:  2087
#Completed :  80.27 %
#Elapsed time:  15656.97 s
#------------------------------------------------------------------------------
#
#Response for player/55502. Successful:  <Response [200]>
#
#Total successful requests:  2088
#Completed :  80.31 %
#Elapsed time:  15665.27 s
#------------------------------------------------------------------------------
#
#Response for player/25875. Successful:  <Response [200]>
#
#Total successful requests:  2089
#Completed :  80.35 %
#Elapsed time:  15683.18 s
#------------------------------------------------------------------------------
#
#Response for player/793467. Successful:  <Response [200]>
#
#Total successful requests:  2090
#Completed :  80.38 %
#Elapsed time:  15684.42 s
#------------------------------------------------------------------------------
#
#Response for player/928067. Successful:  <Response [200]>
#
#Total successful requests:  2091
#Completed :  80.42 %
#Elapsed time:  15700.66 s
#------------------------------------------------------------------------------
#
#Response for player/16885. Successful:  <Response [200]>
#
#Total successful requests:  2092
#Completed :  80.46 %
#Elapsed time:  15702.15 s
#------------------------------------------------------------------------------
#
#Response for player/55982. Successful:  <Response [200]>
#
#Total successful requests:  2093
#Completed :  80.50 %
#Elapsed time:  15710.78 s
#------------------------------------------------------------------------------
#
#Response for player/23965. Successful:  <Response [200]>
#
#Total successful requests:  2094
#Completed :  80.54 %
#Elapsed time:  15728.12 s
#------------------------------------------------------------------------------
#
#Response for player/646181. Successful:  <Response [200]>
#
#Total successful requests:  2095
#Completed :  80.58 %
#Elapsed time:  15735.39 s
#------------------------------------------------------------------------------
#
#Response for player/941959. Successful:  <Response [200]>
#
#Total successful requests:  2096
#Completed :  80.62 %
#Elapsed time:  15745.60 s
#------------------------------------------------------------------------------
#
#Response for player/33034. Successful:  <Response [200]>
#
#Total successful requests:  2097
#Completed :  80.65 %
#Elapsed time:  15746.82 s
#------------------------------------------------------------------------------
#
#Response for player/25860. Successful:  <Response [200]>
#
#Total successful requests:  2098
#Completed :  80.69 %
#Elapsed time:  15752.46 s
#------------------------------------------------------------------------------
#
#Response for player/20282. Successful:  <Response [200]>
#
#Total successful requests:  2099
#Completed :  80.73 %
#Elapsed time:  15759.94 s
#------------------------------------------------------------------------------
#
#Response for player/457279. Successful:  <Response [200]>
#
#Total successful requests:  2100
#Completed :  80.77 %
#Elapsed time:  15770.84 s
#------------------------------------------------------------------------------
#
#Response for player/38411. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  2101
#Completed :  80.81 %
#Elapsed time:  15786.88 s
#------------------------------------------------------------------------------
#
#Response for player/21607. Successful:  <Response [200]>
#
#Total successful requests:  2102
#Completed :  80.85 %
#Elapsed time:  15790.30 s
#------------------------------------------------------------------------------
#
#Response for player/47846. Successful:  <Response [200]>
#
#Total successful requests:  2103
#Completed :  80.88 %
#Elapsed time:  15796.29 s
#------------------------------------------------------------------------------
#
#Response for player/43726. Successful:  <Response [200]>
#
#Total successful requests:  2104
#Completed :  80.92 %
#Elapsed time:  15816.92 s
#------------------------------------------------------------------------------
#
#Response for player/360911. Successful:  <Response [200]>
#
#Total successful requests:  2105
#Completed :  80.96 %
#Elapsed time:  15821.27 s
#------------------------------------------------------------------------------
#
#Response for player/39898. Successful:  <Response [200]>
#
#Total successful requests:  2106
#Completed :  81.00 %
#Elapsed time:  15824.57 s
#------------------------------------------------------------------------------
#
#Response for player/51113. Successful:  <Response [200]>
#
#Total successful requests:  2107
#Completed :  81.04 %
#Elapsed time:  15826.83 s
#------------------------------------------------------------------------------
#
#Response for player/51278. Successful:  <Response [200]>
#
#Total successful requests:  2108
#Completed :  81.08 %
#Elapsed time:  15828.71 s
#------------------------------------------------------------------------------
#
#Response for player/545467. Successful:  <Response [200]>
#
#Total successful requests:  2109
#Completed :  81.12 %
#Elapsed time:  15834.94 s
#------------------------------------------------------------------------------
#
#Response for player/44752. Successful:  <Response [200]>
#
#Total successful requests:  2110
#Completed :  81.15 %
#Elapsed time:  15836.48 s
#------------------------------------------------------------------------------
#
#Response for player/440977. Successful:  <Response [200]>
#
#Total successful requests:  2111
#Completed :  81.19 %
#Elapsed time:  15838.00 s
#------------------------------------------------------------------------------
#
#Response for player/51649. Successful:  <Response [200]>
#
#Total successful requests:  2112
#Completed :  81.23 %
#Elapsed time:  15838.67 s
#------------------------------------------------------------------------------
#
#Response for player/28067. Successful:  <Response [200]>
#
#Total successful requests:  2113
#Completed :  81.27 %
#Elapsed time:  15839.93 s
#------------------------------------------------------------------------------
#
#Response for player/48808. Successful:  <Response [200]>
#
#Total successful requests:  2114
#Completed :  81.31 %
#Elapsed time:  15841.63 s
#------------------------------------------------------------------------------
#
#Response for player/48995. Successful:  <Response [200]>
#
#Total successful requests:  2115
#Completed :  81.35 %
#Elapsed time:  15857.33 s
#------------------------------------------------------------------------------
#
#Response for player/55898. Successful:  <Response [200]>
#
#Total successful requests:  2116
#Completed :  81.38 %
#Elapsed time:  15862.76 s
#------------------------------------------------------------------------------
#
#Response for player/55907. Successful:  <Response [200]>
#
#Total successful requests:  2117
#Completed :  81.42 %
#Elapsed time:  15871.21 s
#------------------------------------------------------------------------------
#
#Response for player/29299. Successful:  <Response [200]>
#
#Total successful requests:  2118
#Completed :  81.46 %
#Elapsed time:  15892.99 s
#------------------------------------------------------------------------------
#
#Response for player/24212. Successful:  <Response [200]>
#
#Total successful requests:  2119
#Completed :  81.50 %
#Elapsed time:  15897.20 s
#------------------------------------------------------------------------------
#
#Response for player/480603. Successful:  <Response [200]>
#
#Total successful requests:  2120
#Completed :  81.54 %
#Elapsed time:  15898.74 s
#------------------------------------------------------------------------------
#
#Response for player/55560. Successful:  <Response [200]>
#
#Total successful requests:  2121
#Completed :  81.58 %
#Elapsed time:  15902.22 s
#------------------------------------------------------------------------------
#
#Response for player/16378. Successful:  <Response [200]>
#
#Total successful requests:  2122
#Completed :  81.62 %
#Elapsed time:  15903.28 s
#------------------------------------------------------------------------------
#
#Response for player/37700. Successful:  <Response [200]>
#
#Total successful requests:  2123
#Completed :  81.65 %
#Elapsed time:  15904.87 s
#------------------------------------------------------------------------------
#
#Response for player/55582. Successful:  <Response [200]>
#
#Total successful requests:  2124
#Completed :  81.69 %
#Elapsed time:  15907.01 s
#------------------------------------------------------------------------------
#
#Response for player/376169. Successful:  <Response [200]>
#
#Total successful requests:  2125
#Completed :  81.73 %
#Elapsed time:  15914.21 s
#------------------------------------------------------------------------------
#
#Response for player/481979. Successful:  <Response [200]>
#
#Total successful requests:  2126
#Completed :  81.77 %
#Elapsed time:  15918.84 s
#------------------------------------------------------------------------------
#
#Response for player/49870. Successful:  <Response [200]>
#
#Total successful requests:  2127
#Completed :  81.81 %
#Elapsed time:  15926.22 s
#------------------------------------------------------------------------------
#
#Response for player/323244. Successful:  <Response [200]>
#
#Total successful requests:  2128
#Completed :  81.85 %
#Elapsed time:  15929.60 s
#------------------------------------------------------------------------------
#
#Response for player/33129. Successful:  <Response [200]>
#
#Total successful requests:  2129
#Completed :  81.88 %
#Elapsed time:  15932.23 s
#------------------------------------------------------------------------------
#
#Response for player/25872. Successful:  <Response [200]>
#
#Total successful requests:  2130
#Completed :  81.92 %
#Elapsed time:  15937.96 s
#------------------------------------------------------------------------------
#
#Response for player/34214. Successful:  <Response [200]>
#
#Total successful requests:  2131
#Completed :  81.96 %
#Elapsed time:  15940.96 s
#------------------------------------------------------------------------------
#
#Response for player/35281. Successful:  <Response [200]>
#
#Total successful requests:  2132
#Completed :  82.00 %
#Elapsed time:  15944.87 s
#------------------------------------------------------------------------------
#
#Response for player/25546. Successful:  <Response [200]>
#
#Total successful requests:  2133
#Completed :  82.04 %
#Elapsed time:  15947.42 s
#------------------------------------------------------------------------------
#
#Response for player/20345. Successful:  <Response [200]>
#
#Total successful requests:  2134
#Completed :  82.08 %
#Elapsed time:  15949.35 s
#------------------------------------------------------------------------------
#
#Response for player/50807. Successful:  <Response [200]>
#
#Total successful requests:  2135
#Completed :  82.12 %
#Elapsed time:  15950.55 s
#------------------------------------------------------------------------------
#
#Response for player/316102. Successful:  <Response [200]>
#
#Total successful requests:  2136
#Completed :  82.15 %
#Elapsed time:  15958.26 s
#------------------------------------------------------------------------------
#
#Response for player/47900. Successful:  <Response [200]>
#
#Total successful requests:  2137
#Completed :  82.19 %
#Elapsed time:  15968.49 s
#------------------------------------------------------------------------------
#
#Response for player/24687. Successful:  <Response [200]>
#
#Total successful requests:  2138
#Completed :  82.23 %
#Elapsed time:  15970.13 s
#------------------------------------------------------------------------------
#
#Response for player/669855. Successful:  <Response [200]>
#
#Total successful requests:  2139
#Completed :  82.27 %
#Elapsed time:  15971.57 s
#------------------------------------------------------------------------------
#
#Response for player/272477. Successful:  <Response [200]>
#
#Total successful requests:  2140
#Completed :  82.31 %
#Elapsed time:  15974.33 s
#------------------------------------------------------------------------------
#
#Response for player/380957. Successful:  <Response [200]>
#
#Total successful requests:  2141
#Completed :  82.35 %
#Elapsed time:  15980.41 s
#------------------------------------------------------------------------------
#
#Response for player/55382. Successful:  <Response [200]>
#
#Total successful requests:  2142
#Completed :  82.38 %
#Elapsed time:  15990.44 s
#------------------------------------------------------------------------------
#
#Response for player/40094. Successful:  <Response [200]>
#
#Total successful requests:  2143
#Completed :  82.42 %
#Elapsed time:  15993.23 s
#------------------------------------------------------------------------------
#
#Response for player/49008. Successful:  <Response [200]>
#
#Total successful requests:  2144
#Completed :  82.46 %
#Elapsed time:  16001.43 s
#------------------------------------------------------------------------------
#
#Response for player/529349. Successful:  <Response [200]>
#
#Total successful requests:  2145
#Completed :  82.50 %
#Elapsed time:  16008.36 s
#------------------------------------------------------------------------------
#
#Response for player/276370. Successful:  <Response [200]>
#
#Total successful requests:  2146
#Completed :  82.54 %
#Elapsed time:  16019.26 s
#------------------------------------------------------------------------------
#
#Response for player/55493. Successful:  <Response [200]>
#
#Total successful requests:  2147
#Completed :  82.58 %
#Elapsed time:  16023.43 s
#------------------------------------------------------------------------------
#
#Response for player/5732. Successful:  <Response [200]>
#
#Total successful requests:  2148
#Completed :  82.62 %
#Elapsed time:  16044.80 s
#------------------------------------------------------------------------------
#
#Response for player/402247. Successful:  <Response [200]>
#
#Total successful requests:  2149
#Completed :  82.65 %
#Elapsed time:  16056.07 s
#------------------------------------------------------------------------------
#
#Response for player/45711. Successful:  <Response [200]>
#
#Total successful requests:  2150
#Completed :  82.69 %
#Elapsed time:  16059.68 s
#------------------------------------------------------------------------------
#
#Response for player/55937. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  2151
#Completed :  82.73 %
#Elapsed time:  16066.01 s
#------------------------------------------------------------------------------
#
#Response for player/49598. Successful:  <Response [200]>
#
#Total successful requests:  2152
#Completed :  82.77 %
#Elapsed time:  16068.06 s
#------------------------------------------------------------------------------
#
#Response for player/41246. Successful:  <Response [200]>
#
#Total successful requests:  2153
#Completed :  82.81 %
#Elapsed time:  16071.76 s
#------------------------------------------------------------------------------
#
#Response for player/1043681. Successful:  <Response [200]>
#
#Total successful requests:  2154
#Completed :  82.85 %
#Elapsed time:  16073.51 s
#------------------------------------------------------------------------------
#
#Response for player/6480. Successful:  <Response [200]>
#
#Total successful requests:  2155
#Completed :  82.88 %
#Elapsed time:  16076.85 s
#------------------------------------------------------------------------------
#
#Response for player/30999. Successful:  <Response [200]>
#
#Total successful requests:  2156
#Completed :  82.92 %
#Elapsed time:  16086.18 s
#------------------------------------------------------------------------------
#
#Response for player/52437. Successful:  <Response [200]>
#
#Total successful requests:  2157
#Completed :  82.96 %
#Elapsed time:  16091.07 s
#------------------------------------------------------------------------------
#
#Response for player/6654. Successful:  <Response [200]>
#
#Total successful requests:  2158
#Completed :  83.00 %
#Elapsed time:  16095.01 s
#------------------------------------------------------------------------------
#
#Response for player/446810. Successful:  <Response [200]>
#
#Total successful requests:  2159
#Completed :  83.04 %
#Elapsed time:  16107.22 s
#------------------------------------------------------------------------------
#
#Response for player/49868. Successful:  <Response [200]>
#
#Total successful requests:  2160
#Completed :  83.08 %
#Elapsed time:  16114.98 s
#------------------------------------------------------------------------------
#
#Response for player/450101. Successful:  <Response [200]>
#
#Total successful requests:  2161
#Completed :  83.12 %
#Elapsed time:  16117.70 s
#------------------------------------------------------------------------------
#
#Response for player/20051. Successful:  <Response [200]>
#
#Total successful requests:  2162
#Completed :  83.15 %
#Elapsed time:  16138.94 s
#------------------------------------------------------------------------------
#
#Response for player/20182. Successful:  <Response [200]>
#
#Total successful requests:  2163
#Completed :  83.19 %
#Elapsed time:  16143.27 s
#------------------------------------------------------------------------------
#
#Response for player/50460. Successful:  <Response [200]>
#
#Total successful requests:  2164
#Completed :  83.23 %
#Elapsed time:  16150.70 s
#------------------------------------------------------------------------------
#
#Response for player/24956. Successful:  <Response [200]>
#
#Total successful requests:  2165
#Completed :  83.27 %
#Elapsed time:  16180.26 s
#------------------------------------------------------------------------------
#
#Response for player/461632. Successful:  <Response [200]>
#
#Total successful requests:  2166
#Completed :  83.31 %
#Elapsed time:  16181.80 s
#------------------------------------------------------------------------------
#
#Response for player/928057. Successful:  <Response [200]>
#
#Total successful requests:  2167
#Completed :  83.35 %
#Elapsed time:  16184.11 s
#------------------------------------------------------------------------------
#
#Response for player/24975. Successful:  <Response [200]>
#
#Total successful requests:  2168
#Completed :  83.38 %
#Elapsed time:  16185.76 s
#------------------------------------------------------------------------------
#
#Response for player/36080. Successful:  <Response [200]>
#
#Total successful requests:  2169
#Completed :  83.42 %
#Elapsed time:  16189.26 s
#------------------------------------------------------------------------------
#
#Response for player/48139. Successful:  <Response [200]>
#
#Total successful requests:  2170
#Completed :  83.46 %
#Elapsed time:  16190.75 s
#------------------------------------------------------------------------------
#
#Response for player/26942. Successful:  <Response [200]>
#
#Total successful requests:  2171
#Completed :  83.50 %
#Elapsed time:  16195.56 s
#------------------------------------------------------------------------------
#
#Response for player/4517. Successful:  <Response [200]>
#
#Total successful requests:  2172
#Completed :  83.54 %
#Elapsed time:  16197.33 s
#------------------------------------------------------------------------------
#
#Response for player/4523. Successful:  <Response [200]>
#
#Total successful requests:  2173
#Completed :  83.58 %
#Elapsed time:  16199.08 s
#------------------------------------------------------------------------------
#
#Response for player/27603. Successful:  <Response [200]>
#
#Total successful requests:  2174
#Completed :  83.62 %
#Elapsed time:  16200.33 s
#------------------------------------------------------------------------------
#
#Response for player/55353. Successful:  <Response [200]>
#
#Total successful requests:  2175
#Completed :  83.65 %
#Elapsed time:  16220.73 s
#------------------------------------------------------------------------------
#
#Response for player/420341. Successful:  <Response [200]>
#
#Total successful requests:  2176
#Completed :  83.69 %
#Elapsed time:  16222.65 s
#------------------------------------------------------------------------------
#
#Response for player/431905. Successful:  <Response [200]>
#
#Total successful requests:  2177
#Completed :  83.73 %
#Elapsed time:  16224.13 s
#------------------------------------------------------------------------------
#
#Response for player/44954. Successful:  <Response [200]>
#
#Total successful requests:  2178
#Completed :  83.77 %
#Elapsed time:  16225.68 s
#------------------------------------------------------------------------------
#
#Response for player/55887. Successful:  <Response [200]>
#
#Total successful requests:  2179
#Completed :  83.81 %
#Elapsed time:  16238.00 s
#------------------------------------------------------------------------------
#
#Response for player/1139028. Successful:  <Response [200]>
#
#Total successful requests:  2180
#Completed :  83.85 %
#Elapsed time:  16264.74 s
#------------------------------------------------------------------------------
#
#Response for player/13437. Successful:  <Response [200]>
#
#Total successful requests:  2181
#Completed :  83.88 %
#Elapsed time:  16268.53 s
#------------------------------------------------------------------------------
#
#Response for player/23952. Successful:  <Response [200]>
#
#Total successful requests:  2182
#Completed :  83.92 %
#Elapsed time:  16285.21 s
#------------------------------------------------------------------------------
#
#Response for player/29280. Successful:  <Response [200]>
#
#Total successful requests:  2183
#Completed :  83.96 %
#Elapsed time:  16289.56 s
#------------------------------------------------------------------------------
#
#Response for player/14159. Successful:  <Response [200]>
#
#Total successful requests:  2184
#Completed :  84.00 %
#Elapsed time:  16304.66 s
#------------------------------------------------------------------------------
#
#Response for player/23773. Successful:  <Response [200]>
#
#Total successful requests:  2185
#Completed :  84.04 %
#Elapsed time:  16311.05 s
#------------------------------------------------------------------------------
#
#Response for player/935553. Successful:  <Response [200]>
#
#Total successful requests:  2186
#Completed :  84.08 %
#Elapsed time:  16312.31 s
#------------------------------------------------------------------------------
#
#Response for player/30135. Successful:  <Response [200]>
#
#Total successful requests:  2187
#Completed :  84.12 %
#Elapsed time:  16314.01 s
#------------------------------------------------------------------------------
#
#Response for player/6943. Successful:  <Response [200]>
#
#Total successful requests:  2188
#Completed :  84.15 %
#Elapsed time:  16315.34 s
#------------------------------------------------------------------------------
#
#Response for player/440162. Successful:  <Response [200]>
#
#Total successful requests:  2189
#Completed :  84.19 %
#Elapsed time:  16320.52 s
#------------------------------------------------------------------------------
#
#Response for player/32226. Successful:  <Response [200]>
#
#Total successful requests:  2190
#Completed :  84.23 %
#Elapsed time:  16321.55 s
#------------------------------------------------------------------------------
#
#Response for player/1122557. Successful:  <Response [200]>
#
#Total successful requests:  2191
#Completed :  84.27 %
#Elapsed time:  16322.80 s
#------------------------------------------------------------------------------
#
#Response for player/47010. Successful:  <Response [200]>
#
#Total successful requests:  2192
#Completed :  84.31 %
#Elapsed time:  16324.31 s
#------------------------------------------------------------------------------
#
#Response for player/697279. Successful:  <Response [200]>
#
#Total successful requests:  2193
#Completed :  84.35 %
#Elapsed time:  16340.72 s
#------------------------------------------------------------------------------
#
#Response for player/38746. Successful:  <Response [200]>
#
#Total successful requests:  2194
#Completed :  84.38 %
#Elapsed time:  16343.73 s
#------------------------------------------------------------------------------
#
#Response for player/627732. Successful:  <Response [200]>
#
#Total successful requests:  2195
#Completed :  84.42 %
#Elapsed time:  16352.71 s
#------------------------------------------------------------------------------
#
#Response for player/557298. Successful:  <Response [200]>
#
#Total successful requests:  2196
#Completed :  84.46 %
#Elapsed time:  16355.33 s
#------------------------------------------------------------------------------
#
#Response for player/25661. Successful:  <Response [200]>
#
#Total successful requests:  2197
#Completed :  84.50 %
#Elapsed time:  16363.18 s
#------------------------------------------------------------------------------
#
#Response for player/275943. Successful:  <Response [200]>
#
#Total successful requests:  2198
#Completed :  84.54 %
#Elapsed time:  16365.67 s
#------------------------------------------------------------------------------
#
#Response for player/334946. Successful:  <Response [200]>
#
#Total successful requests:  2199
#Completed :  84.58 %
#Elapsed time:  16370.60 s
#------------------------------------------------------------------------------
#
#Response for player/15385. Successful:  <Response [200]>
#
#Total successful requests:  2200
#Completed :  84.62 %
#Elapsed time:  16376.71 s
#------------------------------------------------------------------------------
#
#Response for page 2 Successful:  <Response [200]> 	=>
#

#list of players:  200
#Response for player/40872. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  2201
#Completed :  84.65 %
#Elapsed time:  16431.26 s
#------------------------------------------------------------------------------
#
#Response for player/629066. Successful:  <Response [200]>
#
#Total successful requests:  2202
#Completed :  84.69 %
#Elapsed time:  16440.61 s
#------------------------------------------------------------------------------
#
#Response for player/24229. Successful:  <Response [200]>
#
#Total successful requests:  2203
#Completed :  84.73 %
#Elapsed time:  16445.67 s
#------------------------------------------------------------------------------
#
#Response for player/23960. Successful:  <Response [200]>
#
#Total successful requests:  2204
#Completed :  84.77 %
#Elapsed time:  16453.24 s
#------------------------------------------------------------------------------
#
#Response for player/41963. Successful:  <Response [200]>
#
#Total successful requests:  2205
#Completed :  84.81 %
#Elapsed time:  16461.39 s
#------------------------------------------------------------------------------
#
#Response for player/41272. Successful:  <Response [200]>
#
#Total successful requests:  2206
#Completed :  84.85 %
#Elapsed time:  16462.65 s
#------------------------------------------------------------------------------
#
#Response for player/41984. Successful:  <Response [200]>
#
#Total successful requests:  2207
#Completed :  84.88 %
#Elapsed time:  16468.69 s
#------------------------------------------------------------------------------
#
#Response for player/533953. Successful:  <Response [200]>
#
#Total successful requests:  2208
#Completed :  84.92 %
#Elapsed time:  16470.28 s
#------------------------------------------------------------------------------
#
#Response for player/42059. Successful:  <Response [200]>
#
#Total successful requests:  2209
#Completed :  84.96 %
#Elapsed time:  16472.91 s
#------------------------------------------------------------------------------
#
#Response for player/56044. Successful:  <Response [200]>
#
#Total successful requests:  2210
#Completed :  85.00 %
#Elapsed time:  16474.23 s
#------------------------------------------------------------------------------
#
#Response for player/23969. Successful:  <Response [200]>
#
#Total successful requests:  2211
#Completed :  85.04 %
#Elapsed time:  16484.39 s
#------------------------------------------------------------------------------
#
#Response for player/913853. Successful:  <Response [200]>
#
#Total successful requests:  2212
#Completed :  85.08 %
#Elapsed time:  16498.89 s
#------------------------------------------------------------------------------
#
#Response for player/52805. Successful:  <Response [200]>
#
#Total successful requests:  2213
#Completed :  85.12 %
#Elapsed time:  16503.65 s
#------------------------------------------------------------------------------
#
#Response for player/42612. Successful:  <Response [200]>
#
#Total successful requests:  2214
#Completed :  85.15 %
#Elapsed time:  16512.31 s
#------------------------------------------------------------------------------
#
#Response for player/34074. Successful:  <Response [200]>
#
#Total successful requests:  2215
#Completed :  85.19 %
#Elapsed time:  16528.27 s
#------------------------------------------------------------------------------
#
#Response for player/24827. Successful:  <Response [200]>
#
#Total successful requests:  2216
#Completed :  85.23 %
#Elapsed time:  16535.78 s
#------------------------------------------------------------------------------
#
#Response for player/56180. Successful:  <Response [200]>
#
#Total successful requests:  2217
#Completed :  85.27 %
#Elapsed time:  16540.08 s
#------------------------------------------------------------------------------
#
#Response for player/421892. Successful:  <Response [200]>
#
#Total successful requests:  2218
#Completed :  85.31 %
#Elapsed time:  16541.76 s
#------------------------------------------------------------------------------
#
#Response for player/47541. Successful:  <Response [200]>
#
#Total successful requests:  2219
#Completed :  85.35 %
#Elapsed time:  16544.25 s
#------------------------------------------------------------------------------
#
#Response for player/223642. Successful:  <Response [200]>
#
#Total successful requests:  2220
#Completed :  85.38 %
#Elapsed time:  16552.53 s
#------------------------------------------------------------------------------
#
#Response for player/245186. Successful:  <Response [200]>
#
#Total successful requests:  2221
#Completed :  85.42 %
#Elapsed time:  16555.06 s
#------------------------------------------------------------------------------
#
#Response for player/511532. Successful:  <Response [200]>
#
#Total successful requests:  2222
#Completed :  85.46 %
#Elapsed time:  16557.75 s
#------------------------------------------------------------------------------
#
#Response for player/701201. Successful:  <Response [200]>
#
#Total successful requests:  2223
#Completed :  85.50 %
#Elapsed time:  16559.43 s
#------------------------------------------------------------------------------
#
#Response for player/51228. Successful:  <Response [200]>
#
#Total successful requests:  2224
#Completed :  85.54 %
#Elapsed time:  16561.36 s
#------------------------------------------------------------------------------
#
#Response for player/12794. Successful:  <Response [200]>
#
#Total successful requests:  2225
#Completed :  85.58 %
#Elapsed time:  16564.53 s
#------------------------------------------------------------------------------
#
#Response for player/240609. Successful:  <Response [200]>
#
#Total successful requests:  2226
#Completed :  85.62 %
#Elapsed time:  16576.76 s
#------------------------------------------------------------------------------
#
#Response for player/12906. Successful:  <Response [200]>
#
#Total successful requests:  2227
#Completed :  85.65 %
#Elapsed time:  16591.56 s
#------------------------------------------------------------------------------
#
#Response for player/268845. Successful:  <Response [200]>
#
#Total successful requests:  2228
#Completed :  85.69 %
#Elapsed time:  16592.61 s
#------------------------------------------------------------------------------
#
#Response for player/28774. Successful:  <Response [200]>
#
#Total successful requests:  2229
#Completed :  85.73 %
#Elapsed time:  16594.29 s
#------------------------------------------------------------------------------
#
#Response for player/302850. Successful:  <Response [200]>
#
#Total successful requests:  2230
#Completed :  85.77 %
#Elapsed time:  16608.47 s
#------------------------------------------------------------------------------
#
#Response for player/28884. Successful:  <Response [200]>
#
#Total successful requests:  2231
#Completed :  85.81 %
#Elapsed time:  16618.86 s
#------------------------------------------------------------------------------
#
#Response for player/826679. Successful:  <Response [200]>
#
#Total successful requests:  2232
#Completed :  85.85 %
#Elapsed time:  16619.66 s
#------------------------------------------------------------------------------
#
#Response for player/55932. Successful:  <Response [200]>
#
#Total successful requests:  2233
#Completed :  85.88 %
#Elapsed time:  16624.85 s
#------------------------------------------------------------------------------
#
#Response for player/6291. Successful:  <Response [200]>
#
#Total successful requests:  2234
#Completed :  85.92 %
#Elapsed time:  16630.32 s
#------------------------------------------------------------------------------
#
#Response for player/307528. Successful:  <Response [200]>
#
#Total successful requests:  2235
#Completed :  85.96 %
#Elapsed time:  16631.03 s
#------------------------------------------------------------------------------
#
#Response for player/41294. Successful:  <Response [200]>
#
#Total successful requests:  2236
#Completed :  86.00 %
#Elapsed time:  16638.16 s
#------------------------------------------------------------------------------
#
#Response for player/32168. Successful:  <Response [200]>
#
#Total successful requests:  2237
#Completed :  86.04 %
#Elapsed time:  16653.48 s
#------------------------------------------------------------------------------
#
#Response for player/18557. Successful:  <Response [200]>
#
#Total successful requests:  2238
#Completed :  86.08 %
#Elapsed time:  16662.44 s
#------------------------------------------------------------------------------
#
#Response for player/596002. Successful:  <Response [200]>
#
#Total successful requests:  2239
#Completed :  86.12 %
#Elapsed time:  16690.35 s
#------------------------------------------------------------------------------
#
#Response for player/34264. Successful:  <Response [200]>
#
#Total successful requests:  2240
#Completed :  86.15 %
#Elapsed time:  16702.04 s
#------------------------------------------------------------------------------
#
#Response for player/56097. Successful:  <Response [200]>
#
#Total successful requests:  2241
#Completed :  86.19 %
#Elapsed time:  16718.00 s
#------------------------------------------------------------------------------
#
#Response for player/23785. Successful:  <Response [200]>
#
#Total successful requests:  2242
#Completed :  86.23 %
#Elapsed time:  16719.43 s
#------------------------------------------------------------------------------
#
#Response for player/299814. Successful:  <Response [200]>
#
#Total successful requests:  2243
#Completed :  86.27 %
#Elapsed time:  16721.54 s
#------------------------------------------------------------------------------
#
#Response for player/533042. Successful:  <Response [200]>
#
#Total successful requests:  2244
#Completed :  86.31 %
#Elapsed time:  16723.20 s
#------------------------------------------------------------------------------
#
#Response for player/25643. Successful:  <Response [200]>
#
#Total successful requests:  2245
#Completed :  86.35 %
#Elapsed time:  16723.89 s
#------------------------------------------------------------------------------
#
#Response for player/47242. Successful:  <Response [200]>
#
#Total successful requests:  2246
#Completed :  86.38 %
#Elapsed time:  16735.81 s
#------------------------------------------------------------------------------
#
#Response for player/34136. Successful:  <Response [200]>
#
#Total successful requests:  2247
#Completed :  86.42 %
#Elapsed time:  16738.42 s
#------------------------------------------------------------------------------
#
#Response for player/23974. Successful:  <Response [200]>
#
#Total successful requests:  2248
#Completed :  86.46 %
#Elapsed time:  16739.92 s
#------------------------------------------------------------------------------
#
#Response for player/919549. Successful:  <Response [200]>
#
#Total successful requests:  2249
#Completed :  86.50 %
#Elapsed time:  16749.61 s
#------------------------------------------------------------------------------
#
#Response for player/414985. Successful:  <Response [200]>
#
#Total successful requests:  2250
#Completed :  86.54 %
#Elapsed time:  16753.24 s
#------------------------------------------------------------------------------
#
#Response for player/7970. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  2251
#Completed :  86.58 %
#Elapsed time:  16758.74 s
#------------------------------------------------------------------------------
#
#Response for player/333782. Successful:  <Response [200]>
#
#Total successful requests:  2252
#Completed :  86.62 %
#Elapsed time:  16761.24 s
#------------------------------------------------------------------------------
#
#Response for player/25977. Successful:  <Response [200]>
#
#Total successful requests:  2253
#Completed :  86.65 %
#Elapsed time:  16765.74 s
#------------------------------------------------------------------------------
#
#Response for player/22333. Successful:  <Response [200]>
#
#Total successful requests:  2254
#Completed :  86.69 %
#Elapsed time:  16770.44 s
#------------------------------------------------------------------------------
#
#Response for player/51019. Successful:  <Response [200]>
#
#Total successful requests:  2255
#Completed :  86.73 %
#Elapsed time:  16776.67 s
#------------------------------------------------------------------------------
#
#Response for player/50846. Successful:  <Response [200]>
#
#Total successful requests:  2256
#Completed :  86.77 %
#Elapsed time:  16780.70 s
#------------------------------------------------------------------------------
#
#Response for player/8241. Successful:  <Response [200]>
#
#Total successful requests:  2257
#Completed :  86.81 %
#Elapsed time:  16783.42 s
#------------------------------------------------------------------------------
#
#Response for player/48112. Successful:  <Response [200]>
#
#Total successful requests:  2258
#Completed :  86.85 %
#Elapsed time:  16792.71 s
#------------------------------------------------------------------------------
#
#Response for player/398666. Successful:  <Response [200]>
#
#Total successful requests:  2259
#Completed :  86.88 %
#Elapsed time:  16793.42 s
#------------------------------------------------------------------------------
#
#Response for player/390752. Successful:  <Response [200]>
#
#Total successful requests:  2260
#Completed :  86.92 %
#Elapsed time:  16800.29 s
#------------------------------------------------------------------------------
#
#Response for player/927119. Successful:  <Response [200]>
#
#Total successful requests:  2261
#Completed :  86.96 %
#Elapsed time:  16805.92 s
#------------------------------------------------------------------------------
#
#Response for player/25053. Successful:  <Response [200]>
#
#Total successful requests:  2262
#Completed :  87.00 %
#Elapsed time:  16807.36 s
#------------------------------------------------------------------------------
#
#Response for player/307077. Successful:  <Response [200]>
#
#Total successful requests:  2263
#Completed :  87.04 %
#Elapsed time:  16808.24 s
#------------------------------------------------------------------------------
#
#Response for player/48290. Successful:  <Response [200]>
#
#Total successful requests:  2264
#Completed :  87.08 %
#Elapsed time:  16808.96 s
#------------------------------------------------------------------------------
#
#Response for player/25092. Successful:  <Response [200]>
#
#Total successful requests:  2265
#Completed :  87.12 %
#Elapsed time:  16811.61 s
#------------------------------------------------------------------------------
#
#Response for player/49121. Successful:  <Response [200]>
#
#Total successful requests:  2266
#Completed :  87.15 %
#Elapsed time:  16823.14 s
#------------------------------------------------------------------------------
#
#Response for player/37228. Successful:  <Response [200]>
#
#Total successful requests:  2267
#Completed :  87.19 %
#Elapsed time:  16824.38 s
#------------------------------------------------------------------------------
#
#Response for player/37240. Successful:  <Response [200]>
#
#Total successful requests:  2268
#Completed :  87.23 %
#Elapsed time:  16832.01 s
#------------------------------------------------------------------------------
#
#Response for player/49131. Successful:  <Response [200]>
#
#Total successful requests:  2269
#Completed :  87.27 %
#Elapsed time:  16833.53 s
#------------------------------------------------------------------------------
#
#Response for player/40553. Successful:  <Response [200]>
#
#Total successful requests:  2270
#Completed :  87.31 %
#Elapsed time:  16836.10 s
#------------------------------------------------------------------------------
#
#Response for player/585081. Successful:  <Response [200]>
#
#Total successful requests:  2271
#Completed :  87.35 %
#Elapsed time:  16842.27 s
#------------------------------------------------------------------------------
#
#Response for player/208380. Successful:  <Response [200]>
#
#Total successful requests:  2272
#Completed :  87.38 %
#Elapsed time:  16869.62 s
#------------------------------------------------------------------------------
#
#Response for player/55966. Successful:  <Response [200]>
#
#Total successful requests:  2273
#Completed :  87.42 %
#Elapsed time:  16877.66 s
#------------------------------------------------------------------------------
#
#Response for player/55997. Successful:  <Response [200]>
#
#Total successful requests:  2274
#Completed :  87.46 %
#Elapsed time:  16883.37 s
#------------------------------------------------------------------------------
#
#Response for player/49631. Successful:  <Response [200]>
#
#Total successful requests:  2275
#Completed :  87.50 %
#Elapsed time:  16886.08 s
#------------------------------------------------------------------------------
#
#Response for player/672775. Successful:  <Response [200]>
#
#Total successful requests:  2276
#Completed :  87.54 %
#Elapsed time:  16894.95 s
#------------------------------------------------------------------------------
#
#Response for player/37735. Successful:  <Response [200]>
#
#Total successful requests:  2277
#Completed :  87.58 %
#Elapsed time:  16900.84 s
#------------------------------------------------------------------------------
#
#Response for player/31808. Successful:  <Response [200]>
#
#Total successful requests:  2278
#Completed :  87.62 %
#Elapsed time:  16902.49 s
#------------------------------------------------------------------------------
#
#Response for player/38108. Successful:  <Response [200]>
#
#Total successful requests:  2279
#Completed :  87.65 %
#Elapsed time:  16904.41 s
#------------------------------------------------------------------------------
#
#Response for player/32973. Successful:  <Response [200]>
#
#Total successful requests:  2280
#Completed :  87.69 %
#Elapsed time:  16906.24 s
#------------------------------------------------------------------------------
#
#Response for player/23782. Successful:  <Response [200]>
#
#Total successful requests:  2281
#Completed :  87.73 %
#Elapsed time:  16922.13 s
#------------------------------------------------------------------------------
#
#Response for player/364330. Successful:  <Response [200]>
#
#Total successful requests:  2282
#Completed :  87.77 %
#Elapsed time:  16923.57 s
#------------------------------------------------------------------------------
#
#Response for player/7135. Successful:  <Response [200]>
#
#Total successful requests:  2283
#Completed :  87.81 %
#Elapsed time:  16925.33 s
#------------------------------------------------------------------------------
#
#Response for player/55708. Successful:  <Response [200]>
#
#Total successful requests:  2284
#Completed :  87.85 %
#Elapsed time:  16939.23 s
#------------------------------------------------------------------------------
#
#Response for player/38244. Successful:  <Response [200]>
#
#Total successful requests:  2285
#Completed :  87.88 %
#Elapsed time:  16941.12 s
#------------------------------------------------------------------------------
#
#Response for player/524095. Successful:  <Response [200]>
#
#Total successful requests:  2286
#Completed :  87.92 %
#Elapsed time:  16946.11 s
#------------------------------------------------------------------------------
#
#Response for player/23866. Successful:  <Response [200]>
#
#Total successful requests:  2287
#Completed :  87.96 %
#Elapsed time:  16947.94 s
#------------------------------------------------------------------------------
#
#Response for player/52960. Successful:  <Response [200]>
#
#Total successful requests:  2288
#Completed :  88.00 %
#Elapsed time:  16949.93 s
#------------------------------------------------------------------------------
#
#Response for player/43515. Successful:  <Response [200]>
#
#Total successful requests:  2289
#Completed :  88.04 %
#Elapsed time:  16967.35 s
#------------------------------------------------------------------------------
#
#Response for player/23794. Successful:  <Response [200]>
#
#Total successful requests:  2290
#Completed :  88.08 %
#Elapsed time:  16986.05 s
#------------------------------------------------------------------------------
#
#Response for player/47715. Successful:  <Response [200]>
#
#Total successful requests:  2291
#Completed :  88.12 %
#Elapsed time:  16988.44 s
#------------------------------------------------------------------------------
#
#Response for player/440968. Successful:  <Response [200]>
#
#Total successful requests:  2292
#Completed :  88.15 %
#Elapsed time:  17002.06 s
#------------------------------------------------------------------------------
#
#Response for player/43696. Successful:  <Response [200]>
#
#Total successful requests:  2293
#Completed :  88.19 %
#Elapsed time:  17004.56 s
#------------------------------------------------------------------------------
#
#Response for player/409474. Successful:  <Response [200]>
#
#Total successful requests:  2294
#Completed :  88.23 %
#Elapsed time:  17012.59 s
#------------------------------------------------------------------------------
#
#Response for player/307657. Successful:  <Response [200]>
#
#Total successful requests:  2295
#Completed :  88.27 %
#Elapsed time:  17015.56 s
#------------------------------------------------------------------------------
#
#Response for player/957645. Successful:  <Response [200]>
#
#Total successful requests:  2296
#Completed :  88.31 %
#Elapsed time:  17020.81 s
#------------------------------------------------------------------------------
#
#Response for player/8501. Successful:  <Response [200]>
#
#Total successful requests:  2297
#Completed :  88.35 %
#Elapsed time:  17025.24 s
#------------------------------------------------------------------------------
#
#Response for player/318337. Successful:  <Response [200]>
#
#Total successful requests:  2298
#Completed :  88.38 %
#Elapsed time:  17031.78 s
#------------------------------------------------------------------------------
#
#Response for player/56222. Successful:  <Response [200]>
#
#Total successful requests:  2299
#Completed :  88.42 %
#Elapsed time:  17043.96 s
#------------------------------------------------------------------------------
#
#Response for player/557295. Successful:  <Response [200]>
#
#Total successful requests:  2300
#Completed :  88.46 %
#Elapsed time:  17050.17 s
#------------------------------------------------------------------------------
#
#Response for player/4882. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  2301
#Completed :  88.50 %
#Elapsed time:  17060.57 s
#------------------------------------------------------------------------------
#
#Response for player/5112. Successful:  <Response [200]>
#
#Total successful requests:  2302
#Completed :  88.54 %
#Elapsed time:  17062.47 s
#------------------------------------------------------------------------------
#
#Response for player/5126. Successful:  <Response [200]>
#
#Total successful requests:  2303
#Completed :  88.58 %
#Elapsed time:  17066.45 s
#------------------------------------------------------------------------------
#
#Response for player/55883. Successful:  <Response [200]>
#
#Total successful requests:  2304
#Completed :  88.62 %
#Elapsed time:  17078.80 s
#------------------------------------------------------------------------------
#
#Response for player/1126002. Successful:  <Response [200]>
#
#Total successful requests:  2305
#Completed :  88.65 %
#Elapsed time:  17086.52 s
#------------------------------------------------------------------------------
#
#Response for player/24243. Successful:  <Response [200]>
#
#Total successful requests:  2306
#Completed :  88.69 %
#Elapsed time:  17098.19 s
#------------------------------------------------------------------------------
#
#Response for player/49002. Successful:  <Response [200]>
#
#Total successful requests:  2307
#Completed :  88.73 %
#Elapsed time:  17101.82 s
#------------------------------------------------------------------------------
#
#Response for player/379927. Successful:  <Response [200]>
#
#Total successful requests:  2308
#Completed :  88.77 %
#Elapsed time:  17121.20 s
#------------------------------------------------------------------------------
#
#Response for player/307235. Successful:  <Response [200]>
#
#Total successful requests:  2309
#Completed :  88.81 %
#Elapsed time:  17128.05 s
#------------------------------------------------------------------------------
#
#Response for player/628240. Successful:  <Response [200]>
#
#Total successful requests:  2310
#Completed :  88.85 %
#Elapsed time:  17129.61 s
#------------------------------------------------------------------------------
#
#Response for player/741143. Successful:  <Response [200]>
#
#Total successful requests:  2311
#Completed :  88.88 %
#Elapsed time:  17139.85 s
#------------------------------------------------------------------------------
#
#Response for player/40926. Successful:  <Response [200]>
#
#Total successful requests:  2312
#Completed :  88.92 %
#Elapsed time:  17145.82 s
#------------------------------------------------------------------------------
#
#Response for player/26135. Successful:  <Response [200]>
#
#Total successful requests:  2313
#Completed :  88.96 %
#Elapsed time:  17147.32 s
#------------------------------------------------------------------------------
#
#Response for player/41036. Successful:  <Response [200]>
#
#Total successful requests:  2314
#Completed :  89.00 %
#Elapsed time:  17150.57 s
#------------------------------------------------------------------------------
#
#Response for player/15901. Successful:  <Response [200]>
#
#Total successful requests:  2315
#Completed :  89.04 %
#Elapsed time:  17152.76 s
#------------------------------------------------------------------------------
#
#Response for player/41275. Successful:  <Response [200]>
#
#Total successful requests:  2316
#Completed :  89.08 %
#Elapsed time:  17154.90 s
#------------------------------------------------------------------------------
#
#Response for player/297634. Successful:  <Response [200]>
#
#Total successful requests:  2317
#Completed :  89.12 %
#Elapsed time:  17163.81 s
#------------------------------------------------------------------------------
#
#Response for player/217522. Successful:  <Response [200]>
#
#Total successful requests:  2318
#Completed :  89.15 %
#Elapsed time:  17167.13 s
#------------------------------------------------------------------------------
#
#Response for player/55974. Successful:  <Response [200]>
#
#Total successful requests:  2319
#Completed :  89.19 %
#Elapsed time:  17173.87 s
#------------------------------------------------------------------------------
#
#Response for player/31048. Successful:  <Response [200]>
#
#Total successful requests:  2320
#Completed :  89.23 %
#Elapsed time:  17183.93 s
#------------------------------------------------------------------------------
#
#Response for player/42047. Successful:  <Response [200]>
#
#Total successful requests:  2321
#Completed :  89.27 %
#Elapsed time:  17203.72 s
#------------------------------------------------------------------------------
#
#Response for player/25625. Successful:  <Response [200]>
#
#Total successful requests:  2322
#Completed :  89.31 %
#Elapsed time:  17216.57 s
#------------------------------------------------------------------------------
#
#Response for player/38064. Successful:  <Response [200]>
#
#Total successful requests:  2323
#Completed :  89.35 %
#Elapsed time:  17221.01 s
#------------------------------------------------------------------------------
#
#Response for player/521478. Successful:  <Response [200]>
#
#Total successful requests:  2324
#Completed :  89.38 %
#Elapsed time:  17226.21 s
#------------------------------------------------------------------------------
#
#Response for player/52683. Successful:  <Response [200]>
#
#Total successful requests:  2325
#Completed :  89.42 %
#Elapsed time:  17227.70 s
#------------------------------------------------------------------------------
#
#Response for player/52918. Successful:  <Response [200]>
#
#Total successful requests:  2326
#Completed :  89.46 %
#Elapsed time:  17253.54 s
#------------------------------------------------------------------------------
#
#Response for player/25584. Successful:  <Response [200]>
#
#Total successful requests:  2327
#Completed :  89.50 %
#Elapsed time:  17264.33 s
#------------------------------------------------------------------------------
#
#Response for player/303437. Successful:  <Response [200]>
#
#Total successful requests:  2328
#Completed :  89.54 %
#Elapsed time:  17265.25 s
#------------------------------------------------------------------------------
#
#Response for player/24616. Successful:  <Response [200]>
#
#Total successful requests:  2329
#Completed :  89.58 %
#Elapsed time:  17265.84 s
#------------------------------------------------------------------------------
#
#Response for player/53130. Successful:  <Response [200]>
#
#Total successful requests:  2330
#Completed :  89.62 %
#Elapsed time:  17269.48 s
#------------------------------------------------------------------------------
#
#Response for player/47663. Successful:  <Response [200]>
#
#Total successful requests:  2331
#Completed :  89.65 %
#Elapsed time:  17276.20 s
#------------------------------------------------------------------------------
#
#Response for player/50837. Successful:  <Response [200]>
#
#Total successful requests:  2332
#Completed :  89.69 %
#Elapsed time:  17280.78 s
#------------------------------------------------------------------------------
#
#Response for player/50879. Successful:  <Response [200]>
#
#Total successful requests:  2333
#Completed :  89.73 %
#Elapsed time:  17288.79 s
#------------------------------------------------------------------------------
#
#Response for player/8210. Successful:  <Response [200]>
#
#Total successful requests:  2334
#Completed :  89.77 %
#Elapsed time:  17305.98 s
#------------------------------------------------------------------------------
#
#Response for player/50851. Successful:  <Response [200]>
#
#Total successful requests:  2335
#Completed :  89.81 %
#Elapsed time:  17312.17 s
#------------------------------------------------------------------------------
#
#Response for player/25580. Successful:  <Response [200]>
#
#Total successful requests:  2336
#Completed :  89.85 %
#Elapsed time:  17313.52 s
#------------------------------------------------------------------------------
#
#Response for player/550137. Successful:  <Response [200]>
#
#Total successful requests:  2337
#Completed :  89.88 %
#Elapsed time:  17322.86 s
#------------------------------------------------------------------------------
#
#Response for player/332921. Successful:  <Response [200]>
#
#Total successful requests:  2338
#Completed :  89.92 %
#Elapsed time:  17337.27 s
#------------------------------------------------------------------------------
#
#Response for player/56225. Successful:  <Response [200]>
#
#Total successful requests:  2339
#Completed :  89.96 %
#Elapsed time:  17357.62 s
#------------------------------------------------------------------------------
#
#Response for player/24860. Successful:  <Response [200]>
#
#Total successful requests:  2340
#Completed :  90.00 %
#Elapsed time:  17359.60 s
#------------------------------------------------------------------------------
#
#Response for player/362079. Successful:  <Response [200]>
#
#Total successful requests:  2341
#Completed :  90.04 %
#Elapsed time:  17372.35 s
#------------------------------------------------------------------------------
#
#Response for player/10809. Successful:  <Response [200]>
#
#Total successful requests:  2342
#Completed :  90.08 %
#Elapsed time:  17380.60 s
#------------------------------------------------------------------------------
#
#Response for player/10846. Successful:  <Response [200]>
#
#Total successful requests:  2343
#Completed :  90.12 %
#Elapsed time:  17381.41 s
#------------------------------------------------------------------------------
#
#Response for player/48473. Successful:  <Response [200]>
#
#Total successful requests:  2344
#Completed :  90.15 %
#Elapsed time:  17388.60 s
#------------------------------------------------------------------------------
#
#Response for player/5130. Successful:  <Response [200]>
#
#Total successful requests:  2345
#Completed :  90.19 %
#Elapsed time:  17396.95 s
#------------------------------------------------------------------------------
#
#Response for player/568136. Successful:  <Response [200]>
#
#Total successful requests:  2346
#Completed :  90.23 %
#Elapsed time:  17405.23 s
#------------------------------------------------------------------------------
#
#Response for player/436749. Successful:  <Response [200]>
#
#Total successful requests:  2347
#Completed :  90.27 %
#Elapsed time:  17409.62 s
#------------------------------------------------------------------------------
#
#Response for player/28808. Successful:  <Response [200]>
#
#Total successful requests:  2348
#Completed :  90.31 %
#Elapsed time:  17426.14 s
#------------------------------------------------------------------------------
#
#Response for player/637496. Successful:  <Response [200]>
#
#Total successful requests:  2349
#Completed :  90.35 %
#Elapsed time:  17444.83 s
#------------------------------------------------------------------------------
#
#Response for player/40574. Successful:  <Response [200]>
#
#Total successful requests:  2350
#Completed :  90.38 %
#Elapsed time:  17446.66 s
#------------------------------------------------------------------------------
#
#Response for player/49207. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  2351
#Completed :  90.42 %
#Elapsed time:  17450.35 s
#------------------------------------------------------------------------------
#
#Response for player/15555. Successful:  <Response [200]>
#
#Total successful requests:  2352
#Completed :  90.46 %
#Elapsed time:  17459.19 s
#------------------------------------------------------------------------------
#
#Response for player/326017. Successful:  <Response [200]>
#
#Total successful requests:  2353
#Completed :  90.50 %
#Elapsed time:  17465.66 s
#------------------------------------------------------------------------------
#
#Response for player/315623. Successful:  <Response [200]>
#
#Total successful requests:  2354
#Completed :  90.54 %
#Elapsed time:  17474.46 s
#------------------------------------------------------------------------------
#
#Response for player/6441. Successful:  <Response [200]>
#
#Total successful requests:  2355
#Completed :  90.58 %
#Elapsed time:  17475.97 s
#------------------------------------------------------------------------------
#
#Response for player/41259. Successful:  <Response [200]>
#
#Total successful requests:  2356
#Completed :  90.62 %
#Elapsed time:  17482.06 s
#------------------------------------------------------------------------------
#
#Response for player/348037. Successful:  <Response [200]>
#
#Total successful requests:  2357
#Completed :  90.65 %
#Elapsed time:  17486.68 s
#------------------------------------------------------------------------------
#
#Response for player/439288. Successful:  <Response [200]>
#
#Total successful requests:  2358
#Completed :  90.69 %
#Elapsed time:  17489.31 s
#------------------------------------------------------------------------------
#
#Response for player/243073. Successful:  <Response [200]>
#
#Total successful requests:  2359
#Completed :  90.73 %
#Elapsed time:  17493.64 s
#------------------------------------------------------------------------------
#
#Response for player/56011. Successful:  <Response [200]>
#
#Total successful requests:  2360
#Completed :  90.77 %
#Elapsed time:  17497.56 s
#------------------------------------------------------------------------------
#
#Response for player/46255. Successful:  <Response [200]>
#
#Total successful requests:  2361
#Completed :  90.81 %
#Elapsed time:  17500.10 s
#------------------------------------------------------------------------------
#
#Response for player/299821. Successful:  <Response [200]>
#
#Total successful requests:  2362
#Completed :  90.85 %
#Elapsed time:  17507.83 s
#------------------------------------------------------------------------------
#
#Response for player/55640. Successful:  <Response [200]>
#
#Total successful requests:  2363
#Completed :  90.88 %
#Elapsed time:  17512.41 s
#------------------------------------------------------------------------------
#
#Response for player/6981. Successful:  <Response [200]>
#
#Total successful requests:  2364
#Completed :  90.92 %
#Elapsed time:  17514.91 s
#------------------------------------------------------------------------------
#
#Response for player/42057. Successful:  <Response [200]>
#
#Total successful requests:  2365
#Completed :  90.96 %
#Elapsed time:  17520.58 s
#------------------------------------------------------------------------------
#
#Response for player/32102. Successful:  <Response [200]>
#
#Total successful requests:  2366
#Completed :  91.00 %
#Elapsed time:  17527.44 s
#------------------------------------------------------------------------------
#
#Response for player/18389. Successful:  <Response [200]>
#
#Total successful requests:  2367
#Completed :  91.04 %
#Elapsed time:  17528.74 s
#------------------------------------------------------------------------------
#
#Response for player/24789. Successful:  <Response [200]>
#
#Total successful requests:  2368
#Completed :  91.08 %
#Elapsed time:  17529.77 s
#------------------------------------------------------------------------------
#
#Response for player/796331. Successful:  <Response [200]>
#
#Total successful requests:  2369
#Completed :  91.12 %
#Elapsed time:  17552.75 s
#------------------------------------------------------------------------------
#
#Response for player/52913. Successful:  <Response [200]>
#
#Total successful requests:  2370
#Completed :  91.15 %
#Elapsed time:  17558.43 s
#------------------------------------------------------------------------------
#
#Response for player/38255. Successful:  <Response [200]>
#
#Total successful requests:  2371
#Completed :  91.19 %
#Elapsed time:  17563.21 s
#------------------------------------------------------------------------------
#
#Response for player/25862. Successful:  <Response [200]>
#
#Total successful requests:  2372
#Completed :  91.23 %
#Elapsed time:  17566.30 s
#------------------------------------------------------------------------------
#
#Response for player/272994. Successful:  <Response [200]>
#
#Total successful requests:  2373
#Completed :  91.27 %
#Elapsed time:  17584.46 s
#------------------------------------------------------------------------------
#
#Response for player/50429. Successful:  <Response [200]>
#
#Total successful requests:  2374
#Completed :  91.31 %
#Elapsed time:  17585.99 s
#------------------------------------------------------------------------------
#
#Response for player/7691. Successful:  <Response [200]>
#
#Total successful requests:  2375
#Completed :  91.35 %
#Elapsed time:  17599.71 s
#------------------------------------------------------------------------------
#
#Response for player/301847. Successful:  <Response [200]>
#
#Total successful requests:  2376
#Completed :  91.38 %
#Elapsed time:  17601.48 s
#------------------------------------------------------------------------------
#
#Response for player/21484. Successful:  <Response [200]>
#
#Total successful requests:  2377
#Completed :  91.42 %
#Elapsed time:  17609.29 s
#------------------------------------------------------------------------------
#
#Response for player/21486. Successful:  <Response [200]>
#
#Total successful requests:  2378
#Completed :  91.46 %
#Elapsed time:  17623.05 s
#------------------------------------------------------------------------------
#
#Response for player/21512. Successful:  <Response [200]>
#
#Total successful requests:  2379
#Completed :  91.50 %
#Elapsed time:  17635.17 s
#------------------------------------------------------------------------------
#
#Response for player/317784. Successful:  <Response [200]>
#
#Total successful requests:  2380
#Completed :  91.54 %
#Elapsed time:  17643.27 s
#------------------------------------------------------------------------------
#
#Response for player/50836. Successful:  <Response [200]>
#
#Total successful requests:  2381
#Completed :  91.58 %
#Elapsed time:  17654.17 s
#------------------------------------------------------------------------------
#
#Response for player/413702. Successful:  <Response [200]>
#
#Total successful requests:  2382
#Completed :  91.62 %
#Elapsed time:  17656.67 s
#------------------------------------------------------------------------------
#
#Response for player/447587. Successful:  <Response [200]>
#
#Total successful requests:  2383
#Completed :  91.65 %
#Elapsed time:  17661.02 s
#------------------------------------------------------------------------------
#
#Response for player/36064. Successful:  <Response [200]>
#
#Total successful requests:  2384
#Completed :  91.69 %
#Elapsed time:  17664.87 s
#------------------------------------------------------------------------------
#
#Response for player/36078. Successful:  <Response [200]>
#
#Total successful requests:  2385
#Completed :  91.73 %
#Elapsed time:  17668.27 s
#------------------------------------------------------------------------------
#
#Response for player/23976. Successful:  <Response [200]>
#
#Total successful requests:  2386
#Completed :  91.77 %
#Elapsed time:  17671.09 s
#------------------------------------------------------------------------------
#
#Response for player/1063728. Successful:  <Response [200]>
#
#Total successful requests:  2387
#Completed :  91.81 %
#Elapsed time:  17673.88 s
#------------------------------------------------------------------------------
#
#Response for player/319613. Successful:  <Response [200]>
#
#Total successful requests:  2388
#Completed :  91.85 %
#Elapsed time:  17678.66 s
#------------------------------------------------------------------------------
#
#Response for player/3975. Successful:  <Response [200]>
#
#Total successful requests:  2389
#Completed :  91.88 %
#Elapsed time:  17679.99 s
#------------------------------------------------------------------------------
#
#Response for player/56235. Successful:  <Response [200]>
#
#Total successful requests:  2390
#Completed :  91.92 %
#Elapsed time:  17682.16 s
#------------------------------------------------------------------------------
#
#Response for player/23762. Successful:  <Response [200]>
#
#Total successful requests:  2391
#Completed :  91.96 %
#Elapsed time:  17688.02 s
#------------------------------------------------------------------------------
#
#Response for player/48298. Successful:  <Response [200]>
#
#Total successful requests:  2392
#Completed :  92.00 %
#Elapsed time:  17690.51 s
#------------------------------------------------------------------------------
#
#Response for player/9069. Successful:  <Response [200]>
#
#Total successful requests:  2393
#Completed :  92.04 %
#Elapsed time:  17711.38 s
#------------------------------------------------------------------------------
#
#Response for player/26896. Successful:  <Response [200]>
#
#Total successful requests:  2394
#Completed :  92.08 %
#Elapsed time:  17728.45 s
#------------------------------------------------------------------------------
#
#Response for player/937953. Successful:  <Response [200]>
#
#Total successful requests:  2395
#Completed :  92.12 %
#Elapsed time:  17737.86 s
#------------------------------------------------------------------------------
#
#Response for player/25881. Successful:  <Response [200]>
#
#Total successful requests:  2396
#Completed :  92.15 %
#Elapsed time:  17777.06 s
#------------------------------------------------------------------------------
#
#Response for player/36304. Successful:  <Response [200]>
#
#Total successful requests:  2397
#Completed :  92.19 %
#Elapsed time:  17778.74 s
#------------------------------------------------------------------------------
#
#Response for player/23764. Successful:  <Response [200]>
#
#Total successful requests:  2398
#Completed :  92.23 %
#Elapsed time:  17780.14 s
#------------------------------------------------------------------------------
#
#Response for player/44493. Successful:  <Response [200]>
#
#Total successful requests:  2399
#Completed :  92.27 %
#Elapsed time:  17782.47 s
#------------------------------------------------------------------------------
#
#Response for player/220521. Successful:  <Response [200]>
#
#Total successful requests:  2400
#Completed :  92.31 %
#Elapsed time:  17786.50 s
#------------------------------------------------------------------------------
#
#Response for page 3 Successful:  <Response [200]> 	=>
#

#list of players:  147
#Response for player/55893. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  2401
#Completed :  92.36 %
#Elapsed time:  17865.92 s
#------------------------------------------------------------------------------
#
#Response for player/303412. Successful:  <Response [200]>
#
#Total successful requests:  2402
#Completed :  92.41 %
#Elapsed time:  17871.83 s
#------------------------------------------------------------------------------
#
#Response for player/51883. Successful:  <Response [200]>
#
#Total successful requests:  2403
#Completed :  92.46 %
#Elapsed time:  17873.08 s
#------------------------------------------------------------------------------
#
#Response for player/13365. Successful:  <Response [200]>
#
#Total successful requests:  2404
#Completed :  92.52 %
#Elapsed time:  17878.85 s
#------------------------------------------------------------------------------
#
#Response for player/24903. Successful:  <Response [200]>
#
#Total successful requests:  2405
#Completed :  92.57 %
#Elapsed time:  17880.56 s
#------------------------------------------------------------------------------
#
#Response for player/37239. Successful:  <Response [200]>
#
#Total successful requests:  2406
#Completed :  92.62 %
#Elapsed time:  17882.37 s
#------------------------------------------------------------------------------
#
#Response for player/55912. Successful:  <Response [200]>
#
#Total successful requests:  2407
#Completed :  92.67 %
#Elapsed time:  17883.25 s
#------------------------------------------------------------------------------
#
#Response for player/5605. Successful:  <Response [200]>
#
#Total successful requests:  2408
#Completed :  92.73 %
#Elapsed time:  17885.57 s
#------------------------------------------------------------------------------
#
#Response for player/919495. Successful:  <Response [200]>
#
#Total successful requests:  2409
#Completed :  92.78 %
#Elapsed time:  17907.79 s
#------------------------------------------------------------------------------
#
#Response for player/772471. Successful:  <Response [200]>
#
#Total successful requests:  2410
#Completed :  92.83 %
#Elapsed time:  17913.60 s
#------------------------------------------------------------------------------
#
#Response for player/307756. Successful:  <Response [200]>
#
#Total successful requests:  2411
#Completed :  92.88 %
#Elapsed time:  17914.69 s
#------------------------------------------------------------------------------
#
#Response for player/1077307. Successful:  <Response [200]>
#
#Total successful requests:  2412
#Completed :  92.94 %
#Elapsed time:  17915.98 s
#------------------------------------------------------------------------------
#
#Response for player/465797. Successful:  <Response [200]>
#
#Total successful requests:  2413
#Completed :  92.99 %
#Elapsed time:  17922.89 s
#------------------------------------------------------------------------------
#
#Response for player/45888. Successful:  <Response [200]>
#
#Total successful requests:  2414
#Completed :  93.04 %
#Elapsed time:  17925.66 s
#------------------------------------------------------------------------------
#
#Response for player/16388. Successful:  <Response [200]>
#
#Total successful requests:  2415
#Completed :  93.09 %
#Elapsed time:  17927.78 s
#------------------------------------------------------------------------------
#
#Response for player/906783. Successful:  <Response [200]>
#
#Total successful requests:  2416
#Completed :  93.14 %
#Elapsed time:  17934.40 s
#------------------------------------------------------------------------------
#
#Response for player/430105. Successful:  <Response [200]>
#
#Total successful requests:  2417
#Completed :  93.20 %
#Elapsed time:  17937.10 s
#------------------------------------------------------------------------------
#
#Response for player/355267. Successful:  <Response [200]>
#
#Total successful requests:  2418
#Completed :  93.25 %
#Elapsed time:  17944.17 s
#------------------------------------------------------------------------------
#
#Response for player/37720. Successful:  <Response [200]>
#
#Total successful requests:  2419
#Completed :  93.30 %
#Elapsed time:  17953.84 s
#------------------------------------------------------------------------------
#
#Response for player/41452. Successful:  <Response [200]>
#
#Total successful requests:  2420
#Completed :  93.35 %
#Elapsed time:  17955.54 s
#------------------------------------------------------------------------------
#
#Response for player/227771. Successful:  <Response [200]>
#
#Total successful requests:  2421
#Completed :  93.41 %
#Elapsed time:  17957.54 s
#------------------------------------------------------------------------------
#
#Response for player/52490. Successful:  <Response [200]>
#
#Total successful requests:  2422
#Completed :  93.46 %
#Elapsed time:  17959.47 s
#------------------------------------------------------------------------------
#
#Response for player/42071. Successful:  <Response [200]>
#
#Total successful requests:  2423
#Completed :  93.51 %
#Elapsed time:  17977.57 s
#------------------------------------------------------------------------------
#
#Response for player/42160. Successful:  <Response [200]>
#
#Total successful requests:  2424
#Completed :  93.56 %
#Elapsed time:  17978.66 s
#------------------------------------------------------------------------------
#
#Response for player/42055. Successful:  <Response [200]>
#
#Total successful requests:  2425
#Completed :  93.62 %
#Elapsed time:  17983.75 s
#------------------------------------------------------------------------------
#
#Response for player/24228. Successful:  <Response [200]>
#
#Total successful requests:  2426
#Completed :  93.67 %
#Elapsed time:  17985.06 s
#------------------------------------------------------------------------------
#
#Response for player/793447. Successful:  <Response [200]>
#
#Total successful requests:  2427
#Completed :  93.72 %
#Elapsed time:  18011.18 s
#------------------------------------------------------------------------------
#
#Response for player/32091. Successful:  <Response [200]>
#
#Total successful requests:  2428
#Completed :  93.77 %
#Elapsed time:  18017.30 s
#------------------------------------------------------------------------------
#
#Response for player/333002. Successful:  <Response [200]>
#
#Total successful requests:  2429
#Completed :  93.83 %
#Elapsed time:  18042.21 s
#------------------------------------------------------------------------------
#
#Response for player/38066. Successful:  <Response [200]>
#
#Total successful requests:  2430
#Completed :  93.88 %
#Elapsed time:  18051.84 s
#------------------------------------------------------------------------------
#
#Response for player/38114. Successful:  <Response [200]>
#
#Total successful requests:  2431
#Completed :  93.93 %
#Elapsed time:  18055.12 s
#------------------------------------------------------------------------------
#
#Response for player/230552. Successful:  <Response [200]>
#
#Total successful requests:  2432
#Completed :  93.98 %
#Elapsed time:  18066.78 s
#------------------------------------------------------------------------------
#
#Response for player/52678. Successful:  <Response [200]>
#
#Total successful requests:  2433
#Completed :  94.03 %
#Elapsed time:  18089.70 s
#------------------------------------------------------------------------------
#
#Response for player/604302. Successful:  <Response [200]>
#
#Total successful requests:  2434
#Completed :  94.09 %
#Elapsed time:  18093.62 s
#------------------------------------------------------------------------------
#
#Response for player/46797. Successful:  <Response [200]>
#
#Total successful requests:  2435
#Completed :  94.14 %
#Elapsed time:  18096.94 s
#------------------------------------------------------------------------------
#
#Response for player/19314. Successful:  <Response [200]>
#
#Total successful requests:  2436
#Completed :  94.19 %
#Elapsed time:  18101.76 s
#------------------------------------------------------------------------------
#
#Response for player/56077. Successful:  <Response [200]>
#
#Total successful requests:  2437
#Completed :  94.24 %
#Elapsed time:  18103.43 s
#------------------------------------------------------------------------------
#
#Response for player/499594. Successful:  <Response [200]>
#
#Total successful requests:  2438
#Completed :  94.30 %
#Elapsed time:  18119.26 s
#------------------------------------------------------------------------------
#
#Response for player/500236. Successful:  <Response [200]>
#
#Total successful requests:  2439
#Completed :  94.35 %
#Elapsed time:  18120.31 s
#------------------------------------------------------------------------------
#
#Response for player/50246. Successful:  <Response [200]>
#
#Total successful requests:  2440
#Completed :  94.40 %
#Elapsed time:  18128.44 s
#------------------------------------------------------------------------------
#
#Response for player/343548. Successful:  <Response [200]>
#
#Total successful requests:  2441
#Completed :  94.45 %
#Elapsed time:  18141.16 s
#------------------------------------------------------------------------------
#
#Response for player/25609. Successful:  <Response [200]>
#
#Total successful requests:  2442
#Completed :  94.51 %
#Elapsed time:  18143.24 s
#------------------------------------------------------------------------------
#
#Response for player/227455. Successful:  <Response [200]>
#
#Total successful requests:  2443
#Completed :  94.56 %
#Elapsed time:  18155.67 s
#------------------------------------------------------------------------------
#
#Response for player/1174024. Successful:  <Response [200]>
#
#Total successful requests:  2444
#Completed :  94.61 %
#Elapsed time:  18165.66 s
#------------------------------------------------------------------------------
#
#Response for player/42634. Successful:  <Response [200]>
#
#Total successful requests:  2445
#Completed :  94.66 %
#Elapsed time:  18183.14 s
#------------------------------------------------------------------------------
#
#Response for player/42652. Successful:  <Response [200]>
#
#Total successful requests:  2446
#Completed :  94.71 %
#Elapsed time:  18195.89 s
#------------------------------------------------------------------------------
#
#Response for player/379145. Successful:  <Response [200]>
#
#Total successful requests:  2447
#Completed :  94.77 %
#Elapsed time:  18202.11 s
#------------------------------------------------------------------------------
#
#Response for player/633410. Successful:  <Response [200]>
#
#Total successful requests:  2448
#Completed :  94.82 %
#Elapsed time:  18206.50 s
#------------------------------------------------------------------------------
#
#Response for player/52946. Successful:  <Response [200]>
#
#Total successful requests:  2449
#Completed :  94.87 %
#Elapsed time:  18209.54 s
#------------------------------------------------------------------------------
#
#Response for player/43274. Successful:  <Response [200]>
#
#Total successful requests:  2450
#Completed :  94.92 %
#Elapsed time:  18214.32 s
#------------------------------------------------------------------------------
#
#Response for player/348133. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  2451
#Completed :  94.98 %
#Elapsed time:  18218.03 s
#------------------------------------------------------------------------------
#
#Response for player/914567. Successful:  <Response [200]>
#
#Total successful requests:  2452
#Completed :  95.03 %
#Elapsed time:  18220.85 s
#------------------------------------------------------------------------------
#
#Response for player/35657. Successful:  <Response [200]>
#
#Total successful requests:  2453
#Completed :  95.08 %
#Elapsed time:  18225.79 s
#------------------------------------------------------------------------------
#
#Response for player/24835. Successful:  <Response [200]>
#
#Total successful requests:  2454
#Completed :  95.13 %
#Elapsed time:  18227.75 s
#------------------------------------------------------------------------------
#
#Response for player/47903. Successful:  <Response [200]>
#
#Total successful requests:  2455
#Completed :  95.19 %
#Elapsed time:  18237.29 s
#------------------------------------------------------------------------------
#
#Response for player/56173. Successful:  <Response [200]>
#
#Total successful requests:  2456
#Completed :  95.24 %
#Elapsed time:  18266.04 s
#------------------------------------------------------------------------------
#
#Response for player/38963. Successful:  <Response [200]>
#
#Total successful requests:  2457
#Completed :  95.29 %
#Elapsed time:  18274.54 s
#------------------------------------------------------------------------------
#
#Response for player/39084. Successful:  <Response [200]>
#
#Total successful requests:  2458
#Completed :  95.34 %
#Elapsed time:  18276.13 s
#------------------------------------------------------------------------------
#
#Response for player/410763. Successful:  <Response [200]>
#
#Total successful requests:  2459
#Completed :  95.40 %
#Elapsed time:  18282.40 s
#------------------------------------------------------------------------------
#
#Response for player/48116. Successful:  <Response [200]>
#
#Total successful requests:  2460
#Completed :  95.45 %
#Elapsed time:  18286.62 s
#------------------------------------------------------------------------------
#
#Response for player/36187. Successful:  <Response [200]>
#
#Total successful requests:  2461
#Completed :  95.50 %
#Elapsed time:  18288.07 s
#------------------------------------------------------------------------------
#
#Response for player/349853. Successful:  <Response [200]>
#
#Total successful requests:  2462
#Completed :  95.55 %
#Elapsed time:  18301.37 s
#------------------------------------------------------------------------------
#
#Response for player/270135. Successful:  <Response [200]>
#
#Total successful requests:  2463
#Completed :  95.60 %
#Elapsed time:  18302.97 s
#------------------------------------------------------------------------------
#
#Response for player/39007. Successful:  <Response [200]>
#
#Total successful requests:  2464
#Completed :  95.66 %
#Elapsed time:  18313.27 s
#------------------------------------------------------------------------------
#
#Response for player/1115033. Successful:  <Response [200]>
#
#Total successful requests:  2465
#Completed :  95.71 %
#Elapsed time:  18315.32 s
#------------------------------------------------------------------------------
#
#Response for player/36285. Successful:  <Response [200]>
#
#Total successful requests:  2466
#Completed :  95.76 %
#Elapsed time:  18336.26 s
#------------------------------------------------------------------------------
#
#Response for player/4112. Successful:  <Response [200]>
#
#Total successful requests:  2467
#Completed :  95.81 %
#Elapsed time:  18350.20 s
#------------------------------------------------------------------------------
#
#Response for player/44097. Successful:  <Response [200]>
#
#Total successful requests:  2468
#Completed :  95.87 %
#Elapsed time:  18364.91 s
#------------------------------------------------------------------------------
#
#Response for player/310107. Successful:  <Response [200]>
#
#Total successful requests:  2469
#Completed :  95.92 %
#Elapsed time:  18376.60 s
#------------------------------------------------------------------------------
#
#Response for player/303435. Successful:  <Response [200]>
#
#Total successful requests:  2470
#Completed :  95.97 %
#Elapsed time:  18378.50 s
#------------------------------------------------------------------------------
#
#Response for player/4584. Successful:  <Response [200]>
#
#Total successful requests:  2471
#Completed :  96.02 %
#Elapsed time:  18381.72 s
#------------------------------------------------------------------------------
#
#Response for player/4600. Successful:  <Response [200]>
#
#Total successful requests:  2472
#Completed :  96.08 %
#Elapsed time:  18383.62 s
#------------------------------------------------------------------------------
#
#Response for player/4613. Successful:  <Response [200]>
#
#Total successful requests:  2473
#Completed :  96.13 %
#Elapsed time:  18386.54 s
#------------------------------------------------------------------------------
#
#Response for player/10797. Successful:  <Response [200]>
#
#Total successful requests:  2474
#Completed :  96.18 %
#Elapsed time:  18390.57 s
#------------------------------------------------------------------------------
#
#Response for player/25917. Successful:  <Response [200]>
#
#Total successful requests:  2475
#Completed :  96.23 %
#Elapsed time:  18412.28 s
#------------------------------------------------------------------------------
#
#Response for player/393279. Successful:  <Response [200]>
#
#Total successful requests:  2476
#Completed :  96.28 %
#Elapsed time:  18424.00 s
#------------------------------------------------------------------------------
#
#Response for player/348135. Successful:  <Response [200]>
#
#Total successful requests:  2477
#Completed :  96.34 %
#Elapsed time:  18430.69 s
#------------------------------------------------------------------------------
#
#Response for player/786925. Successful:  <Response [200]>
#
#Total successful requests:  2478
#Completed :  96.39 %
#Elapsed time:  18434.53 s
#------------------------------------------------------------------------------
#
#Response for player/48821. Successful:  <Response [200]>
#
#Total successful requests:  2479
#Completed :  96.44 %
#Elapsed time:  18439.66 s
#------------------------------------------------------------------------------
#
#Response for player/55472. Successful:  <Response [200]>
#
#Total successful requests:  2480
#Completed :  96.49 %
#Elapsed time:  18442.30 s
#------------------------------------------------------------------------------
#
#Response for player/317293. Successful:  <Response [200]>
#
#Total successful requests:  2481
#Completed :  96.55 %
#Elapsed time:  18447.04 s
#------------------------------------------------------------------------------
#
#Response for player/49081. Successful:  <Response [200]>
#
#Total successful requests:  2482
#Completed :  96.60 %
#Elapsed time:  18451.99 s
#------------------------------------------------------------------------------
#
#Response for player/45568. Successful:  <Response [200]>
#
#Total successful requests:  2483
#Completed :  96.65 %
#Elapsed time:  18453.86 s
#------------------------------------------------------------------------------
#
#Response for player/45431. Successful:  <Response [200]>
#
#Total successful requests:  2484
#Completed :  96.70 %
#Elapsed time:  18460.95 s
#------------------------------------------------------------------------------
#
#Response for player/5692. Successful:  <Response [200]>
#
#Total successful requests:  2485
#Completed :  96.76 %
#Elapsed time:  18470.49 s
#------------------------------------------------------------------------------
#
#Response for player/40575. Successful:  <Response [200]>
#
#Total successful requests:  2486
#Completed :  96.81 %
#Elapsed time:  18480.14 s
#------------------------------------------------------------------------------
#
#Response for player/24911. Successful:  <Response [200]>
#
#Total successful requests:  2487
#Completed :  96.86 %
#Elapsed time:  18493.80 s
#------------------------------------------------------------------------------
#
#Response for player/49344. Successful:  <Response [200]>
#
#Total successful requests:  2488
#Completed :  96.91 %
#Elapsed time:  18500.38 s
#------------------------------------------------------------------------------
#
#Response for player/392946. Successful:  <Response [200]>
#
#Total successful requests:  2489
#Completed :  96.96 %
#Elapsed time:  18506.49 s
#------------------------------------------------------------------------------
#
#Response for player/45800. Successful:  <Response [200]>
#
#Total successful requests:  2490
#Completed :  97.02 %
#Elapsed time:  18518.90 s
#------------------------------------------------------------------------------
#
#Response for player/416103. Successful:  <Response [200]>
#
#Total successful requests:  2491
#Completed :  97.07 %
#Elapsed time:  18522.38 s
#------------------------------------------------------------------------------
#
#Response for player/16219. Successful:  <Response [200]>
#
#Total successful requests:  2492
#Completed :  97.12 %
#Elapsed time:  18524.07 s
#------------------------------------------------------------------------------
#
#Response for player/24808. Successful:  <Response [200]>
#
#Total successful requests:  2493
#Completed :  97.17 %
#Elapsed time:  18532.20 s
#------------------------------------------------------------------------------
#
#Response for player/55568. Successful:  <Response [200]>
#
#Total successful requests:  2494
#Completed :  97.23 %
#Elapsed time:  18539.88 s
#------------------------------------------------------------------------------
#
#Response for player/6576. Successful:  <Response [200]>
#
#Total successful requests:  2495
#Completed :  97.28 %
#Elapsed time:  18542.76 s
#------------------------------------------------------------------------------
#
#Response for player/389666. Successful:  <Response [200]>
#
#Total successful requests:  2496
#Completed :  97.33 %
#Elapsed time:  18550.98 s
#------------------------------------------------------------------------------
#
#Response for player/940973. Successful:  <Response [200]>
#
#Total successful requests:  2497
#Completed :  97.38 %
#Elapsed time:  18557.87 s
#------------------------------------------------------------------------------
#
#Response for player/524044. Successful:  <Response [200]>
#
#Total successful requests:  2498
#Completed :  97.44 %
#Elapsed time:  18569.00 s
#------------------------------------------------------------------------------
#
#Response for player/23964. Successful:  <Response [200]>
#
#Total successful requests:  2499
#Completed :  97.49 %
#Elapsed time:  18571.88 s
#------------------------------------------------------------------------------
#
#Response for player/25021. Successful:  <Response [200]>
#
#Total successful requests:  2500
#Completed :  97.54 %
#Elapsed time:  18573.09 s
#------------------------------------------------------------------------------
#
#Response for player/6938. Successful:  <Response [200]>
#
#New Proxy POOL: ( 100 )
#
#Total successful requests:  2501
#Completed :  97.59 %
#Elapsed time:  18579.55 s
#------------------------------------------------------------------------------
#
#Response for player/486679. Successful:  <Response [200]>
#
#Total successful requests:  2502
#Completed :  97.65 %
#Elapsed time:  18594.37 s
#------------------------------------------------------------------------------
#
#Response for player/464626. Successful:  <Response [200]>
#
#Total successful requests:  2503
#Completed :  97.70 %
#Elapsed time:  18605.30 s
#------------------------------------------------------------------------------
#
#Response for player/299812. Successful:  <Response [200]>
#
#Total successful requests:  2504
#Completed :  97.75 %
#Elapsed time:  18610.58 s
#------------------------------------------------------------------------------
#
#Response for player/501012. Successful:  <Response [200]>
#
#Total successful requests:  2505
#Completed :  97.80 %
#Elapsed time:  18619.14 s
#------------------------------------------------------------------------------
#
#Response for player/215058. Successful:  <Response [200]>
#
#Total successful requests:  2506
#Completed :  97.85 %
#Elapsed time:  18627.65 s
#------------------------------------------------------------------------------
#
#Response for player/378496. Successful:  <Response [200]>
#
#Total successful requests:  2507
#Completed :  97.91 %
#Elapsed time:  18630.06 s
#------------------------------------------------------------------------------
#
#Response for player/32249. Successful:  <Response [200]>
#
#Total successful requests:  2508
#Completed :  97.96 %
#Elapsed time:  18648.16 s
#------------------------------------------------------------------------------
#
#Response for player/327947. Successful:  <Response [200]>
#
#Total successful requests:  2509
#Completed :  98.01 %
#Elapsed time:  18650.02 s
#------------------------------------------------------------------------------
#
#Response for player/49857. Successful:  <Response [200]>
#
#Total successful requests:  2510
#Completed :  98.06 %
#Elapsed time:  18653.02 s
#------------------------------------------------------------------------------
#
#Response for player/694037. Successful:  <Response [200]>
#
#Total successful requests:  2511
#Completed :  98.12 %
#Elapsed time:  18655.07 s
#------------------------------------------------------------------------------
#
#Response for player/395057. Successful:  <Response [200]>
#
#Total successful requests:  2512
#Completed :  98.17 %
#Elapsed time:  18657.84 s
#------------------------------------------------------------------------------
#
#Response for player/33085. Successful:  <Response [200]>
#
#Total successful requests:  2513
#Completed :  98.22 %
#Elapsed time:  18668.87 s
#------------------------------------------------------------------------------
#
#Response for player/50248. Successful:  <Response [200]>
#
#Total successful requests:  2514
#Completed :  98.27 %
#Elapsed time:  18676.90 s
#------------------------------------------------------------------------------
#
#Response for player/475816. Successful:  <Response [200]>
#
#Total successful requests:  2515
#Completed :  98.33 %
#Elapsed time:  18683.39 s
#------------------------------------------------------------------------------
#
#Response for player/42430. Successful:  <Response [200]>
#
#Total successful requests:  2516
#Completed :  98.38 %
#Elapsed time:  18685.70 s
#------------------------------------------------------------------------------
#
#Response for player/793907. Successful:  <Response [200]>
#
#Total successful requests:  2517
#Completed :  98.43 %
#Elapsed time:  18706.62 s
#------------------------------------------------------------------------------
#
#Response for player/25542. Successful:  <Response [200]>
#
#Total successful requests:  2518
#Completed :  98.48 %
#Elapsed time:  18711.16 s
#------------------------------------------------------------------------------
#
#Response for player/25552. Successful:  <Response [200]>
#
#Total successful requests:  2519
#Completed :  98.53 %
#Elapsed time:  18714.73 s
#------------------------------------------------------------------------------
#
#Response for player/43235. Successful:  <Response [200]>
#
#Total successful requests:  2520
#Completed :  98.59 %
#Elapsed time:  18725.39 s
#------------------------------------------------------------------------------
#
#Response for player/499660. Successful:  <Response [200]>
#
#Total successful requests:  2521
#Completed :  98.64 %
#Elapsed time:  18728.67 s
#------------------------------------------------------------------------------
#
#Response for player/524050. Successful:  <Response [200]>
#
#Total successful requests:  2522
#Completed :  98.69 %
#Elapsed time:  18731.33 s
#------------------------------------------------------------------------------
#
#Response for player/330223. Successful:  <Response [200]>
#
#Total successful requests:  2523
#Completed :  98.74 %
#Elapsed time:  18734.90 s
#------------------------------------------------------------------------------
#
#Response for player/47165. Successful:  <Response [200]>
#
#Total successful requests:  2524
#Completed :  98.80 %
#Elapsed time:  18736.77 s
#------------------------------------------------------------------------------
#
#Response for player/33891. Successful:  <Response [200]>
#
#Total successful requests:  2525
#Completed :  98.85 %
#Elapsed time:  18752.57 s
#------------------------------------------------------------------------------
#
#Response for player/25545. Successful:  <Response [200]>
#
#Total successful requests:  2526
#Completed :  98.90 %
#Elapsed time:  18755.99 s
#------------------------------------------------------------------------------
#
#Response for player/30288. Successful:  <Response [200]>
#
#Total successful requests:  2527
#Completed :  98.95 %
#Elapsed time:  18758.40 s
#------------------------------------------------------------------------------
#
#Response for player/230860. Successful:  <Response [200]>
#
#Total successful requests:  2528
#Completed :  99.01 %
#Elapsed time:  18760.43 s
#------------------------------------------------------------------------------
#
#Response for player/34057. Successful:  <Response [200]>
#
#Total successful requests:  2529
#Completed :  99.06 %
#Elapsed time:  18764.84 s
#------------------------------------------------------------------------------
#
#Response for player/52939. Successful:  <Response [200]>
#
#Total successful requests:  2530
#Completed :  99.11 %
#Elapsed time:  18770.14 s
#------------------------------------------------------------------------------
#
#Response for player/333029. Successful:  <Response [200]>
#
#Total successful requests:  2531
#Completed :  99.16 %
#Elapsed time:  18782.44 s
#------------------------------------------------------------------------------
#
#Response for player/537126. Successful:  <Response [200]>
#
#Total successful requests:  2532
#Completed :  99.22 %
#Elapsed time:  18786.54 s
#------------------------------------------------------------------------------
#
#Response for player/38405. Successful:  <Response [200]>
#
#Total successful requests:  2533
#Completed :  99.27 %
#Elapsed time:  18790.56 s
#------------------------------------------------------------------------------
#
#Response for player/38626. Successful:  <Response [200]>
#
#Total successful requests:  2534
#Completed :  99.32 %
#Elapsed time:  18797.58 s
#------------------------------------------------------------------------------
#
#Response for player/7944. Successful:  <Response [200]>
#
#Total successful requests:  2535
#Completed :  99.37 %
#Elapsed time:  18800.73 s
#------------------------------------------------------------------------------
#
#Response for player/21550. Successful:  <Response [200]>
#
#Total successful requests:  2536
#Completed :  99.42 %
#Elapsed time:  18803.80 s
#------------------------------------------------------------------------------
#
#Response for player/307237. Successful:  <Response [200]>
#
#Total successful requests:  2537
#Completed :  99.48 %
#Elapsed time:  18814.77 s
#------------------------------------------------------------------------------
#
#Response for player/53132. Successful:  <Response [200]>
#
#Total successful requests:  2538
#Completed :  99.53 %
#Elapsed time:  18820.91 s
#------------------------------------------------------------------------------
#
#Response for player/390484. Successful:  <Response [200]>
#
#Total successful requests:  2539
#Completed :  99.58 %
#Elapsed time:  18828.88 s
#------------------------------------------------------------------------------
#
#Response for player/56162. Successful:  <Response [200]>
#
#Total successful requests:  2540
#Completed :  99.63 %
#Elapsed time:  18830.71 s
#------------------------------------------------------------------------------
#
#Response for player/38740. Successful:  <Response [200]>
#
#Total successful requests:  2541
#Completed :  99.69 %
#Elapsed time:  18832.42 s
#------------------------------------------------------------------------------
#
#Response for player/719715. Successful:  <Response [200]>
#
#Total successful requests:  2542
#Completed :  99.74 %
#Elapsed time:  18834.56 s
#------------------------------------------------------------------------------
#
#Response for player/22328. Successful:  <Response [200]>
#
#Total successful requests:  2543
#Completed :  99.79 %
#Elapsed time:  18840.81 s
#------------------------------------------------------------------------------
#
#Response for player/50914. Successful:  <Response [200]>
#
#Total successful requests:  2544
#Completed :  99.84 %
#Elapsed time:  18843.58 s
#------------------------------------------------------------------------------
#
#Response for player/308410. Successful:  <Response [200]>
#
#Total successful requests:  2545
#Completed :  99.90 %
#Elapsed time:  18850.24 s
#------------------------------------------------------------------------------
#
#Response for player/712219. Successful:  <Response [200]>
#
#Total successful requests:  2546
#Completed :  99.95 %
#Elapsed time:  18851.56 s
#------------------------------------------------------------------------------
#
#Response for player/56166. Successful:  <Response [200]>
#
#Total successful requests:  2547
#Completed :  100.00 %
#Elapsed time:  18874.40 s
#------------------------------------------------------------------------------
#
#Done!
#Total time:  5.24  Hrs
