import requests
from bs4 import BeautifulSoup
import pandas as pd

def scrape_starbill(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    
    data_list = []
    tbody = soup.find("tbody")
    for row in tbody.find_all("tr", class_="topline"):
        cols = row.find_all("td", class_="first")
        if len(cols) >= 5:
            record = {
                "항목": cols[0].get_text(strip=True),
                "구분": cols[1].get_text(strip=True),
                "발주처": cols[2].get_text(strip=True),
                "공고명": cols[3].get_text(strip=True),
                "접수마감일": cols[4].get_text(strip=True)
            }
            data_list.append(record)
    
    df = pd.DataFrame(data_list, columns=["항목", "구분", "발주처", "공고명", "접수마감일"])
    df.to_excel("starbill_bids.xlsx", index=False, engine="openpyxl")
    print(f"Saved {len(data_list)} records to starbill_bids.xlsx")

if __name__ == "__main__":
    scrape_starbill("https://starbill.co.kr/your-university-page")
