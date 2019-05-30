#TASK:
	#get a list of all cricket players who have ever played a ODI match.
	#get a list the number of runs they've made every year of their career(from 1970 - 2019).
	#cumulate all the runs of each player from whatever year they've started playing ODI till 2019 or till any year you put in the function.

import requests
from bs4 import BeautifulSoup
import csv
import time
import os
from helper import proxy_request, generate_proxies, get_proxies_urls

############################################ NAMES OF ALL THE PLAYERS PLAYED IN ODI ############################################

def main(writer):
	global proxies, urls
	start_t = time.time()
	print("Start time:", start_t)
	print("URLs to scrape:", len(urls))
	print("Proxy POOL: (",len(proxies),")\n", proxies)
	iterator = 0
	for url in urls:		# GET ALL UNIQUE PLAYERS LIST OF NAMES AND THEIR INDIVIDUAL PAGES LINK #
		response = proxy_request(0, proxies,'get', url)
		print(response)
		ODI_soup = BeautifulSoup(response.content, 'lxml')
		for caption in ODI_soup.findAll("caption"):
			if caption.get_text() == 'Overall figures':
				table = caption.find_parent('table', {'class': 'engineTable'})		# SINCE CLASS WITH SAME NAMES CAN BE MULTIPLE WE KNOW THERE IS ONLY ONE TABLE(WHICH WE WANT) WITH CAPTION == 'OVERALL FIGURES' #
		rows = table.findAll('tr',{'class':'data1'})
		for row in rows:
			link = row.findAll('a')[0]
			name_of_player = str(link.contents[0])[3:-4]
			link_of_player_bio = 'http://stats.espncricinfo.com' + link.attrs['href']		#BIO LINK IF WANT TO SCRAP MORE ON THE PLAYER #
			link_of_player_stats = 'http://stats.espncricinfo.com/ci/engine' + str(link.attrs['href'])[11:] + '?class=2;template=results;type=batting;view=series'
			writer.writerow([name_of_player,link_of_player_bio,link_of_player_stats])		# STORE IT IN A CSV FILE FOR FUTURE SCRAPING #
		if iterator % 50 == 0:		# GENERATE NEW POOL OF PROXIES AFTER EVERY 50 ITERATIONS #
			proxies = generate_proxies()
		iterator += 1
		print("Total successful requests: ", iterator)
		print("Completed : ",(iterator/len(urls))*100)
		current_t = time.time()
		print("Current time: ",current_t,"\n------------------------------------------------------------------------------\n")
	print("Done!")
	print("Total time: ", (current_t - start_t)/3600, " Hrs")

proxies, urls = get_proxies_urls(0)		# GET THE POOL OF PROXIES AND REQUIRED URLS TO SCRAPE(ALL THE PAGES WITH ALL PLAYERS PLAYED IN THE ODI) #

if os.path.isfile('./players_odi.csv.csv'):		# IF FILE PRESENT JUST GET IT #
	f = open("players_odi.csv", "a", encoding='utf-8',newline='')
	writer = csv.writer(f)
else:		# IF FILE NOT PRESENT CREATE  IT #
	f = open("players_odi.csv", "a", encoding='utf-8',newline='')
	f.seek(0)
	f.truncate()
	writer = csv.writer(f)
	writer.writerow(['Name Of Player', 'Bio Link', 'ODI Stats link'])

main(writer)