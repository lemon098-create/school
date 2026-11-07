
import streamlit as st
import requests
import pandas as pd
import folium
import html

from folium.plugins import Fullscreen
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from statistics import median


# ==========================================
# 1. 기본 설정
# ==========================================

st.set_page_config(
    page_title="우리 동네 안전지도",
    page_icon="🗺️",
    layout="wide"
)

st.title("🗺️ 우리 동네 안전지도")
st.caption("카카오 장소 검색 API를 활용한 지역 안전시설 지도")


# ==========================================
# 2. API 키 설정
# ==========================================

try:
    KAKAO_API_KEY = st.secrets["KAKAO_REST_API_KEY"]
except Exception:
    KAKAO_API_KEY = ""

if not KAKAO_API_KEY:
    st.error(
        "카카오 API 키를 찾을 수 없습니다.\n\n"
        ".streamlit/secrets.toml 파일을 확인해 주세요."
    )
    st.stop()


# ==========================================
# 3. 검색 설정
# ==========================================

API_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"

HEADERS = {
    "Authorization": f"KakaoAK {KAKAO_API_KEY}"
}

SEARCH_KEYWORDS = {
    "경찰": [
        "경찰서",
        "지구대",
        "파출소"
    ],
    "소방": [
        "소방서",
        "119안전센터"
    ],
    "병원": [
        "병원",
        "종합병원",
        "대학병원",
        "의료원"
    ]
}

COLORS = {
    "경찰": "blue",
    "소방": "red",
    "병원": "green"
}

ICONS = {
    "경찰": "shield",
    "소방": "fire-extinguisher",
    "병원": "plus"
}


# ==========================================
# 4. 카카오 장소 검색 함수
# ==========================================

def search_kakao(query, category=None):
    """
    카카오 키워드 검색 API를 이용해 장소 검색
    한 검색어당 최대 45개 결과 조회
    """

    results = []

    for page in range(1, 4):

        params = {
            "query": query,
            "page": page,
            "size": 15,
            "sort": "accuracy"
        }

        if category:
            params["category_group_code"] = category

        try:
            response = requests.get(
                API_URL,
                headers=HEADERS,
                params=params,
                timeout=15
            )

            if response.status_code != 200:
                try:
                    error_info = response.json()
                except Exception:
                    error_info = response.text

                raise Exception(
                    f"HTTP {response.status_code}: {error_info}"
                )

            data = response.json()

            results.extend(data.get("documents", []))

            if data.get("meta", {}).get("is_end", True):
                break

        except requests.exceptions.Timeout:
            raise Exception("카카오 API 요청 시간이 초과되었습니다.")

        except requests.exceptions.RequestException as e:
            raise Exception(f"API 통신 오류: {e}")

    return results


# ==========================================
# 5. 검색 결과 정리
# ==========================================

def clean_results(results, area):
    """
    중복 장소 제거 및 선택한 지역의 결과만 유지
    """

    cleaned = []
    seen_ids = set()

    # 시·군·구가 입력된 경우 마지막 행정구역 이름으로 필터링
    area_parts = area.strip().split()

    district = None

    if len(area_parts) >= 2:
        district = area_parts[-1]

    for item in results:

        place_id = item.get("id")

        if not place_id or place_id in seen_ids:
            continue

        address = (
            item.get("road_address_name")
            or item.get("address_name")
            or ""
        )

        # 시·군·구가 입력되었으면 주소 확인
        if district and district not in address:
            continue

        try:
            longitude = float(item["x"])
            latitude = float(item["y"])
        except (ValueError, TypeError, KeyError):
            continue

        if not (-90 <= latitude <= 90):
            continue

        if not (-180 <= longitude <= 180):
            continue

        seen_ids.add(place_id)

        cleaned.append({
            "시설명": item.get("place_name", ""),
            "종류": item.get("_type", ""),
            "주소": address,
            "전화번호": item.get("phone", ""),
            "위도": latitude,
            "경도": longitude,
            "카카오맵": item.get("place_url", ""),
            "카테고리": item.get("category_name", "")
        })

    return cleaned


# ==========================================
# 6. 시설 검색 실행
# ==========================================

def search_all_facilities(area, selected_types):

    all_results = []

    progress = st.progress(0)
    status = st.empty()

    search_tasks = []

    for facility_type in selected_types:
        for keyword in SEARCH_KEYWORDS[facility_type]:
            search_tasks.append((facility_type, keyword))

    total_tasks = len(search_tasks)

    for index, (facility_type, keyword) in enumerate(search_tasks):

        status.write(
            f"🔎 {facility_type} - {keyword} 검색 중..."
        )

        query = f"{area} {keyword}"

        # 병원은 카카오 병원 카테고리(HP8)로 제한
        category = "HP8" if facility_type == "병원" else None

        try:
            results = search_kakao(
                query,
                category=category
            )

            for item in results:
                item["_type"] = facility_type

            all_results.extend(results)

        except Exception as e:
            st.warning(
                f"{keyword} 검색 중 오류가 발생했습니다: {e}"
            )

        progress.progress((index + 1) / total_tasks)

    status.success("검색이 완료되었습니다.")

    return clean_results(all_results, area)


# ==========================================
# 7. 사이드바
# ==========================================

st.sidebar.title("🔍 안전지도 검색")

area = st.sidebar.text_input(
    "검색할 지역",
    value="서울특별시 강남구",
    help="예: 서울특별시 강남구, 경기도 수원시 영통구"
)

st.sidebar.markdown("---")

st.sidebar.subheader("시설 종류")

selected_types = []

for facility_type in ["경찰", "소방", "병원"]:

    checked = st.sidebar.checkbox(
        facility_type,
        value=True
    )

    if checked:
        selected_types.append(facility_type)

st.sidebar.markdown("---")

search_button = st.sidebar.button(
    "🔎 시설 검색하기",
    use_container_width=True,
    type="primary"
)


# ==========================================
# 8. 검색 실행
# ==========================================

if "search_results" not in st.session_state:
    st.session_state.search_results = []

if "searched_area" not in st.session_state:
    st.session_state.searched_area = ""

if search_button:

    if not area.strip():
        st.error("검색할 지역을 입력해 주세요.")

    elif not selected_types:
        st.warning("검색할 시설 종류를 하나 이상 선택해 주세요.")

    else:

        with st.spinner("카카오 API에서 시설 정보를 가져오는 중입니다..."):

            try:
                results = search_all_facilities(
                    area.strip(),
                    selected_types
                )

                st.session_state.search_results = results
                st.session_state.searched_area = area.strip()

            except Exception as e:
                st.error(f"검색 오류: {e}")


# ==========================================
# 9. 검색 결과 표시
# ==========================================

results = st.session_state.search_results

if results:

    st.subheader(
        f"📍 {st.session_state.searched_area} 검색 결과"
    )

    df = pd.DataFrame(results)

    police_count = len(df[df["종류"] == "경찰"])
    fire_count = len(df[df["종류"] == "소방"])
    hospital_count = len(df[df["종류"] == "병원"])

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("전체 시설", f"{len(df):,}개")
    col2.metric("경찰", f"{police_count:,}개")
    col3.metric("소방", f"{fire_count:,}개")
    col4.metric("병원", f"{hospital_count:,}개")

    st.markdown("---")

    # ======================================
    # 10. 지도 생성
    # ======================================

    center_lat = median(df["위도"].tolist())
    center_lon = median(df["경도"].tolist())

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=13,
        tiles="OpenStreetMap"
    )

    Fullscreen(
        position="topright"
    ).add_to(m)

    marker_cluster = MarkerCluster().add_to(m)

    for _, row in df.iterrows():

        facility_type = row["종류"]

        name = html.escape(str(row["시설명"]))
        address = html.escape(str(row["주소"]))
        phone = html.escape(str(row["전화번호"]))
        category = html.escape(str(row["카테고리"]))
        kakao_url = html.escape(str(row["카카오맵"]), quote=True)

        popup_html = f"""
        <div style="width:240px; font-size:13px;">
            <h4 style="margin-bottom:8px;">{name}</h4>
            <b>종류:</b> {facility_type}<br>
            <b>분류:</b> {category}<br>
            <b>주소:</b> {address}<br>
            <b>전화:</b> {phone}<br>
            <br>
            <a href="{kakao_url}" target="_blank">
                카카오맵에서 보기
            </a>
        </div>
        """

        folium.Marker(
            location=[
                row["위도"],
                row["경도"]
            ],
            popup=folium.Popup(
                popup_html,
                max_width=300
            ),
            tooltip=name,
            icon=folium.Icon(
                color=COLORS[facility_type],
                icon=ICONS[facility_type],
                prefix="fa"
            )
        ).add_to(marker_cluster)

    st.subheader("🗺️ 시설 위치 지도")

    st_folium(
        m,
        width=None,
        height=650,
        use_container_width=True,
        key="safety_map"
    )

    # ======================================
    # 11. 시설 목록
    # ======================================

    st.markdown("---")
    st.subheader("📋 시설 목록")

    filter_type = st.selectbox(
        "시설 종류별 보기",
        ["전체", "경찰", "소방", "병원"]
    )

    if filter_type == "전체":
        display_df = df.copy()
    else:
        display_df = df[
            df["종류"] == filter_type
        ].copy()

    display_df = display_df.rename(
        columns={
            "시설명": "시설 이름",
            "종류": "시설 종류",
            "주소": "주소",
            "전화번호": "전화번호",
            "카테고리": "카테고리"
        }
    )

    st.dataframe(
        display_df[
            [
                "시설 이름",
                "시설 종류",
                "주소",
                "전화번호",
                "카테고리"
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

    st.caption(
        "※ 검색 결과는 카카오 장소 검색 API에서 제공하는 정보입니다. "
        "실제 시설 전체 목록과 일치하지 않을 수 있습니다."
    )

elif st.session_state.searched_area:

    st.warning(
        "검색 결과가 없습니다. 지역 이름이나 검색 조건을 확인해 주세요."
    )

else:

    st.info(
        "👈 왼쪽 사이드바에서 지역을 입력하고 "
        "'시설 검색하기'를 눌러 주세요."
    )

    st.markdown("### 이용 방법")

    st.write(
        "1. 검색할 시·군·구를 입력합니다."
    )

    st.write(
        "2. 경찰, 소방, 병원 중 검색할 시설을 선택합니다."
    )

    st.write(
        "3. 검색 버튼을 누르면 카카오 API에서 장소 정보를 가져옵니다."
    )

    st.write(
        "4. 지도에서 시설 위치와 상세정보를 확인할 수 있습니다."
    )

