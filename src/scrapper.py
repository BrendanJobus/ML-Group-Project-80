from bs4 import BeautifulSoup as soup
import pandas as pd
import requests
from seleniumwire import webdriver
import time

def parseAndCleanData(data, address):
	priceAndBed, rest = data.split("bd")
	bath, rest = rest.split("ba")
	area, _ = rest.split("sqft")
	startOfBeds = priceAndBed.rindex(',') + 4
	price = priceAndBed[:startOfBeds].replace("$", "")
	bed = priceAndBed[startOfBeds:]
	price = price.replace(",", "")
	if bed.find("--") != -1:
		bed = 0
	else:
		bed = int(bed)
	if bath.find("--") != -1:
		bath = 0
	else:
		bath = int(bath)
	if area.find("--") != -1:
		area = 0
	else:
		area = int(area.replace(",", ""))
	prices.append(price); beds.append(bed); baths.append(bath); areas.append(area); addresses.append(address)

def parseAndCleanDetails(details):
	yearBuilt, parkingSpots = 0, 0
	for detail in details:
		if detail.get_text().find("Built") != -1:
			yearBuilt = detail.get_text()
			yearBuilt = int(yearBuilt[9:])
		elif detail.get_text().find("Parking space") != -1:
			parkingSpots = detail.get_text()
			parkingSpots = int(parkingSpots.replace("Parking space", ""))
		elif detail.get_text().find("Parking spaces") != -1:
			parkingSpots = detail.get_text()
			parkingSpots = int(parkingSpots.replace("Parking spaces", ""))
	yearOfConstruction.append(yearBuilt)
	parkingSpaces.append(parkingSpots)

def sleepSchedule(startTime, timeSinceLastHibernate):
	if timeSinceLastHibernate == 180:
		print("hibernating")
		time.sleep(120)
		timeSinceLastHibernate = 0
	elif time.perf_counter() - startTime >= 20:
		print("sleeping")
		time.sleep(20)
		startTime = time.perf_counter()
		timeSinceLastHibernate += 20

def checkForDuplicates(address):
	if address in duplicateChecks: 
		return True
	else: 
		return False

def extractDataFromHtml(htmlDoc, duplicateChecks):
	addToDuplicateChecks = False
	duplicates = 0
	if not duplicateChecks:
		print("first page")
		addToDuplicateChecks = True

	for listing in htmlDoc.findAll('a', {'class': 'list-card-link list-card-link-top-margin list-card-img'}, href=True):
		print(f"Found URL: {listing['href']}")
		if addToDuplicateChecks:
			duplicateChecks.append(listing['href'])
		elif checkForDuplicates(listing['href']):
			duplicates += 1
			print("Link is a duplicate")
			if duplicates >= 5:
				print("Too many duplicates found, going to next borough")
				return True
			else:
				continue
		gotSummary, gotDetails = False, False
		while(not gotSummary or not gotDetails):
			listingHtml = requests.get(url=listing['href'], headers=header)
			if listingHtml.status_code != 200:
				break

			listingHtmlDoc = soup(listingHtml.content, 'html.parser')
			if listingHtmlDoc.find('div', {'class': 'ds-summary-row-container'}) and not gotSummary:
				data = listingHtmlDoc.find('div', {'class': 'ds-summary-row-container'}).get_text()
				address = listingHtmlDoc.find('h1', {'id': 'ds-chip-property-address'}).get_text()
				gotSummary = True
				parseAndCleanData(data, address)
			if listingHtmlDoc.find('ul', {'class': 'hdp__sc-1m6tl3b-0 gpsjXQ'}) and not gotDetails:
				deets = listingHtmlDoc.findAll('span', {'class': 'Text-c11n-8-53-2__sc-aiai24-0 hdp__sc-1esuh59-3 cvftlt hjZqSR'})
				parseAndCleanDetails(deets)
				gotDetails = True
	return False

def writeData():
	df = pd.DataFrame({'Address': addresses, 'Beds': beds, 'Baths': baths, 'Area': areas, 'Construction': yearOfConstruction, 'Parking': parkingSpaces, 'Price': prices})
	df.to_csv('data/listings.csv', index=False, encoding='utf-8')
	print(df.size)

def interceptor(request):
	del request.headers['user-agent']
	request.headers['user-agent'] = 'Mozilla/5.0 (X11; Linux x86_64; rv:94.0) Gecko/20100101 Firefox/94.0'
	del request.headers['Referer']
	request.headers['Referer'] = 'https://www.zillow.com/brooklyn-new-york-ny/?searchQueryState=%7B%22pagination'

prices, beds, baths, addresses, areas, yearOfConstruction, parkingSpaces = [], [], [], [], [], [], []

listOfNeighborhoods = ['Manhattan', 'Brooklyn', 'Bronx', 'Staten-Island', 'Queens']
searchQueryExtension = {'Manhattan': ['%7B%22usersSearchTerm%22%3A%22Manhattan%2C%20New%20York%2C%20NY%22%2C%22mapBounds%22%3A%7B%22west%22%3A-74.040174%2C%22east%22%3A-73.906999%2C%22south%22%3A40.680598%2C%22north%22%3A40.879278%7D%2C%22regionSelection%22%3A%5B%7B%22regionId%22%3A12530%2C%22regionType%22%3A17%7D%5D%2C%22isMapVisible%22%3Afalse%2C%22filterState%22%3A%7B%22sort%22%3A%7B%22value%22%3A%22globalrelevanceex%22%7D%2C%22ah%22%3A%7B%22value%22%3Atrue%7D%2C%22price%22%3A%7B%22max%22%3A', '%2C%22min%22%3A', '%7D%2C%22mp%22%3A%7B%22max%22%3A1656%2C%22min%22%3A331%7D%7D%2C%22isListVisible%22%3Atrue%2C%22category%22%3A%22cat1%22%7D'],
}

header = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:94.0) Gecko/20100101 Firefox/94.0',
  'referer': 'https://www.zillow.com/brooklyn-new-york-ny/?searchQueryState=%7B%22pagination'
}

for neighborhood in listOfNeighborhoods:
	duplicateChecks = []
	for page in range (1,100):
		driver = webdriver.Chrome()
		if page > 1:
			url = 'https://www.zillow.com/' + neighborhood + '-new-york-ny/' + str(page) + '_p/?searchQueryState=' +  searchQueryExtension.get(neighborhood)[0] + str(500000) + searchQueryExtension.get(neighborhood)[1] + str(100000) + searchQueryExtension.get(neighborhood)[2]
		else:
			url = 'https://www.zillow.com/' + neighborhood + '-new-york-ny/?searchQueryState=' + searchQueryExtension.get(neighborhood)[0] + str(500000) + searchQueryExtension.get(neighborhood)[1] + str(100000) + searchQueryExtension.get(neighborhood)[2]
		driver.request_interceptor = interceptor
		driver.get(url)
		time.sleep(1)
		driver.execute_script("window.scrollTo({top: document.body.scrollHeight, left: 0, behavior: 'smooth'});")
		time.sleep(5)
		html = driver.page_source
		htmlDoc = soup(html, 'html.parser')
		goToNextBorough = extractDataFromHtml(htmlDoc, duplicateChecks)
		if goToNextBorough:
			break
		driver.close()

writeData()