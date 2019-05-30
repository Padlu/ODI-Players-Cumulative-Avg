import requests
from bs4 import BeautifulSoup
import csv
import time
import pickle
import os
from helper import proxy_request, generate_proxies, get_proxies_urls

############################################ ALL STATS OF THE PLAYER YEAR WISE ############################################

def check_pickle_exist():
	return os.path.isfile('./runs_scraping.pickle')

def main(url_idx, total_successful_req, writer):
	global proxies, urls
	start_t = time.time()
	print("Start time:", start_t)
	print("URLs to scrape: ", len(urls))
	print("Proxy POOL:\n", proxies)
	iterator = 0
	for i in range(url_idx,len(urls)):		# GET ALL DATA OF EACH PLAYER PLAYED IN THE ODI #
		response = proxy_request(1, proxies, 'get', urls[i])
		print(response)
		STAT_soup = BeautifulSoup(response.content, 'lxml')
		name = STAT_soup.find('div', {'class': 'icc-home'}).find('a').text[26:-30]
		print(name)
		for caption in STAT_soup.findAll("caption"):
			if caption.get_text() == 'Series averages':
				table = caption.find_parent('table', {'class': 'engineTable'})		# SINCE CLASS WITH SAME NAMES CAN BE MULTIPLE WE KNOW THERE IS ONLY ONE TABLE(WHICH WE WANT) WITH CAPTION == 'SERIES AVERAGES' #
		rows = table.findAll('tr',{'class':'data1'})
		for row in rows:
			cells = row.findAll('td')
			runs = cells[4].text # Runs Column
			date = str(cells[-4].contents[0])[3:-4] # Date Column
			writer.writerow([name,date,runs])		# STORE IT IN A CSV FILE FOR FUTURE USE FOR CALCULATION, ETC #
		if iterator % 50 == 0:		# GENERATE NEW POOL OF PROXIES AFTER EVERY 50 ITERATIONS #
			proxies = generate_proxies()
		pickle.dump([i,total_successful_req], open('runs_scraping.pickle','wb'))		# STORE THE PROGRESS FOR EACH PLAYER/ITERATION #
		iterator += 1
		total_successful_req += 1
		print("Total successful requests: ", total_successful_req)
		print("Completed : ",(total_successful_req/len(urls))*100)
		current_t = time.time()
		print("Current time: ",current_t,"\n------------------------------------------------------------------------------\n")
	print("Done!")
	print("Total time: ", (current_t - start_t)/3600, " Hrs")

proxies, urls = get_proxies_urls(1)		# GET THE POOL OF PROXIES AND REQUIRED URLS TO SCRAPE(INDIVIDUAL PLAYER PAGES) #

if os.path.isfile('./players_odi_individualyear_runs.csv'):		# IF FILE PRESENT JUST GET IT #
	f = open("players_odi_individualyear_runs.csv", "a", encoding='utf-8',newline='')
	writer = csv.writer(f)
else:															# IF FILE NOT PRESENT CREATE  IT #
	f = open("players_odi_individualyear_runs.csv", "a", encoding='utf-8',newline='')
	f.seek(0)
	f.truncate()
	writer = csv.writer(f)
	writer.writerow(['Name Of Player', 'Date Month Year', 'Runs'])

## I CREATED A PICKLE TO STORE THE PROGRESS AND CONTINUE FROM WHERE LEFT SO THAT IF LAPTOP SHUTSDOWN OR IDE CRASHES WE COULD RESUME OUR SCRAPPING FROM WHERE LEFT OFF ##

if check_pickle_exist():		# CHECK IF THE PICKLE EXISTS(PREVIOUSLY THE CODE HAS RAN) #
	pickle_in = open('runs_scraping.pickle', 'rb')
	url_idx, total_successful_req = pickle.load(pickle_in)		# GET THE REQUIRED DATA #
	main(url_idx, total_successful_req, writer)			# RESUME THE WORK #
else:		# CODE IS RUNNING FOR THE FIRST TIME #
	main(0, 0, writer)
	