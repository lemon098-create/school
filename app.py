import streamlit as st
import requests
import re

st.set_page_config(page_title="급식알리미", page_icon="🍱")

API_KEY = "1ec7431e0f884feda517a34fdd34d72b"

def find_school(office_code, school_name):
    url = "https://open.neis.go.kr/hub/schoolInfo"
    params = {
        "KEY": API_KEY, "Type": "json",
        "pIndex": 1, "pSize": 5,
        "ATPT_OFCDC_SC_CODE": office_code,
        "SCHUL_NM": school_name
    }
    data = requests.get(url, params=params).json()
    school = data["schoolInfo"][1]["row"][0]
    return school["SD_SCHUL_CODE"]

def get_meal(office_code, school_code, date):
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "KEY": API_KEY, "Type": "json",
        "pIndex": 1, "pSize": 5,
        "ATPT_OFCDC_SC_CODE": office_code,
        "SD_SCHUL_CODE": school_code,
        "MLSV_YMD": date
    }
    data = requests.get(url, params=params).json()
    return data["mealServiceDietInfo"][1]["row"][0]["DDISH_NM"]

def clean_dish_name(dish):
    dish = re.sub(r"[\(\[].*?[\)\]]", "", dish)
    return dish.strip("*! ")

def clean_menu(raw):
    return [clean_dish_name(d) for d in raw.split("<br/>")]

st.title("🍱 급식알리미")

offices = {
    "서울특별시교육청": "B10", "부산광역시교육청": "C10",
    "대구광역시교육청": "D10", "인천광역시교육청": "E10",
    "광주광역시교육청": "F10", "대전광역시교육청": "G10",
    "울산광역시교육청": "H10", "세종특별자치시교육청": "I10",
    "경기도교육청": "J10", "강원특별자치도교육청": "K10",
    "충청북도교육청": "M10", "충청남도교육청": "N10",
    "전북특별자치도교육청": "P10", "전라남도교육청": "Q10",
    "경상북도교육청": "R10", "경상남도교육청": "S10",
    "제주특별자치도교육청": "T10"
}
office_name = st.selectbox("교육청을 선택하세요", list(offices.keys()))
office_code = offices[office_name]

col1, col2 = st.columns(2)
with col1:
    school_name = st.text_input("학교 이름을 입력하세요")
with col2:
    date = st.date_input("날짜를 선택하세요")

if st.button("급식 조회하기"):
    school_code = find_school(office_code, school_name)

    with st.spinner("급식 정보를 불러오는 중..."):
        date_str = date.strftime("%Y%m%d")
        raw_menu = get_meal(office_code, school_code, date_str)

    if raw_menu:
        st.success(f"{school_name} 급식을 불러왔습니다.")
        st.balloons()

        menu = clean_menu(raw_menu)
        st.write(f"### {school_name} {date_str} 급식")
        for dish in menu:
            st.write(f"- {dish}")

        with st.expander("학교 정보 더보기"):
            st.write(f"교육청: {office_name} ({office_code})")
            st.write(f"학교 코드: {school_code}")
    else:
        st.error("급식 정보를 찾을 수 없습니다. 날짜나 학교 이름을 다시 확인해주세요.")