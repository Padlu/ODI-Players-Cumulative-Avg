import csv

def get_spaces(name, runs):		# JUST FOR PRINTING NEATLY # (((EXTRA WORK JUST TO IMPRESS!))) #
	name_s = ''.join(' ' for x in range(0,(27 - len(name))))
	runs_s = ''.join(' ' for x in range(0,(5 - len(str(runs)))))
	year_s = ''.join(' ' for x in range(0,3))
	return name_s, runs_s, year_s
	
def get_sum_of_runs(i, name, start_year, till_year):
	f = open("players_odi_individualyear_runs.csv", "r", encoding='utf-8',newline='')
	reader = csv.reader(f)
	sum_runs = 0
	player = {'name':name, 'runs': sum_runs, 'start_year': start_year, 'end_year': till_year}		# PLAYER DATA #
	for idx, row in enumerate(reader):
		if i == 0:		# SUM OF RUNS FOR PARTICULAR PLAYER FOR PARTICULAR RANGE OF YEARS #
			if row[0] == name and int(row[1][-4:]) >= start_year and int(row[1][-4:]) <= till_year :
				if start_year == 0:
					start_year = int(row[1][-4:])
				if row[2] != '-':
					sum_runs += int(row[2])
		elif i == 1:		# SUM OF RUNS FOR EACH PLAYER'S WHOLE CAREER IN ODI #
			if row[0] == name:
				if start_year == 0:
					start_year = int(row[1][-4:])
				till_year = int(row[1][-4:])
				if row[2] != '-':
					sum_runs += int(row[2])
	player['runs'] = sum_runs
	player['start_year'] = start_year
	player['end_year'] = till_year
	return player	
			

def main():
	f = open("players_odi.csv", "r", encoding='utf-8',newline='')
	reader = csv.reader(f)
	print("Performing SUM of total runs of each player in ODI career : \n")
	print("+-------+------------------------------+--------------+--------------+--------+")
	print("+  ID#  +         PLAYER NAME          +  START YEAR  +   END YEAR   +  RUNS  +")
	print("+-------+------------------------------+--------------+--------------+--------+")
	for idx, row in enumerate(reader):		# PRINTS SUM OF RUNS FOR EACH PLAYER'S WHOLE CAREER IN ODI #
		if idx == 0:
			continue
		player = get_sum_of_runs(1, row[0], 0, 0)
		name_space, runs_space, year_space = get_spaces(player['name'], player['runs'])
		id_space = ''.join(' ' for x in range(0,(4 - len(str(idx)))))
		print("+", idx, id_space,"+", player['name'],name_space, "+", year_space, player['start_year'], year_space, "+", year_space, player['end_year'], year_space, "+", runs_space, player['runs'], "+")
		print("+-------+------------------------------+--------------+--------------+--------+")
	print("\n")
	while 1:		# PRINTS SUM OF RUNS FOR PARTICULAR PLAYER FOR PARTICULAR RANGE OF YEARS #
		i = input("To Perform SUM of total runs of each player till particular period in the career : (yes)\n")	
		if i.lower() == 'yes':
			name = input("Enter name of the player. Caution! Name must match from the data to get the result.\n")
			start_year = input("Enter start year. Put (0) if you want the sum of the runs from start of player's career.\n")
			till_year = input("Enter end year. Put any year till you want the sum of the runs player's career.\n")
			player = get_sum_of_runs(0, name, int(start_year), int(till_year)yes)
			print("+------------------------------+--------------+--------------+--------+")
			print("+         PLAYER NAME          +  START YEAR  +   TILLYEAR   +  RUNS  +")
			print("+------------------------------+--------------+--------------+--------+")
			name_space, runs_space, year_space = get_spaces(player['name'], player['runs'])
			print("+", player['name'],name_space, "+", year_space, player['start_year'], year_space, "+", year_space, player['end_year'], year_space, "+", runs_space, player['runs'], "+")
			print("+------------------------------+--------------+--------------+--------+")
		else:
			break
		
main()

## REALLY HOPE TO WORK WITH YOU. ##
