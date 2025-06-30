from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import pandas as pd

# 1. CSV 파일 읽기 ('unys.csv'라고 가정)
#    - A열: 대학명, B열: URL
df = pd.read_excel('unys.xlsx', usecols=[0, 1], names=['name', 'url'], header=0)

# 2. 크롬 드라이버 옵션 설정 (브라우저 창 띄우기)
options = Options()
options.add_argument("--disable-gpu")
options.add_argument("--start-maximized")

# 3. 드라이버 실행
driver = webdriver.Chrome(options=options)

# 4. 첫 번째 URL 열기
first_url = df.loc[0, 'url']
driver.get(first_url)
time.sleep(2)

# 5. 나머지 URL을 새 탭으로 순차적으로 열기
for idx in range(1, len(df)):
    url = df.loc[idx, 'url']
    driver.execute_script(f"window.open('{url}');")
    time.sleep(1)

# 6. 종료 전까지 유지 (Ctrl+C 로 중단)
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    driver.quit()
