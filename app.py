import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
from utils.astronomy import AstronomyEngine


KST = ZoneInfo("Asia/Seoul")
BASE_DIR = Path(__file__).resolve().parent
MESSIER_PATH = BASE_DIR / "data" / "messier.json"


st.set_page_config(
    page_title="천체관측 도우미",
    page_icon="🌌",
    layout="wide",
)

# ==========================================
# 모바일 Pull-to-Refresh
# ==========================================

components.html(
    """
    <script>
    const win = window.parent;
    const doc = win.document;
    if ("scrollRestoration" in win.history) {
        win.history.scrollRestoration = "manual";
    }
    if (win.__astroPullRefreshController) {
        win.__astroPullRefreshController.destroy();
    }

    const REFRESH_DISTANCE = 260;
    const MAX_PULL = 95;

    let startY = 0;
    let startX = 0;

    let pullDistance = 0;
    let visualPull = 0;

    let canPull = false;
    let refreshing = false;

    let touchTarget = null;


    // =====================================
    // 이전 표시 제거
    // =====================================

    const oldIndicator =
        doc.getElementById(
            "astro-pull-refresh"
        );

    if (oldIndicator) {
        oldIndicator.remove();
    }

    const oldStyle =
        doc.getElementById(
            "astro-pull-refresh-style"
        );

    if (oldStyle) {
        oldStyle.remove();
    }


    // =====================================
    // 스타일
    // =====================================

    const style =
        doc.createElement("style");

    style.id =
        "astro-pull-refresh-style";

    style.textContent = `
        html,
        body {
            overscroll-behavior-y: none !important;
        }

        #astro-pull-refresh {
            position: fixed;

            top: 8px;
            left: 50%;

            z-index: 999999;

            display: flex;
            align-items: center;

            gap: 8px;

            padding: 8px 13px;

            border-radius: 22px;

            background:
                rgba(30, 30, 30, 0.86);

            color: white;

            font-size: 13px;
            font-weight: 600;

            box-shadow:
                0 3px 12px
                rgba(0, 0, 0, 0.22);

            opacity: 0;

            transform:
                translate(-50%, -45px)
                scale(0.9);

            transition:
                opacity 0.18s ease,
                transform 0.18s ease;

            pointer-events: none;
        }

        #astro-pull-refresh.visible {
            opacity: 1;
        }

        #astro-pull-refresh .spinner {
            width: 17px;
            height: 17px;

            border: 2px solid
                rgba(255, 255, 255, 0.35);

            border-top-color: white;

            border-radius: 50%;
        }

        #astro-pull-refresh.refreshing .spinner {
            animation:
                astro-spin
                0.75s
                linear
                infinite;
        }

        @keyframes astro-spin {

            from {
                transform: rotate(0deg);
            }

            to {
                transform: rotate(360deg);
            }
        }

        [data-testid="stAppViewContainer"] {
            will-change: transform;
        }
    `;

    doc.head.appendChild(style);


    // =====================================
    // 새로고침 표시
    // =====================================

    const indicator =
        doc.createElement("div");

    indicator.id =
        "astro-pull-refresh";

    indicator.innerHTML = `
        <div class="spinner"></div>

        <span class="refresh-text">
            아래로 당기세요
        </span>
    `;

    doc.body.appendChild(
        indicator
    );


    const refreshText =
        indicator.querySelector(
            ".refresh-text"
        );


    // =====================================
    // 실제 스크롤 위치 찾기
    // =====================================

    function getRealScrollTop(target) {

        const scrollValues = [
            win.scrollY || 0,

            doc.documentElement
                ? doc.documentElement.scrollTop
                : 0,

            doc.body
                ? doc.body.scrollTop
                : 0,

            doc.scrollingElement
                ? doc.scrollingElement.scrollTop
                : 0
        ];


        const selectors = [
            '[data-testid="stAppViewContainer"]',
            '[data-testid="stMain"]',
            'section.main',
            '.main'
        ];


        selectors.forEach(
            function(selector) {

                const elements =
                    doc.querySelectorAll(
                        selector
                    );

                elements.forEach(
                    function(element) {

                        scrollValues.push(
                            element.scrollTop || 0
                        );
                    }
                );
            }
        );


        // 터치한 위치의 부모 요소 중
        // 실제로 스크롤되는 요소도 검사
        let element = target;

        while (
            element
            && element !== doc.body
        ) {

            if (
                element.scrollHeight
                > element.clientHeight + 5
            ) {

                scrollValues.push(
                    element.scrollTop || 0
                );
            }

            element =
                element.parentElement;
        }


        return Math.max(
            ...scrollValues
        );
    }


    function getAppContainer() {

        return doc.querySelector(
            '[data-testid="stAppViewContainer"]'
        );
    }

    function forceScrollTop() {

        win.scrollTo(
            0,
            0
        );

        if (doc.documentElement) {
            doc.documentElement.scrollTop = 0;
        }

        if (doc.body) {
            doc.body.scrollTop = 0;
        }

        if (doc.scrollingElement) {
            doc.scrollingElement.scrollTop = 0;
        }

        const selectors = [
            '[data-testid="stAppViewContainer"]',
            '[data-testid="stMain"]',
            'section.main',
            '.main'
        ];

        selectors.forEach(
            function(selector) {

                const elements =
                    doc.querySelectorAll(
                        selector
                    );

                elements.forEach(
                    function(element) {
                        element.scrollTop = 0;
                    }
                );
            }
        );
    }


    // 새로고침 후에는 무조건 앱 맨 위에서 시작
    if (
        win.sessionStorage.getItem(
            "astroForceScrollTop"
        ) === "1"
    ) {

        win.sessionStorage.removeItem(
            "astroForceScrollTop"
        );

        forceScrollTop();

        setTimeout(
            forceScrollTop,
            100
        );

        setTimeout(
            forceScrollTop,
            400
        );

        setTimeout(
            forceScrollTop,
            1000
        );
    }
    
    // =====================================
    // 화면 원위치
    // =====================================

    function resetPull() {

        const app =
            getAppContainer();

        if (app) {

            app.style.transition =
                "transform 0.30s ease";

            app.style.transform =
                "translateY(0px)";
        }


        indicator.style.transition =
            "opacity 0.22s ease, "
            + "transform 0.30s ease";


        indicator.style.transform =
            "translate(-50%, -45px) "
            + "scale(0.9)";


        indicator.classList.remove(
            "visible"
        );

        indicator.classList.remove(
            "refreshing"
        );


        setTimeout(
            function() {

                if (app) {
                    app.style.transition = "";
                }

                indicator.style.transition = "";

            },
            330
        );


        pullDistance = 0;
        visualPull = 0;

        canPull = false;
        touchTarget = null;
    }


    // =====================================
    // 손가락 터치 시작
    // =====================================

    function touchStart(event) {

        if (refreshing) {
            return;
        }


        touchTarget =
            event.target;


        const currentScroll =
            getRealScrollTop(
                touchTarget
            );


        // 반드시 실제 페이지 최상단이어야 함
        if (currentScroll <= 2) {

            startY =
                event.touches[0].clientY;

            startX =
                event.touches[0].clientX;

            pullDistance = 0;
            visualPull = 0;

            canPull = true;

        } else {

            canPull = false;
        }
    }


    // =====================================
    // 아래로 당기는 동안
    // =====================================

    function touchMove(event) {

        if (
            !canPull
            || refreshing
        ) {
            return;
        }


        // 이동 도중에도
        // 정말 최상단인지 다시 확인
        if (
            getRealScrollTop(
                touchTarget
            ) > 2
        ) {

            canPull = false;
            resetPull();

            return;
        }


        const currentY =
            event.touches[0].clientY;

        const currentX =
            event.touches[0].clientX;


        const moveY =
            currentY - startY;

        const moveX =
            Math.abs(
                currentX - startX
            );


        // 위로 스와이프하거나
        // 옆으로 스와이프하면 새로고침 취소
        if (
            moveY <= 0
            || moveY <= moveX
        ) {

            return;
        }


        if (event.cancelable) {
            event.preventDefault();
        }


        pullDistance =
            moveY;


        visualPull =
            Math.min(
                MAX_PULL,
                moveY * 0.30
            );


        const app =
            getAppContainer();


        if (app) {

            app.style.transition =
                "none";

            app.style.transform =
                `translateY(${visualPull}px)`;
        }


        indicator.classList.add(
            "visible"
        );


        const indicatorY =
            Math.min(
                58,
                visualPull - 35
            );


        indicator.style.transform =
            `translate(-50%, ${indicatorY}px) `
            + "scale(1)";


        const spinner =
            indicator.querySelector(
                ".spinner"
            );


        const rotation =
            Math.min(
                300,
                pullDistance
            );


        spinner.style.transform =
            `rotate(${rotation}deg)`;


        if (
            pullDistance
            >= REFRESH_DISTANCE
        ) {

            refreshText.textContent =
                "놓아서 새로고침";

        } else {

            refreshText.textContent =
                "아래로 더 당기세요";
        }
    }


    // =====================================
    // 손가락을 놓음
    // =====================================

    function touchEnd() {

        if (
            !canPull
            || refreshing
        ) {
            return;
        }


        // 손을 놓는 순간에도
        // 최상단 여부 마지막 확인
        const currentScroll =
            getRealScrollTop(
                touchTarget
            );


        if (
            pullDistance
            >= REFRESH_DISTANCE
            && currentScroll <= 2
        ) {

            refreshing = true;


            const app =
                getAppContainer();


            refreshText.textContent =
                "새로고침 중...";


            indicator.classList.add(
                "refreshing"
            );

            indicator.classList.add(
                "visible"
            );


            indicator.style.transform =
                "translate(-50%, 18px) "
                + "scale(1)";


            if (app) {

                app.style.transition =
                    "transform 0.3s ease";

                app.style.transform =
                    "translateY(58px)";
            }


                  setTimeout(
                function() {

                    win.sessionStorage.setItem(
                        "astroForceScrollTop",
                        "1"
                    );

                    forceScrollTop();

                    setTimeout(
                        function() {
                            win.location.reload();
                        },
                        80
                    );

                },
                550
            );

        } else {

            resetPull();
        }
    }


    // =====================================
    // 이벤트
    // =====================================

    doc.addEventListener(
        "touchstart",
        touchStart,
        {
            passive: true
        }
    );


    doc.addEventListener(
        "touchmove",
        touchMove,
        {
            passive: false
        }
    );


    doc.addEventListener(
        "touchend",
        touchEnd,
        {
            passive: true
        }
    );


    // =====================================
    // Streamlit 재실행 시
    // 중복 이벤트 방지
    // =====================================

    win.__astroPullRefreshController = {

        destroy: function() {

            doc.removeEventListener(
                "touchstart",
                touchStart
            );

            doc.removeEventListener(
                "touchmove",
                touchMove
            );

            doc.removeEventListener(
                "touchend",
                touchEnd
            );


            const indicator =
                doc.getElementById(
                    "astro-pull-refresh"
                );

            if (indicator) {
                indicator.remove();
            }


            const style =
                doc.getElementById(
                    "astro-pull-refresh-style"
                );

            if (style) {
                style.remove();
            }
        }
    };

    </script>
    """,
    height=0
)

# ==========================================
# 모바일 화면 글씨 크기 최적화
# ==========================================

st.markdown(
    """
    <style>

    @media (max-width: 768px) {

        /* 전체 페이지 좌우 여백 */
        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
            padding-top: 1.5rem;
        }

        /* 가장 큰 제목 */
        h1 {
            font-size: 2rem !important;
            line-height: 1.25 !important;
        }

        /* 섹션 제목 */
        h2 {
            font-size: 1.65rem !important;
            line-height: 1.3 !important;
            margin-top: 1.5rem !important;
            margin-bottom: 0.8rem !important;
        }

        /* 소제목 */
        h3 {
            font-size: 1.35rem !important;
            line-height: 1.3 !important;
        }

        /* 일반 글씨 */
        p,
        li {
            font-size: 0.95rem;
        }

        /* 일반 화면 글자 선택 / 복사 메뉴 방지 */
        .stApp h1,
        .stApp h2,
        .stApp h3,
        .stApp p,
        .stApp span,
        .stApp label,
        .weekly-card,
        .weather-mini-card {
            -webkit-user-select: none !important;
            user-select: none !important;
            -webkit-touch-callout: none !important;
        }

        /* 검색창 등 입력칸은 정상적으로 선택 가능 */
        input,
        textarea,
        [contenteditable="true"] {
            -webkit-user-select: text !important;
            user-select: text !important;
            -webkit-touch-callout: default !important;
        }        

        /* metric 이름 */
        [data-testid="stMetricLabel"] {
            font-size: 0.9rem !important;
        }

        /* metric 숫자 */
        [data-testid="stMetricValue"] {
            font-size: 2rem !important;
        }

        /* 카드 날짜 */
        .weekly-card-date {
            font-size: 16px !important;
        }

        /* 카드 등급 */
        .weekly-card-grade {
            font-size: 17px !important;
        }

        /* 카드 점수 */
        .weekly-card-score {
            font-size: 26px !important;
        }

        /* 카드 상세 정보 */
        .weekly-card-info {
            font-size: 14px !important;
            line-height: 1.65 !important;
        }

    }

    </style>
    """,
    unsafe_allow_html=True
)


st.title("🌌 AAA 날씨 확인")
st.write("AAA를 위한 관측 지원 앱입니다.")
st.divider()

# ==========================================
# 장소 이름 → 위도 / 경도 검색
# ==========================================

@st.cache_data(ttl=3600)
def search_location(search_text):

    url = "https://nominatim.openstreetmap.org/search"

    headers = {
        "User-Agent": "AstroObservationClubApp/1.0"
    }

    search_text = search_text.strip()

    search_candidates = [
        search_text,
        f"{search_text}시",
        f"{search_text}군",
        f"{search_text}읍"
    ]

    allowed_types = {
        "city",
        "county",
        "town",
        "village",
        "municipality"
    }

    final_results = []
    seen = set()

    for candidate in search_candidates:

        params = {
            "q": f"{candidate}, 대한민국",
            "format": "jsonv2",
            "countrycodes": "kr",
            "limit": 10,
            "addressdetails": 1,
            "accept-language": "ko"
        }

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=10
        )

        response.raise_for_status()

        results = response.json()

        for result in results:

            address_type = result.get(
                "addresstype",
                ""
            )

            if address_type not in allowed_types:
                continue

            lat = result.get("lat")
            lon = result.get("lon")

            key = (
                result.get("display_name", ""),
                lat,
                lon
            )

            if key not in seen:
                seen.add(key)
                final_results.append(result)

    return final_results
# ==========================================
# 관측지 설정
# ==========================================

st.sidebar.header("📍 관측지 설정")


# ==========================================
# 처음 실행할 때 기본 위치
# ==========================================

if "applied_latitude" not in st.session_state:
    st.session_state["applied_latitude"] = 36.5684

if "applied_longitude" not in st.session_state:
    st.session_state["applied_longitude"] = 128.7294

if "applied_location_name" not in st.session_state:
    st.session_state["applied_location_name"] = "안동"

if "location_results" not in st.session_state:
    st.session_state["location_results"] = []


# ==========================================
# 장소 검색
# Enter 키로도 검색 가능
# ==========================================

with st.sidebar.form(
    "location_search_form"
):

    search_text = st.text_input(
        "🔎 장소 검색",
        placeholder="예: 용인, 안동, 소백산"
    )

    search_pressed = st.form_submit_button(
        "검색",
        use_container_width=True
    )


# Enter 또는 검색 버튼
if search_pressed:

    if search_text.strip():

        try:

            results = search_location(
                search_text.strip()
            )

            if len(results) == 0:

                st.sidebar.warning(
                    "검색 결과가 없습니다."
                )

            else:

                selected = results[0]

                address = selected.get(
                    "address",
                    {}
                )

                selected_lat = float(
                    selected["lat"]
                )

                selected_lon = float(
                    selected["lon"]
                )

                selected_name = (
                    selected.get("name")
                    or address.get("city")
                    or address.get("town")
                    or address.get("county")
                    or "선택한 위치"
                )

                st.session_state[
                    "applied_latitude"
                ] = selected_lat

                st.session_state[
                    "applied_longitude"
                ] = selected_lon

                st.session_state[
                    "applied_location_name"
                ] = selected_name

                st.session_state[
                    "location_results"
                ] = []

                st.rerun()

        except Exception as e:

            st.sidebar.error(
                "장소 검색 중 오류가 발생했습니다."
            )

            st.sidebar.code(
                str(e)
            )

    else:

        st.sidebar.warning(
            "검색할 장소를 입력해주세요."
        )


# ==========================================
# 검색 결과
# ==========================================

results = st.session_state[
    "location_results"
]


if len(results) > 0:

    result_labels = []


    for result in results:

        address = result.get(
            "address",
            {}
        )

        name = result.get(
            "name",
            ""
        )

        city = (
            address.get("city")
            or address.get("town")
            or address.get("municipality")
            or address.get("county")
            or ""
        )

        province = (
            address.get("state")
            or address.get("province")
            or ""
        )

        lat = float(
            result["lat"]
        )

        lon = float(
            result["lon"]
        )


        # 중복 이름 제거
        parts = []

        for part in [
            name,
            city,
            province
        ]:

            if (
                part
                and part not in parts
            ):
                parts.append(part)


        short_name = " / ".join(
            parts
        )


        # 검색 결과를 너무 길지 않게 표시
        label = (
            f"{short_name} "
            f"({lat:.4f}, {lon:.4f})"
        )

        result_labels.append(
            label
        )


    selected_index = st.sidebar.selectbox(
        "검색 결과",
        options=range(
            len(result_labels)
        ),
        format_func=lambda i: result_labels[i]
    )


    if st.sidebar.button(
        "📍 이 위치 사용",
        use_container_width=True
    ):

        selected = results[
            selected_index
        ]

        address = selected.get(
            "address",
            {}
        )


        selected_lat = float(
            selected["lat"]
        )

        selected_lon = float(
            selected["lon"]
        )


        selected_name = (
            selected.get("name")
            or address.get("city")
            or address.get("town")
            or address.get("county")
            or "선택한 위치"
        )


        # 실제 앱에서 사용할 위치 변경
        st.session_state[
            "applied_latitude"
        ] = selected_lat

        st.session_state[
            "applied_longitude"
        ] = selected_lon

        st.session_state[
            "applied_location_name"
        ] = selected_name


        # 검색 결과 닫기
        st.session_state[
            "location_results"
        ] = []


        st.rerun()


# ==========================================
# 실제 앱에서 사용할 현재 위치
# ==========================================

latitude = float(
    st.session_state[
        "applied_latitude"
    ]
)

longitude = float(
    st.session_state[
        "applied_longitude"
    ]
)

location_name = (
    st.session_state[
        "applied_location_name"
    ]
)


# ==========================================
# 현재 적용된 관측지 표시
# ==========================================

st.sidebar.divider()

st.sidebar.subheader(
    "📌 현재 적용된 관측지"
)

st.sidebar.success(
    location_name
)

st.sidebar.write(
    f"위도: **{latitude:.4f}°**"
)

st.sidebar.write(
    f"경도: **{longitude:.4f}°**"
)



# ==========================================
# 날씨 API
# ==========================================

@st.cache_data(ttl=600)
def get_weather(latitude, longitude):

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": "Asia/Seoul",
        "forecast_days": 8,

        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "cloud_cover,"
            "precipitation,"
            "wind_speed_10m,"
            "visibility"
        ),

        "hourly": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "cloud_cover,"
            "cloud_cover_low,"
            "cloud_cover_mid,"
            "cloud_cover_high,"
            "precipitation_probability,"
            "precipitation,"
            "wind_speed_10m,"
            "visibility"
        ),

        "daily": (
            "sunrise,"
            "sunset,"
            "temperature_2m_max,"
            "temperature_2m_min,"
            "precipitation_probability_max"
        )
    }

    response = requests.get(
        url,
        params=params,
        timeout=10
    )

    response.raise_for_status()

    return response.json()

@st.cache_data(ttl=600)
def get_gfs_weather(latitude, longitude):

    url = "https://api.open-meteo.com/v1/gfs"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": "Asia/Seoul",
        "forecast_days": 8,

        "hourly": (
            "cloud_cover,"
            "cloud_cover_low,"
            "cloud_cover_mid,"
            "cloud_cover_high,"
            "precipitation,"
            "visibility,"
            "wind_speed_10m"
        )
    }

    response = requests.get(
        url,
        params=params,
        timeout=10
    )

    response.raise_for_status()

    return response.json()

@st.cache_data(ttl=600)
def get_ecmwf_weather(latitude, longitude):

    url = "https://api.open-meteo.com/v1/ecmwf"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": "Asia/Seoul",
        "forecast_days": 8,

        "hourly": (
            "cloud_cover,"
            "cloud_cover_low,"
            "cloud_cover_mid,"
            "cloud_cover_high,"
            "precipitation,"
            "visibility,"
            "wind_speed_10m"
        )
    }

    response = requests.get(
        url,
        params=params,
        timeout=10
    )

    response.raise_for_status()

    return response.json()

def build_ecmwf_cloud_forecast(ecmwf_weather, engine):

    hourly = ecmwf_weather["hourly"]

    df = pd.DataFrame({
        "시간": pd.to_datetime(hourly["time"]),
        "전체구름": hourly["cloud_cover"],
        "하층구름": hourly["cloud_cover_low"],
        "중층구름": hourly["cloud_cover_mid"],
        "상층구름": hourly["cloud_cover_high"]
    })

    rows = []

    dates = sorted(
        df["시간"].dt.strftime("%Y-%m-%d").unique()
    )

    for date in dates[:7]:

        astro_start, astro_end = (
            engine.get_astronomical_night(date)
        )

        if astro_start is None or astro_end is None:
            continue
        # ==================================
        # 해당 밤 중간 시각의 달 상태
        # ==================================

       
        astro_start = astro_start.replace(
            tzinfo=None
        )

        astro_end = astro_end.replace(
            tzinfo=None
        )

        night = df[
            (df["시간"] >= astro_start)
            &
            (df["시간"] <= astro_end)
        ].copy()

        if len(night) == 0:
            continue

        night["유효구름량"] = night.apply(
            lambda row: max(
                row["전체구름"],
                row["하층구름"],
                row["중층구름"] * 0.95,
                row["상층구름"] * 0.85
            ),
            axis=1
        )

        rows.append({
            "날짜": date,
            "ECMWF 평균 구름 %":
                round(night["유효구름량"].mean()),
            "ECMWF 전체 구름 %":
                round(night["전체구름"].mean()),
            "ECMWF 하층 구름 %":
                round(night["하층구름"].mean()),
            "ECMWF 중층 구름 %":
                round(night["중층구름"].mean()),
            "ECMWF 상층 구름 %":
                round(night["상층구름"].mean())
        })

    return pd.DataFrame(rows)

def build_gfs_cloud_forecast(gfs_weather, engine):

    hourly = gfs_weather["hourly"]

    hourly_df = pd.DataFrame({
        "시간": pd.to_datetime(hourly["time"]),
        "전체구름": hourly["cloud_cover"],
        "하층구름": hourly["cloud_cover_low"],
        "중층구름": hourly["cloud_cover_mid"],
        "상층구름": hourly["cloud_cover_high"]
    })

    rows = []

    start_date = hourly_df["시간"].dt.date.min()

    for day_offset in range(7):

        date = start_date + timedelta(days=day_offset)

        astro = engine.get_astronomical_night(
            date.strftime("%Y-%m-%d")
        )

        astro_start = astro[0]
        astro_end = astro[1]

        if astro_start is None or astro_end is None:
            continue

        astro_start_naive = astro_start.replace(
            tzinfo=None
        )

        astro_end_naive = astro_end.replace(
            tzinfo=None
        )

        night = hourly_df[
            (hourly_df["시간"] >= astro_start_naive)
            &
            (hourly_df["시간"] <= astro_end_naive)
        ].copy()

        if len(night) == 0:
            continue

        night["유효구름량"] = night.apply(
            lambda row: max(
                row["전체구름"],
                row["하층구름"],
                row["중층구름"] * 0.95,
                row["상층구름"] * 0.85
            ),
            axis=1
        )

        rows.append({
            "날짜": date.strftime("%Y-%m-%d"),

            "GFS 평균 구름 %": round(
                night["유효구름량"].mean()
            ),

            "GFS 전체 구름 %": round(
                night["전체구름"].mean()
            ),

            "GFS 하층 구름 %": round(
                night["하층구름"].mean()
            ),

            "GFS 중층 구름 %": round(
                night["중층구름"].mean()
            ),

            "GFS 상층 구름 %": round(
                night["상층구름"].mean()
            )
        })

    return pd.DataFrame(rows)

@st.cache_data
def load_messier_catalog():
    with open(MESSIER_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ==========================================
# 관측 날씨 점수
# ==========================================

def calculate_observation_score(
    cloud,
    precipitation_probability,
    visibility,
    wind_speed,
    humidity,
):
    cloud_score = max(0, 100 - cloud)
    rain_score = max(0, 100 - precipitation_probability)

    visibility_km = visibility / 1000
    visibility_score = min(100, (visibility_km / 20) * 100)

    if wind_speed <= 10:
        wind_score = 100
    else:
        wind_score = max(0, 100 - ((wind_speed - 10) * 4))

    if humidity <= 70:
        humidity_score = 100
    else:
        humidity_score = max(0, 100 - ((humidity - 70) * 3.3))

    final_score = (
        cloud_score * 0.45
        + rain_score * 0.25
        + visibility_score * 0.15
        + wind_score * 0.10
        + humidity_score * 0.05
    )

    return round(final_score)


def weather_score_grade(score):

    if score >= 90:
        return "🔵 매우 좋음"

    elif score >= 80:
        return "🟢 좋음"

    elif score >= 65:
        return "🟡 보통"

    elif score >= 45:
        return "🟠 좋지 않음"

    else:
        return "🔴 관측 비추천"

def model_agreement(model_difference):

    if pd.isna(model_difference):
        return "⚪ 판단 불가"

    if model_difference <= 10:
        return "🟢 높음"

    elif model_difference <= 25:
        return "🟡 보통"

    else:
        return "🔴 낮음"

def consensus_cloud_score(avg_cloud):

    if pd.isna(avg_cloud):
        return 50

    if avg_cloud <= 10:
        score = 100

    elif avg_cloud <= 25:
        score = 100 - (avg_cloud - 10) * 1.33

    elif avg_cloud <= 40:
        score = 80 - (avg_cloud - 25) * 1.33

    elif avg_cloud <= 60:
        score = 60 - (avg_cloud - 40) * 1.25

    elif avg_cloud <= 80:
        score = 35 - (avg_cloud - 60) * 1.25

    else:
        score = 10 - (avg_cloud - 80) * 0.5

    return max(
        0,
        min(100, score)
    )

def moon_observation_penalty(brightness, altitude):

    if pd.isna(brightness) or pd.isna(altitude):
        return 0

    # 달이 지평선 아래면 영향 없음
    if altitude <= 0:
        return 0

    # 달 밝기에 따른 기본 감점
    if brightness < 20:
        base_penalty = 0

    elif brightness < 40:
        base_penalty = 4

    elif brightness < 60:
        base_penalty = 8

    elif brightness < 80:
        base_penalty = 14

    else:
        base_penalty = 20


    # 달 고도에 따른 영향
    if altitude < 15:
        altitude_factor = 0.4

    elif altitude < 30:
        altitude_factor = 0.7

    else:
        altitude_factor = 1.0


    penalty = (
        base_penalty
        * altitude_factor
    )

    return round(penalty, 1)


def moon_penalty_label(penalty):

    if penalty <= 0:
        return "🟢 거의 없음"

    elif penalty <= 4:
        return "🟢 낮음"

    elif penalty <= 9:
        return "🟡 보통"

    elif penalty <= 15:
        return "🟠 높음"

    else:
        return "🔴 매우 높음"

def cloud_observation_score(total, low, mid, high):

    effective_cloud = max(
        total,
        low,
        mid * 0.95,
        high * 0.85
    )

    if effective_cloud <= 10:
        score = 100

    elif effective_cloud <= 25:
        score = 100 - (effective_cloud - 10) * 1.33

    elif effective_cloud <= 40:
        score = 80 - (effective_cloud - 25) * 1.33

    elif effective_cloud <= 60:
        score = 60 - (effective_cloud - 40) * 1.25

    elif effective_cloud <= 80:
        score = 35 - (effective_cloud - 60) * 1.25

    else:
        score = 10 - (effective_cloud - 80) * 0.5

    return max(0, min(100, score))


def hourly_weather_score(row):

    cloud_score = cloud_observation_score(
        row["전체구름"],
        row["하층구름"],
        row["중층구름"],
        row["상층구름"]
    )

    rain_score = max(
        0,
        100 - row["강수확률"] * 1.4
    )

    visibility_km = row["시정"] / 1000

    visibility_score = min(
        100,
        (visibility_km / 20) * 100
    )

    if row["풍속"] <= 10:
        wind_score = 100
    else:
        wind_score = max(
            0,
            100 - (row["풍속"] - 10) * 4
        )

    if row["습도"] <= 70:
        humidity_score = 100
    else:
        humidity_score = max(
            0,
            100 - (row["습도"] - 70) * 3.3
        )

    score = (
        cloud_score * 0.58
        + rain_score * 0.18
        + visibility_score * 0.10
        + wind_score * 0.07
        + humidity_score * 0.07
    )

    if row["강수량"] >= 0.1:
        score = min(score, 35)

    effective_cloud = max(
        row["전체구름"],
        row["하층구름"],
        row["중층구름"] * 0.95,
        row["상층구름"] * 0.85
    )

    if effective_cloud >= 80:
        score = min(score, 30)

    elif effective_cloud >= 60:
        score = min(score, 50)

    return round(
        max(0, min(100, score))
    )

def build_weekly_forecast(weather, engine):

    daily = weather["daily"]
    hourly = weather["hourly"]

    # 시간별 날씨 DataFrame
    hourly_df = pd.DataFrame({
    "시간": pd.to_datetime(hourly["time"]),
    "전체구름": hourly["cloud_cover"],
    "하층구름": hourly["cloud_cover_low"],
    "중층구름": hourly["cloud_cover_mid"],
    "상층구름": hourly["cloud_cover_high"],
    "강수확률": hourly["precipitation_probability"],
    "강수량": hourly["precipitation"],
    "시정": hourly["visibility"],
    "풍속": hourly["wind_speed_10m"],
    "습도": hourly["relative_humidity_2m"]
})

    rows = []

    # 화면에는 7일만 표시
    for i in range(7):

        date = daily["time"][i]

                # ==================================
        # 정확한 천문학적 밤 계산
        #
        # 저녁 천문박명 종료
        # ~
        # 다음날 아침 천문박명 시작
        # ==================================

        astro_start, astro_end = (
            engine.get_astronomical_night(
                date
            )
        )

        if (
            astro_start is None
            or astro_end is None
        ):
            continue

        # ==================================
        # 해당 밤의 중간 시각 달 상태
        # ==================================

        
        # Open-Meteo 시간 데이터는
        # timezone 정보가 없는 KST 시간이므로
        # 비교를 위해 timezone 제거
        astro_start_naive = (
            astro_start.replace(
                tzinfo=None
            )
        )

        astro_end_naive = (
            astro_end.replace(
                tzinfo=None
            )
        )

        night = hourly_df[
            (
                hourly_df["시간"]
                >= astro_start_naive
            )
            &
            (
                hourly_df["시간"]
                <= astro_end_naive
            )
        ].copy()

        if len(night) == 0:
            continue
              # ==================================
        # 유효 구름량
        # ==================================

        night["유효구름량"] = night.apply(
            lambda row: max(
                row["전체구름"],
                row["하층구름"],
                row["중층구름"] * 0.95,
                row["상층구름"] * 0.85
            ),
            axis=1
        )


        # ==================================
        # 시간별 관측 점수
        # ==================================

        night["시간점수"] = night.apply(
            hourly_weather_score,
            axis=1
        )


        # ==================================
        # 밤 전체 점수용 통계
        # ==================================

        average_score = night["시간점수"].mean()

        lower_score = (
            night["시간점수"]
            .quantile(0.25)
        )

        best_score = night["시간점수"].max()


        # 구름 40% 이상인 시간 비율
        cloudy_ratio = (
            night["유효구름량"] >= 40
        ).mean()


        # 구름 70% 이상인 시간 비율
        very_cloudy_ratio = (
            night["유효구름량"] >= 70
        ).mean()


        # 강수확률 30% 이상인 시간 비율
        rainy_ratio = (
            night["강수확률"] >= 30
        ).mean()
        # ==================================
        # 최종 밤 점수
        # ==================================

        score = (
            average_score * 0.65
            + lower_score * 0.25
            + best_score * 0.10
        )

        score -= cloudy_ratio * 15
        score -= very_cloudy_ratio * 20
        score -= rainy_ratio * 10


        # 밤 절반 이상이 흐리면
        # 높은 등급이 나오지 못하게 제한
        if cloudy_ratio >= 0.50:
            score = min(score, 79)

        if very_cloudy_ratio >= 0.50:
            score = min(score, 64)

        if rainy_ratio >= 0.30:
            score = min(score, 59)


        score = round(
            max(0, min(100, score))
        )

        grade = weather_score_grade(
            score
        )
        score = round(score)

        grade = weather_score_grade(
            score
        )

        # --------------------------
        # 그날 밤 가장 좋은 시간
        # --------------------------

        night["시간점수"] = night.apply(
            hourly_weather_score,
            axis=1
        )

        best_index = (
            night["시간점수"].idxmax()
        )

        best_time = night.loc[
            best_index,
            "시간"
        ]

        best_hour_score = night.loc[
            best_index,
            "시간점수"
        ]

        # ==================================
        # 실제 최적 관측 시간의 달 상태
        # ==================================

        moon_info = engine.get_moon_at_time(
            best_time
        )

        moon_brightness = moon_info["밝기"]
        moon_altitude = moon_info["고도"]

        if moon_altitude < 0:
            moon_status = "🌑 지평선 아래"
        else:
            moon_status = "🌙 떠 있음"

        # ==================================
        # 실제 최적 관측 시간의 달 상태
        # ==================================

        moon_info = engine.get_moon_at_time(
            best_time
        )

        moon_brightness = moon_info["밝기"]
        moon_altitude = moon_info["고도"]

        if moon_altitude < 0:
            moon_status = "🌑 지평선 아래"
        else:
            moon_status = "🌙 떠 있음"

        # ==================================
        # 밤 시간 평균값 계산
        # ==================================

        avg_total_cloud = night["전체구름"].mean()
        avg_low_cloud = night["하층구름"].mean()
        avg_mid_cloud = night["중층구름"].mean()
        avg_high_cloud = night["상층구름"].mean()

        avg_effective_cloud = (
            night["유효구름량"].mean()
        )

        avg_rain = night["강수확률"].mean()
        avg_humidity = night["습도"].mean()

        avg_visibility = (
            night["시정"].mean() / 1000
        )

        avg_wind = night["풍속"].mean()

        rows.append({
             
            "날짜":
                date,

            "천문박명 종료":
                astro_start.strftime("%H:%M"),

            "천문박명 시작":
                astro_end.strftime("%H:%M"),

            "관측 점수":
                score,

            "등급":
                grade,
            "달 밝기 %": moon_brightness,
            "달 고도 °": moon_altitude,
            "달 상태": moon_status,
            "최적 시간":
                best_time.strftime("%H:%M"),

            "최고 예상점수":
                round(best_hour_score),

            "평균 구름 %":
                round(avg_effective_cloud),

            "전체 구름 %":
                round(avg_total_cloud),

            "하층 구름 %":
                round(avg_low_cloud),

            "중층 구름 %":
                round(avg_mid_cloud),

            "상층 구름 %":
                round(avg_high_cloud),

            "흐린 시간 비율 %":
                round(cloudy_ratio * 100),

            "매우 흐린 시간 %":
                round(very_cloudy_ratio * 100),

            "평균 강수확률 %":
                round(avg_rain),

            "평균 습도 %":
                round(avg_humidity),

            "평균 시정 km":
                round(avg_visibility, 1),

            "평균 풍속 km/h":
                round(avg_wind, 1)
        })


    return pd.DataFrame(rows)

# ==========================================
# 오늘 밤 시간대 구성
# ==========================================

def build_night_dataframe(weather):
    hourly = weather["hourly"]

    df = pd.DataFrame(
        {
            "시간": pd.to_datetime(hourly["time"]),
            "기온": hourly["temperature_2m"],
            "습도": hourly["relative_humidity_2m"],
            "구름량": hourly["cloud_cover"],
            "하층구름": hourly["cloud_cover_low"],
            "중층구름": hourly["cloud_cover_mid"],
            "상층구름": hourly["cloud_cover_high"],
            "강수확률": hourly["precipitation_probability"],
            "강수량": hourly["precipitation"],
            "풍속": hourly["wind_speed_10m"],
            "시정": hourly["visibility"],
        }
    )

    now = datetime.now(KST).replace(tzinfo=None)
    sunrise_today = datetime.fromisoformat(weather["daily"]["sunrise"][0])
    sunset_today = datetime.fromisoformat(weather["daily"]["sunset"][0])
    sunrise_tomorrow = datetime.fromisoformat(weather["daily"]["sunrise"][1])

    if now < sunrise_today:
        start_time = now.replace(minute=0, second=0, microsecond=0)
        end_time = sunrise_today
    elif now < sunset_today:
        start_time = sunset_today
        end_time = sunrise_tomorrow
    else:
        start_time = now.replace(minute=0, second=0, microsecond=0)
        end_time = sunrise_tomorrow

    night_df = df[
        (df["시간"] >= start_time)
        & (df["시간"] <= end_time)
    ].copy()

    night_df["관측점수"] = night_df.apply(
        lambda row: calculate_observation_score(
            row["구름량"],
            row["강수확률"],
            row["시정"],
            row["풍속"],
            row["습도"],
        ),
        axis=1,
    )

    return night_df.reset_index(drop=True), start_time, end_time


def find_best_observation_window(df):
    if len(df) == 0:
        return None

    window_size = min(3, len(df))
    rolling_score = df["관측점수"].rolling(window_size).mean()

    if rolling_score.notna().any():
        best_end_index = rolling_score.idxmax()
    else:
        best_end_index = 0

    best_start_index = max(0, best_end_index - window_size + 1)
    best_start = df.iloc[best_start_index]["시간"]
    best_last = df.iloc[best_end_index]["시간"]
    best_end = best_last + timedelta(hours=1)

    best_score = round(
        df.iloc[best_start_index : best_end_index + 1]["관측점수"].mean()
    )

    return best_start, best_end, best_score


def build_half_hour_weather_timeline(night_df):
    """시간별 날씨 점수를 30분 간격으로 보간해 천체별 최적시간 계산에 사용한다."""
    if len(night_df) == 0:
        return []

    score_df = (
        night_df[["시간", "관측점수"]]
        .set_index("시간")
        .sort_index()
        .resample("30min")
        .interpolate(method="time")
        .reset_index()
    )

    return [
        {
            "time": row["시간"].to_pydatetime(),
            "score": float(row["관측점수"]),
        }
        for _, row in score_df.iterrows()
    ]


# ==========================================
# 앱 실행
# ==========================================

try:
    weather = get_weather(latitude, longitude)
    current = weather["current"]

    engine = AstronomyEngine(
        latitude,
        longitude
    )

    ecmwf_weather = get_ecmwf_weather(
        latitude,
        longitude
    )

    ecmwf_df = build_ecmwf_cloud_forecast(
        ecmwf_weather,
        engine
    )

    gfs_weather = get_gfs_weather(
    latitude,
    longitude
)

    gfs_df = build_gfs_cloud_forecast(
    gfs_weather,
    engine
)

    st.subheader(f"📍 현재 관측지: {location_name}")
    st.subheader("🌦️ 현재 날씨")

    st.markdown(
        """
        <style>

        /* 제목 옆 링크/고정 버튼 숨기기 */
[data-testid="stHeaderActionElements"],
a.anchor-link {
    display: none !important;
}

        .current-weather-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 12px;
            margin-top: 8px;
            margin-bottom: 24px;
        }

        .weather-mini-card {
            border: 1px solid rgba(128, 128, 128, 0.30);
            border-radius: 14px;
            padding: 14px 16px;
            min-width: 0;
        }

        .weather-mini-label {
            font-size: 14px;
            opacity: 0.8;
            margin-bottom: 5px;
        }

        .weather-mini-value {
            font-size: 24px;
            font-weight: 700;
            white-space: nowrap;
        }

        @media (max-width: 768px) {

            .current-weather-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 9px;
            }

            .weather-mini-card {
                padding: 12px;
            }

            .weather-mini-label {
                font-size: 13px;
            }

            .weather-mini-value {
                font-size: 20px;
            }

        }

        </style>
        """,
        unsafe_allow_html=True
    )

    current_weather_html = (
        '<div class="current-weather-grid">'

        '<div class="weather-mini-card">'
        '<div class="weather-mini-label">🌡️ 기온</div>'
        f'<div class="weather-mini-value">{current["temperature_2m"]:.1f} °C</div>'
        '</div>'

        '<div class="weather-mini-card">'
        '<div class="weather-mini-label">☁️ 구름량</div>'
        f'<div class="weather-mini-value">{current["cloud_cover"]:.0f}%</div>'
        '</div>'

        '<div class="weather-mini-card">'
        '<div class="weather-mini-label">💧 습도</div>'
        f'<div class="weather-mini-value">{current["relative_humidity_2m"]:.0f}%</div>'
        '</div>'

        '<div class="weather-mini-card">'
        '<div class="weather-mini-label">💨 풍속</div>'
        f'<div class="weather-mini-value">{current["wind_speed_10m"]:.1f} km/h</div>'
        '</div>'

        '<div class="weather-mini-card">'
        '<div class="weather-mini-label">👁️ 시정</div>'
        f'<div class="weather-mini-value">{current["visibility"] / 1000:.1f} km</div>'
        '</div>'

        '<div class="weather-mini-card">'
        '<div class="weather-mini-label">🌧️ 강수량</div>'
        f'<div class="weather-mini-value">{current["precipitation"]:.1f} mm</div>'
        '</div>'

        '</div>'
    )

    st.markdown(
        current_weather_html,
        unsafe_allow_html=True
    )

    # ======================================
    # 7일 관측 예보
    # ======================================

    st.divider()

    st.header("📅 7일 관측 예보")

    weekly_df = build_weekly_forecast(weather, engine)

    # 기존 Open-Meteo Best Match 구름값 이름 추가
    weekly_df["Best Match 평균 구름 %"] = (
        weekly_df["평균 구름 %"]
    )

    # ECMWF 예보를 날짜 기준으로 합치기
    weekly_df = weekly_df.merge(
        ecmwf_df,
        on="날짜",
        how="left"
    )

    weekly_df = weekly_df.merge(
    gfs_df,
    on="날짜",
    how="left"
)

    model_cloud_columns = [
    "Best Match 평균 구름 %",
    "ECMWF 평균 구름 %",
    "GFS 평균 구름 %"
]

    weekly_df["3모델 평균 구름 %"] = (
    weekly_df[model_cloud_columns]
    .mean(axis=1)
    .round()
)

    weekly_df["모델 차이 %p"] = (
    weekly_df[model_cloud_columns].max(axis=1)
    - weekly_df[model_cloud_columns].min(axis=1)
).round()

    weekly_df["모델 일치도"] = (
        weekly_df["모델 차이 %p"]
        .apply(model_agreement)
    )

    model_agreement_column = weekly_df.pop(
        "모델 일치도"
    )

    grade_position = (
        weekly_df.columns.get_loc("등급") + 1
    )

    weekly_df.insert(
        grade_position,
        "모델 일치도",
        model_agreement_column
    )

    weekly_df["기존 관측 점수"] = (
        weekly_df["관측 점수"]
    )

    weekly_df["3모델 구름 점수"] = (
        weekly_df["3모델 평균 구름 %"]
        .apply(consensus_cloud_score)
    )

    weekly_df["모델 불일치 패널티"] = (
        weekly_df["모델 차이 %p"]
        .apply(
            lambda diff:
                0
                if pd.isna(diff) or diff <= 10
                else min(
                    20,
                    (diff - 10) * 0.4
                )
        )
    )

    weekly_df["최종 관측 점수"] = (
        weekly_df["기존 관측 점수"] * 0.65
        + weekly_df["3모델 구름 점수"] * 0.35
        - weekly_df["모델 불일치 패널티"]
    )

    weekly_df["최종 관측 점수"] = (
        weekly_df["최종 관측 점수"]
        .clip(0, 100)
    )


    # 3모델 평균 구름이 많으면
    # 점수가 지나치게 높아지지 않도록 제한
    weekly_df.loc[
        weekly_df["3모델 평균 구름 %"] >= 80,
        "최종 관측 점수"
    ] = weekly_df.loc[
        weekly_df["3모델 평균 구름 %"] >= 80,
        "최종 관측 점수"
    ].clip(upper=30)

    weekly_df.loc[
        weekly_df["3모델 평균 구름 %"] >= 60,
        "최종 관측 점수"
    ] = weekly_df.loc[
        weekly_df["3모델 평균 구름 %"] >= 60,
        "최종 관측 점수"
    ].clip(upper=50)

    weekly_df.loc[
        weekly_df["3모델 평균 구름 %"] >= 40,
        "최종 관측 점수"
    ] = weekly_df.loc[
        weekly_df["3모델 평균 구름 %"] >= 40,
        "최종 관측 점수"
    ].clip(upper=70)

    # ======================================
    # 달 밝기 / 고도에 따른 관측 감점
    # ======================================

    weekly_df["달 감점"] = weekly_df.apply(
        lambda row: moon_observation_penalty(
            row["달 밝기 %"],
            row["달 고도 °"]
        ),
        axis=1
    )

    weekly_df["달 영향"] = (
        weekly_df["달 감점"]
        .apply(moon_penalty_label)
    )

    moon_effect_column = weekly_df.pop(
        "달 영향"
    )

    moon_penalty_column = weekly_df.pop(
        "달 감점"
    )

    agreement_position = (
        weekly_df.columns.get_loc("모델 일치도") + 1
    )

    weekly_df.insert(
        agreement_position,
        "달 영향",
        moon_effect_column
    )

    weekly_df.insert(
        agreement_position + 1,
        "달 감점",
        moon_penalty_column
    )

    weekly_df["최종 관측 점수"] = (
        weekly_df["최종 관측 점수"]
        - weekly_df["달 감점"]
    )

    weekly_df["최종 관측 점수"] = (
        weekly_df["최종 관측 점수"]
        .clip(0, 100)
    )

    weekly_df["최종 관측 점수"] = (
        weekly_df["최종 관측 점수"]
        .round()
        .astype(int)
    )


    # 기존 '관측 점수'를 최종 점수로 교체
    weekly_df["관측 점수"] = (
        weekly_df["최종 관측 점수"]
    )

    weekly_df["등급"] = (
        weekly_df["관측 점수"]
        .apply(weather_score_grade)
    )

        # ======================================
    # 7일 관측 요약 카드
    # ======================================

    st.subheader("🔭 7일 관측 요약")

    card_df = weekly_df.head(7).reset_index(
        drop=True
    )

    st.markdown(
        """
        <style>
        .weekly-card-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 14px;
            margin-top: 10px;
            margin-bottom: 25px;
        }

        .weekly-card {
            border: 1px solid rgba(128, 128, 128, 0.35);
            border-radius: 16px;
            padding: 18px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        }

        .weekly-card-date {
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 14px;
        }

        .weekly-card-score {
            font-size: 30px;
            font-weight: 800;
            margin-bottom: 12px;
        }

        .weekly-card-info {
            font-size: 14px;
            line-height: 1.8;
        }

                .card-blue {
            border-left: 5px solid #3b82f6;
            background: rgba(59, 130, 246, 0.08);
        }

        .card-green {
            border-left: 5px solid #22c55e;
            background: rgba(34, 197, 94, 0.08);
        }

        .card-yellow {
            border-left: 5px solid #eab308;
            background: rgba(234, 179, 8, 0.08);
        }

        .card-orange {
            border-left: 5px solid #f97316;
            background: rgba(249, 115, 22, 0.08);
        }

        .card-red {
            border-left: 5px solid #ef4444;
            background: rgba(239, 68, 68, 0.08);
        }

        @media (max-width: 1100px) {
            .weekly-card-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }

        @media (max-width: 650px) {
            .weekly-card-grid {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    card_html = '<div class="weekly-card-grid">'

    for _, row in card_df.iterrows():

        card_date = pd.to_datetime(
            row["날짜"]
        )

        weekday_names = [
            "월",
            "화",
            "수",
            "목",
            "금",
            "토",
            "일"
        ]

        weekday_name = weekday_names[
            card_date.weekday()
        ]

        score = int(
            row["관측 점수"]
        )

        if score >= 90:
            status_class = "card-blue"

        elif score >= 80:
            status_class = "card-green"

        elif score >= 65:
            status_class = "card-yellow"

        elif score >= 45:
            status_class = "card-orange"

        else:
            status_class = "card-red"

        card_html += (
            f'<div class="weekly-card {status_class}">'
            f'<div class="weekly-card-date">📅 {row["날짜"]}({weekday_name})</div>'
            f'<div class="weekly-card-grade">{row["등급"]}</div>'
            f'<div class="weekly-card-score">{score}점</div>'
            '<div class="weekly-card-info">'
            f'<b>모델 일치도</b> : {row["모델 일치도"]}<br>'
            f'<b>달 영향</b> : {row["달 영향"]}<br>'
            f'<b>어두운 시간</b> : {row["천문박명 종료"]} ~ {row["천문박명 시작"]}<br>'
            f'<b>최적 시간</b> : {row["최적 시간"]}<br>'
            f'<b>평균 구름</b> : {row["3모델 평균 구름 %"]:.0f}%'
            '</div>'
            '</div>'
        )

    card_html += '</div>'

    st.markdown(
        card_html,
        unsafe_allow_html=True
    )


    # ======================================
    # 7일 상세 예보 표
    # ======================================
    preferred_columns = [
        "날짜",
        "천문박명 종료",
        "천문박명 시작",
        "관측 점수",
        "등급",
        "모델 일치도",
        "달 영향",
        "달 감점",
        "달 밝기 %",
        "달 고도 °",
        "달 상태",
        "최적 시간",
        "최고 예상점수",
        "3모델 평균 구름 %",
        "Best Match 평균 구름 %",
        "ECMWF 평균 구름 %",
        "GFS 평균 구름 %",
        "모델 차이 %p",
        "전체 구름 %",
        "하층 구름 %",
        "중층 구름 %",
        "상층 구름 %",
        "ECMWF 전체 구름 %",
        "ECMWF 하층 구름 %",
        "ECMWF 중층 구름 %",
        "ECMWF 상층 구름 %",
        "GFS 전체 구름 %",
        "GFS 하층 구름 %",
        "GFS 중층 구름 %",
        "GFS 상층 구름 %",
        "흐린 시간 비율 %",
        "매우 흐린 시간 %",
        "평균 강수확률 %",
        "평균 습도 %",
        "평균 시정 km",
        "평균 풍속 km/h"
    ]

    existing_columns = [
        col
        for col in preferred_columns
        if col in weekly_df.columns
    ]

    remaining_columns = [
        col
        for col in weekly_df.columns
        if col not in existing_columns
    ]

    weekly_display_df = weekly_df[
        existing_columns + remaining_columns
    ]

    st.dataframe(
        weekly_display_df,
        use_container_width=True,
        hide_index=True
    )
    
    # ======================================
    # 날짜별 평균 구름량 비교
    # ======================================

    
        # ======================================
    # 날짜별 구름층 비교
    # ======================================

    
    # ======================================
    # 이번 주 관측 추천 TOP 3
    # ======================================

    st.subheader("🏆 이번 주 관측 추천 TOP 3")

    top3 = (
        weekly_df
        .sort_values(
            by="관측 점수",
            ascending=False
        )
        .head(3)
        .reset_index(drop=True)
    )

    rank_col1, rank_col2, rank_col3 = st.columns(3)

    rank_columns = [
        rank_col1,
        rank_col2,
        rank_col3
    ]

    medals = [
        "🥇",
        "🥈",
        "🥉"
    ]

    for i in range(len(top3)):

        row = top3.iloc[i]

        with rank_columns[i]:

            st.markdown(
                f"### {medals[i]} {row['날짜']}"
            )

            st.metric(
                "관측 점수",
                f"{row['관측 점수']}점"
            )

            st.write(
                row["등급"]
            )

            st.write(
                f"🔭 최적 시간: **{row['최적 시간']}**"
            )

            st.write(
                f"⭐ 최고 예상점수: **{row['최고 예상점수']}점**"
            )

            st.write(
                f"☁️ 평균 구름: **{row['평균 구름 %']}%**"
            )


    # ======================================
    # 7일 관측 점수 그래프
    # ======================================

    # --------------------------------------
    # 오늘 밤 관측 조건
    # --------------------------------------

    night_df, night_start, night_end = build_night_dataframe(weather)

    st.divider()
    st.header("🔭 오늘 밤 관측 조건")

    if len(night_df) > 0:  
        average_score = round(night_df["관측점수"].mean())
        best_window = find_best_observation_window(night_df)

        score_col1, score_col2 = st.columns(2)
        score_col1.metric("⭐ 오늘 밤 평균 관측 점수", f"{average_score} / 100")
        score_col2.metric("🌌 관측 등급", weather_score_grade(average_score))
        st.progress(average_score / 100)

        if best_window:
            best_start, best_end, best_score = best_window
            st.success(
                "🔭 추천 관측 시간: "
                f"{best_start.strftime('%m/%d %H:%M')} ~ "
                f"{best_end.strftime('%m/%d %H:%M')}"
                f"  |  예상 점수 {best_score}/100"
            )

       

        with st.expander("📊 시간별 상세 정보"):
            table_df = night_df.copy()
            table_df["시간"] = table_df["시간"].dt.strftime("%m/%d %H:%M")
            table_df["시정"] = (table_df["시정"] / 1000).round(1)
            table_df = table_df[
                [
                    "시간",
                    "관측점수",
                    "구름량",
                    "하층구름",
                    "중층구름",
                    "상층구름",
                    "강수확률",
                    "습도",
                    "풍속",
                    "시정",
                ]
            ].rename(
                columns={
                    "관측점수": "관측 점수",
                    "구름량": "전체 구름 %",
                    "하층구름": "하층 %",
                    "중층구름": "중층 %",
                    "상층구름": "상층 %",
                    "강수확률": "강수확률 %",
                    "습도": "습도 %",
                    "풍속": "풍속 km/h",
                    "시정": "시정 km",
                }
            )
            st.dataframe(table_df, use_container_width=True, hide_index=True)
    else:
        average_score = 70
        st.warning("오늘 밤 시간대의 날씨 데이터를 찾을 수 없습니다.")

    # --------------------------------------
    # 천문 계산 엔진
    # --------------------------------------

    engine = AstronomyEngine(latitude, longitude)

    # --------------------------------------
    # 행성
    # --------------------------------------

    st.divider()
    st.header("🪐 현재 행성 관측 정보")

    with st.spinner("행성 위치를 계산하는 중..."):
        planet_df = engine.get_planets()

    st.dataframe(planet_df, use_container_width=True, hide_index=True)

    visible_planets = planet_df[planet_df["관측"] == "✅ 관측 가능"]

    if len(visible_planets) > 0:
        st.success(
            "🔭 현재 관측 추천: "
            + ", ".join(visible_planets["천체"].tolist())
        )
    else:
        st.warning("현재 조건에서 고도 15° 이상인 관측 추천 행성이 없습니다.")

    st.subheader("⏰ 오늘 밤 행성 출·남중·몰 / 최적 관측시간")
    st.caption(
        "출·몰 시각은 고도 0° 교차, 관측 가능 시간은 천체 고도 15° 이상 + "
        "태양 고도 -6° 이하를 기준으로 계산합니다."
    )

    with st.spinner("오늘 밤 행성 관측 시간을 계산하는 중..."):
        planet_schedule_df = engine.get_planet_night_schedule(
            night_start,
            night_end,
        )

    st.dataframe(
        planet_schedule_df,
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------
    # 달
    # --------------------------------------

    st.divider()
    st.header("🌙 현재 달 관측 정보")

    moon = engine.get_moon()

    moon_col1, moon_col2, moon_col3 = st.columns(3)
    moon_col1.metric("🌙 달 밝기", f'{moon["밝기"]:.1f}%')
    moon_col2.metric("⬆️ 현재 고도", f'{moon["고도"]:.1f}°')
    moon_col3.metric("🧭 방위각", f'{moon["방위각"]:.1f}°')

    moon_col4, moon_col5, moon_col6 = st.columns(3)
    moon_col4.metric("🧭 방향", moon["방향"])
    moon_col5.metric("📏 거리", f'{moon["거리_km"]:,} km')
    moon_col6.metric("🌌 심우주 관측 영향", moon["달빛영향"])

    st.info(f'현재 달 위상: **{moon["위상"]}**')
    st.caption(
        f'달 위상각: {moon["위상각"]:.1f}° | '
        f'달 상태: {moon["상태"]}'
    )

    # --------------------------------------
    # 메시에 M1 ~ M110
    # --------------------------------------

    st.divider()
    st.header("🌌 메시에 M1 ~ M110")
    st.caption(
        "현재 고도·방위각, 오늘 밤 날씨 점수, 달 밝기와 달과의 각거리, "
        "겉보기등급을 합쳐 v1 추천점수를 계산합니다."
    )

    messier_catalog = load_messier_catalog()

    with st.spinner("M1 ~ M110 위치와 관측 조건을 계산하는 중..."):
        messier_df = engine.get_messier_objects(
            messier_catalog,
            weather_score=average_score,
        )

    observable_df = messier_df[messier_df["추천점수"] > 0].copy()

    mcol1, mcol2, mcol3 = st.columns(3)
    mcol1.metric("🔭 현재 관측 가능", f"{len(observable_df)}개")
    mcol2.metric("🌙 달 밝기", f'{moon["밝기"]:.1f}%')

    if len(observable_df) > 0:
        best_messier = observable_df.iloc[0]
        best_label = best_messier["메시에"]
        if best_messier["이름"]:
            best_label += f' {best_messier["이름"]}'
        mcol3.metric(
            "🏆 현재 1순위",
            best_label,
            f'{best_messier["추천점수"]}점',
        )
    else:
        mcol3.metric("🏆 현재 1순위", "없음")

    st.subheader("🏆 오늘의 메시에 추천 TOP 10")

    if len(observable_df) > 0:
        top10 = observable_df.head(10)[
            [
                "메시에",
                "이름",
                "종류",
                "등급",
                "고도 °",
                "방향",
                "달과 각거리 °",
                "추천점수",
                "추천",
            ]
        ]
        st.dataframe(top10, use_container_width=True, hide_index=True)
    else:
        st.warning("현재 시각에는 고도 15° 이상이면서 충분히 어두운 조건의 메시에 천체가 없습니다.")

    st.subheader("⏰ 오늘 밤 메시에 최적 관측시간 TOP 10")
    st.caption(
        "30분 간격의 날씨 점수, 천체 고도, 달 밝기·각거리, 겉보기등급을 함께 계산해 "
        "오늘 밤 가장 좋은 시간대를 찾습니다."
    )

    weather_timeline = build_half_hour_weather_timeline(night_df)

    with st.spinner("M1 ~ M110의 오늘 밤 최적 관측시간을 계산하는 중..."):
        messier_best_df = engine.get_messier_best_times(
            messier_catalog,
            weather_timeline,
        )

    tonight_messier = messier_best_df[
        messier_best_df["오늘 최고점수"] > 0
    ].copy()

    if len(tonight_messier) > 0:
        st.dataframe(
            tonight_messier.head(10),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.warning("오늘 밤 추천 가능한 메시에 천체를 찾지 못했습니다.")

    st.subheader("🔎 M1 ~ M110 전체 목록")

    filter_col1, filter_col2 = st.columns(2)
    only_observable = filter_col1.checkbox("현재 관측 가능한 천체만", value=True)

    type_options = ["전체"] + sorted(messier_df["종류"].dropna().unique().tolist())
    selected_type = filter_col2.selectbox("천체 종류", type_options)

    display_messier = messier_df.copy()

    if only_observable:
        display_messier = display_messier[display_messier["추천점수"] > 0]

    if selected_type != "전체":
        display_messier = display_messier[display_messier["종류"] == selected_type]

    st.dataframe(display_messier, use_container_width=True, hide_index=True)

    st.caption(
        "※ 메시에 추천점수는 동아리용 v1 경험식입니다. "
        "확장천체의 겉보기등급만으로 실제 관측 난이도를 완전히 표현할 수 없으며, "
        "현재 버전에는 시간대별 천체 고도와 최적 관측시간이 추가되었습니다. "
        "다음 버전에서 광공해·천문박명·시상/투명도 등을 더 정교하게 반영할 예정입니다."
    )


except requests.exceptions.RequestException as e:
    st.error("날씨 정보를 불러오지 못했습니다.")
    st.code(str(e))

except FileNotFoundError as e:
    st.error("메시에 데이터 파일을 찾지 못했습니다.")
    st.code(str(e))

except Exception as e:
    st.error("프로그램 실행 중 오류가 발생했습니다.")
    st.exception(e)
