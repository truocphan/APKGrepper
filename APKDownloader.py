'''
	APKDownloader v23.1.17 by Truoc Phan (@truocphan)
'''
from bs4 import BeautifulSoup
import httpx
import os
from tqdm import tqdm

class APKCombo:
	def __init__(self, packageId, versions=list(), DownloadFolder="."):
		if type(versions) != list:
			exit("eRROR")
		self.packageId = str(packageId)
		self.ori_versions = list(set(versions))
		self.versions = list(set(versions))
		self.appName = ""
		self.DownloadFolder = os.path.abspath(os.path.join(DownloadFolder, "APKCombo"))
		self.apkcombo_host = "https://apkcombo.com"
		self.apkcombo_headers = {
			"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:108.0) Gecko/20100101 Firefox/108.0"
		}
		self.client = httpx.Client(http2=True, headers=self.apkcombo_headers, verify=False, timeout=30)
		self.results = {}

		if not os.path.isdir(self.DownloadFolder): os.mkdir(self.DownloadFolder)

	def download(self):
		res = self.client.get(self.apkcombo_host+"/search/"+self.packageId)

		if res.status_code != 302:
			print("\033[31m[-]",self.packageId, "not found on APKCombo\033[0m")
			self.results[self.packageId] = {
				"status": "error",
				"message": self.packageId+" not found on APKCombo"
			}
		else:
			self.results[self.packageId] = {
				"status": "success",
				"data": {
					"success": {},
					"error": []
				}
			}

			if not os.path.isdir(os.path.join(self.DownloadFolder, self.packageId)): os.mkdir(os.path.join(self.DownloadFolder, self.packageId))

			location = res.headers["location"]

			page = 1
			while True:
				res = self.client.get(self.apkcombo_host+location+"old-versions/?page="+str(page))

				if res.status_code == 302 and page == 1:
					try:
						res = self.client.get(self.apkcombo_host+location+"download/apk")

						soup = BeautifulSoup(res.content, "html.parser")

						downloadlink = soup.find(id="best-variant-tab").find("a", class_="variant").get("href")

						appName = soup.find("span", class_="vername").text
					except Exception as e:
						res = self.client.post(self.apkcombo_host+location+"dl", files=dict(package_name=self.packageId))

						soup = BeautifulSoup(res.content, "html.parser")

						downloadlink = soup.find(id="best-variant-tab").find("a", class_="variant").get("href")

						appName = soup.find("span", class_="vername").text

					self.appName = " ".join(appName.split(" ")[:-1])

					appVer = appName.split(" ")[-1]
					if appVer in self.versions or len(self.ori_versions) == 0:
						if appVer in self.versions: self.versions.remove(appVer)

						try:
							progress_bar = tqdm(unit="iB", unit_scale=True, desc="[*] Downloading \"{}.apk\"".format(appName))

							with open(os.path.join(self.DownloadFolder, self.packageId, appName+".apk"), "wb") as f:
								with httpx.stream("GET", downloadlink, headers=self.apkcombo_headers, timeout=30) as res:
									for chunk in res.iter_bytes():
										progress_bar.update(len(chunk))
										f.write(chunk)

							progress_bar.close()

							print("\033[32m[+] \""+appName+".apk\" saved at "+os.path.join(self.DownloadFolder, self.packageId) + "\033[0m")
							self.results[self.packageId]["data"]["success"][appName] = os.path.join(self.DownloadFolder, self.packageId, appName+".apk")
						except httpx.ReadTimeout:
							if not os.path.isfile(os.path.join(self.DownloadFolder, self.packageId, appName+".apk")): os.unlink(os.path.join(self.DownloadFolder, self.packageId, appName+".apk"))
							self.results[self.packageId]["data"]["error"].append(appName)
					break
				else:
					soup = BeautifulSoup(res.content, "html.parser")

					if len(soup.find_all("a", class_="ver-item")) == 0: break

					for i in soup.find_all("a", class_="ver-item"):
						res = self.client.get(self.apkcombo_host+i.get("href"))
						soup = BeautifulSoup(res.content, "html.parser")

						downloadlink = soup.find(id="best-variant-tab").find("a", class_="variant").get("href")

						appName = soup.find("span", class_="vername").text
						self.appName = " ".join(appName.split(" ")[:-1])

						appVer = appName.split(" ")[-1]
						if appVer in self.versions or len(self.ori_versions) == 0:
							if appVer in self.versions: self.versions.remove(appVer)

							res = self.client.post(self.apkcombo_host+"/checkin")
							checkin = res.text

							res = self.client.get(downloadlink+"&"+checkin)

							try:
								progress_bar = tqdm(unit="iB", unit_scale=True, desc="[*] Downloading \"{}.apk\"".format(appName))

								with open(os.path.join(self.DownloadFolder, self.packageId, appName+".apk"), "wb") as f:
									with httpx.stream("GET", res.headers["location"], headers=self.apkcombo_headers, timeout=30) as res:
										for chunk in res.iter_bytes():
											progress_bar.update(len(chunk))
											f.write(chunk)

								progress_bar.close()

								print("\033[32m[+] \""+appName+".apk\" saved at "+os.path.join(self.DownloadFolder, self.packageId) + "\033[0m")
								self.results[self.packageId]["data"]["success"][appName] = os.path.join(self.DownloadFolder, self.packageId, appName+".apk")
							except httpx.ReadTimeout:
								if not os.path.isfile(os.path.join(self.DownloadFolder, self.packageId, appName+".apk")): os.unlink(os.path.join(self.DownloadFolder, self.packageId, appName+".apk"))
								self.results[self.packageId]["data"]["error"].append(appName)
				page += 1

			for ver in self.versions:
				self.results[self.packageId]["data"]["error"].append(self.appName + " " + ver + " not found")
