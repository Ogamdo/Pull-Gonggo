import os
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

import pandas as pd
import requests
from dotenv import load_dotenv

# -----------------------------------------------------
# 1) 환경 변수 로드
# -----------------------------------------------------
load_dotenv()  # 프로젝트 루트의 .env 파일을 자동으로 로드

# -----------------------------------------------------
# 2) 설정 클래스
# -----------------------------------------------------
@dataclass
class Config:
    """API 키, URL, 파일명 등을 중앙에서 관리"""
    service_key: str = os.getenv("G2B_SERVICE_KEY")  # .env에서 읽어옴
    base_url: str = "http://apis.data.go.kr/1230000/BidPublicInfoService/getBidPblancListInfoServc"
    search_terms_file: str = "search_terms.xlsx"   # 엑셀 파일명
    term_col: str = "keyword"                      # 키워드 컬럼명
    max_rows: int = 100                            # 한 번에 조회할 최대 건수
    timeout: int = 10                              # HTTP 요청 타임아웃(초)

    def result_fname(self, date: str) -> str:
        return f"{date}_search_results.xlsx"

    def combined_fname(self, date: str) -> str:
        return f"{date}_combined_search_results.xlsx"

# -----------------------------------------------------
# 3) 유틸리티 함수
# -----------------------------------------------------
def get_date_str(offset_days: int = 0) -> str:
    return (datetime.now() + timedelta(days=offset_days)).strftime("%Y%m%d")

def api_date_range(date: str) -> Tuple[str, str]:
    return date + "0000", date + "2359"

def setup_logger() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("g2b_search.log", encoding="utf-8")
        ]
    )
    return logging.getLogger()

# -----------------------------------------------------
# 4) 핵심 기능
# -----------------------------------------------------
def read_search_terms(fname: str, col: str) -> List[str]:
    """엑셀에서 키워드 목록 읽기"""
    df = pd.read_excel(fname, usecols=[col])
    return df[col].dropna().tolist()

def search_bids(term: str, date: str, cfg: Config, logger: logging.Logger) -> List[Dict]:
    """단일 키워드·단일 날짜 입찰공고 검색"""
    start_dt, end_dt = api_date_range(date)
    params = {
        "ServiceKey": cfg.service_key,
        "type": "json",
        "numOfRows": cfg.max_rows,
        "pageNo": 1,
        "inqryDiv": 1,
        "inqryBgnDt": start_dt,
        "inqryEndDt": end_dt,
        "bidNtceNm": term
    }
    try:
        logger.info(f"[{date}] '{term}' 검색 시작")
        resp = requests.get(cfg.base_url, params=params, timeout=cfg.timeout)
        resp.raise_for_status()
        items = resp.json().get("response", {}).get("body", {}).get("items", [])
        results = [{
            "keyword": term,
            "title": it.get("bidNtceNm"),
            "bid_number": it.get("bidNtceNo"),
            "url": it.get("bidNtceDtlUrl"),
            "date": date
        } for it in items]
        logger.info(f"[{date}] '{term}' → {len(results)}건 발견")
        return results
    except Exception as e:
        logger.error(f"Error searching '{term}' on {date}: {e}")
        return []

def merge_results(today: List[Dict], yesterday: List[Dict], logger: logging.Logger) -> List[Dict]:
    """어제 결과 중 오늘에 없는 공고만 오늘 결과에 추가"""
    today_ids = {r["bid_number"] for r in today}
    extra = [r for r in yesterday if r["bid_number"] not in today_ids]
    logger.info(f"어제 결과 중 {len(extra)}건을 오늘 결과에 추가")
    return today + extra

# -----------------------------------------------------
# 5) 메인 워크플로우
# -----------------------------------------------------
def main():
    cfg = Config()
    logger = setup_logger()

    # API 키 설정 확인
    if not cfg.service_key:
        logger.error("서비스 키가 설정되지 않았습니다. .env 파일을 확인하세요.")
        return

    # 1. 검색어 로드
    try:
        terms = read_search_terms(cfg.search_terms_file, cfg.term_col)
        logger.info(f"키워드 {len(terms)}개 로드: {terms}")
    except Exception as e:
        logger.error(f"검색어 파일 로드 실패: {e}")
        return

    # 2. 날짜 설정
    today = get_date_str(0)
    yesterday = get_date_str(-1)

    # 3. 오늘 검색
    results_today = []
    for kw in terms:
        results_today.extend(search_bids(kw, today, cfg, logger))

    # 4. 오늘 결과 저장
    df_today = pd.DataFrame(results_today)
    fn_today = cfg.result_fname(today)
    df_today.to_excel(fn_today, index=False)
    logger.info(f"오늘 결과 저장: {fn_today}")

    # 5. 어제 파일이 없으면 병합 건너뛰기
    fn_yesterday = cfg.result_fname(yesterday)
    if os.path.exists(fn_yesterday):
        df_y = pd.read_excel(fn_yesterday)
        results_yesterday = df_y.to_dict("records")
        combined = merge_results(results_today, results_yesterday, logger)
        df_comb = pd.DataFrame(combined)
        fn_comb = cfg.combined_fname(today)
        df_comb.to_excel(fn_comb, index=False)
        logger.info(f"병합 결과 저장: {fn_comb}")
    else:
        logger.info(f"어제 파일 없음({fn_yesterday}) → 병합 건너뛰고 오늘 파일만 생성")

if __name__ == "__main__":
    main()
