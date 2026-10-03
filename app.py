import base64
import json
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
from utils.astronomy import AstronomyEngine

KST = ZoneInfo("Asia/Seoul")

BASE_DIR = Path(__file__).resolve().parent

MESSIER_PATH = BASE_DIR / "data" / "messier.json"
CONSTELLATION_PATH = BASE_DIR / "data" / "constellations.json"
CLUB_ICON_PATH = BASE_DIR / "assets" / "club_icon.png"

club_icon = None

if CLUB_ICON_PATH.exists():
    club_icon = Image.open(CLUB_ICON_PATH)

st.set_page_config(
    page_title="AAA 관측 도우미",
    page_icon=club_icon if club_icon is not None else "🌌",
    layout="wide",
)

# ==========================================
# 사이드바 지역 검색 버튼 + 크기 고정
# ==========================================

components.html(
    """
    <script>
    const win = window.parent;
    const doc = win.document;

    // ==========================================
    // 이전에 만든 요소 제거
    // ==========================================

    const oldButton =
        doc.getElementById("aaa-sidebar-search-button");

    if (oldButton) {
        oldButton.remove();
    }

    const oldStyle =
        doc.getElementById("aaa-sidebar-search-style");

    if (oldStyle) {
        oldStyle.remove();
    }

    if (win.__aaaSidebarObserver) {
        win.__aaaSidebarObserver.disconnect();
    }


    // ==========================================
    // CSS
    // ==========================================

    const style = doc.createElement("style");

    style.id = "aaa-sidebar-search-style";

    style.textContent = `

   /* ==========================================
   Streamlit 기본 사이드바 열기 버튼 완전 숨김
   우리가 만든 🔍 버튼만 사용
   ========================================== */

[data-testid="stExpandSidebarButton"] {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important;
}

[data-testid="stExpandSidebarButton"] button {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important;
}

        /* ======================================
           사이드바 폭 고정
           ====================================== */

        section[data-testid="stSidebar"][aria-expanded="true"] {
            width: 320px !important;
            min-width: 320px !important;
            max-width: 320px !important;
        }


        /* ======================================
           사이드바가 열린 상태의 기본 버튼
           ====================================== */

        section[data-testid="stSidebar"][aria-expanded="true"]
        [data-testid="stSidebarCollapseButton"] {
            opacity: 1 !important;
            visibility: visible !important;
            display: flex !important;
        }

        section[data-testid="stSidebar"][aria-expanded="true"]
        [data-testid="stSidebarCollapseButton"] button {
            opacity: 1 !important;
            visibility: visible !important;

            width: 38px !important;
            height: 38px !important;

            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }


        /* 기존 화살표 숨기기 */
        section[data-testid="stSidebar"][aria-expanded="true"]
        [data-testid="stSidebarCollapseButton"] button > * {
            display: none !important;
        }


        /* 열린 상태 돋보기 */
        section[data-testid="stSidebar"][aria-expanded="true"]
        [data-testid="stSidebarCollapseButton"] button::after {
            content: "🔍";

            display: block !important;

            font-size: 21px !important;
            line-height: 1 !important;

            opacity: 1 !important;
            visibility: visible !important;
        }


        /* ======================================
           닫힌 상태에서 사용할 우리 버튼
           ====================================== */

        #aaa-sidebar-search-button {
            position: fixed;

            top: 10px;
            left: 10px;

            z-index: 999999;

            width: 42px;
            height: 42px;

            padding: 0;

            border: none;
            border-radius: 10px;

            background: transparent;

            display: flex;
            align-items: center;
            justify-content: center;

            font-size: 22px;
            line-height: 1;

            cursor: pointer;

            opacity: 1;
            visibility: visible;
        }

        #aaa-sidebar-search-button:hover {
            background: rgba(128, 128, 128, 0.12);
        }


        /* ======================================
           리사이즈 영역 제거
           ====================================== */

        [data-testid="stSidebarResizeHandle"] {
            display: none !important;
            pointer-events: none !important;
            cursor: default !important;
        }


        /* inline style로 만들어지는
           Streamlit 리사이즈 영역까지 제거 */
        section[data-testid="stSidebar"]
        [style*="cursor: col-resize"],
        section[data-testid="stSidebar"]
        [style*="cursor: ew-resize"],
        section[data-testid="stSidebar"]
        [style*="cursor: e-resize"] {
            display: none !important;
            pointer-events: none !important;
            cursor: default !important;
        }


        /* ======================================
           모바일
           ====================================== */

        @media (max-width: 640px) {

            section[data-testid="stSidebar"][aria-expanded="true"] {
                width: 85vw !important;
                min-width: 85vw !important;
                max-width: 85vw !important;
            }

            #aaa-sidebar-search-button {
                top: 8px;
                left: 8px;

                width: 38px;
                height: 38px;

                font-size: 20px;
            }
        }
    `;

    doc.head.appendChild(style);


    // ==========================================
    // 닫힌 상태용 돋보기 버튼 생성
    // ==========================================

    const searchButton =
        doc.createElement("button");

    searchButton.id =
        "aaa-sidebar-search-button";

    searchButton.type =
        "button";

    searchButton.innerHTML =
        "🔍";

    searchButton.title =
        "지역 검색";

    searchButton.setAttribute(
        "aria-label",
        "지역 검색"
    );

    doc.body.appendChild(searchButton);


    // ==========================================
    // 사이드바 열림/닫힘 상태 확인
    // ==========================================

    function updateSearchButton() {

        const sidebar =
            doc.querySelector(
                '[data-testid="stSidebar"]'
            );

        if (!sidebar) {
            searchButton.style.display = "flex";
            return;
        }

        const expanded =
            sidebar.getAttribute(
                "aria-expanded"
            ) === "true";


        // 사이드바가 닫혀 있을 때만
        // 별도 돋보기 버튼 표시
        if (expanded) {

            searchButton.style.display =
                "none";

        } else {

            searchButton.style.display =
                "flex";
        }
    }


    // ==========================================
    // 사이드바 크기 조절 영역 완전 제거
    // ==========================================

    function disableSidebarResize() {

        const sidebar =
            doc.querySelector(
                '[data-testid="stSidebar"]'
            );

        if (!sidebar) {
            return;
        }

        const elements =
            sidebar.querySelectorAll("*");

        elements.forEach(
            function(element) {

                const computed =
                    win.getComputedStyle(
                        element
                    );

                const cursor =
                    computed.cursor || "";

                if (
                    cursor.includes("resize")
                ) {

                    element.style.setProperty(
                        "pointer-events",
                        "none",
                        "important"
                    );

                    element.style.setProperty(
                        "cursor",
                        "default",
                        "important"
                    );
                }
            }
        );
    }


   // ==========================================
// 돋보기 클릭 → 실제 사이드바 열기 버튼 클릭
// ==========================================

searchButton.addEventListener(
    "click",
    function() {

        const expandContainer =
            doc.querySelector(
                '[data-testid="stExpandSidebarButton"]'
            );

        if (!expandContainer) {
            return;
        }

        const realButton =
            expandContainer.matches("button")
                ? expandContainer
                : expandContainer.querySelector("button");

        if (!realButton) {
            return;
        }

        realButton.click();

        setTimeout(
            function() {
                updateSearchButton();
                disableSidebarResize();
            },
            100
        );
    }
);


    // ==========================================
    // Streamlit이 화면을 다시 그려도 재적용
    // ==========================================

    const observer =
        new MutationObserver(
            function() {

                updateSearchButton();
                disableSidebarResize();
            }
        );

    observer.observe(
        doc.body,
        {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: [
                "aria-expanded",
                "style"
            ]
        }
    );

    win.__aaaSidebarObserver =
        observer;


    // 처음 한 번 실행
    updateSearchButton();
    disableSidebarResize();

    </script>
    """,
    height=0,
)

# ==========================================
# 모바일 Pull-to-Refresh
# ==========================================

# ==========================================
# 오른쪽 아래 새로고침 버튼
# ==========================================

components.html(
    """
    <script>
    const win = window.parent;
    const doc = win.document;

    // Streamlit 재실행 시 기존 버튼 제거
    const oldButton =
        doc.getElementById(
            "astro-floating-refresh"
        );

    if (oldButton) {
        oldButton.remove();
    }

    const oldStyle =
        doc.getElementById(
            "astro-floating-refresh-style"
        );

    if (oldStyle) {
        oldStyle.remove();
    }


    // 버튼 스타일
    const style =
        doc.createElement("style");

    style.id =
        "astro-floating-refresh-style";

    style.textContent = `
        #astro-floating-refresh {
            position: fixed;

            right: 16px;
            bottom: calc(
                90px + env(safe-area-inset-bottom)
            );

            width: 52px;
            height: 52px;

            border: 1px solid
                rgba(128, 128, 128, 0.35);

            border-radius: 50%;

            background:
                rgba(30, 30, 30, 0.88);

            color: white;

            font-size: 25px;

            display: flex;
            align-items: center;
            justify-content: center;

            cursor: pointer;

            z-index: 999999;

            box-shadow:
                0 4px 14px
                rgba(0, 0, 0, 0.25);

            -webkit-tap-highlight-color:
                transparent;

            -webkit-user-select: none;
            user-select: none;

            transition:
                transform 0.15s ease,
                opacity 0.15s ease;
        }

        #astro-floating-refresh:active {
            transform: scale(0.90);
        }

        #astro-floating-refresh.loading {
            animation:
                astro-refresh-spin
                0.65s
                linear
                infinite;
        }

        @keyframes astro-refresh-spin {

            from {
                transform: rotate(0deg);
            }

            to {
                transform: rotate(360deg);
            }
        }
    `;

    doc.head.appendChild(style);


    // 버튼 생성
    const button =
        doc.createElement("button");

    button.id =
        "astro-floating-refresh";

    button.type = "button";

    button.innerHTML = "↻";

    button.setAttribute(
        "aria-label",
        "새로고침"
    );

    button.setAttribute(
        "title",
        "새로고침"
    );


    // 버튼 클릭
    button.addEventListener(
        "click",
        function() {

            if (
                button.classList.contains(
                    "loading"
                )
            ) {
                return;
            }

            button.classList.add(
                "loading"
            );


            // 새로고침 후 맨 위에서 시작
            win.sessionStorage.setItem(
                "astroForceScrollTop",
                "1"
            );

            win.scrollTo(
                0,
                0
            );


            setTimeout(
                function() {

                    win.location.reload();

                },
                300
            );
        }
    );


    doc.body.appendChild(
        button
    );
    </script>
    """,
    height=0,
)

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
    height=0,
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
    unsafe_allow_html=True,
)

# ==========================================
# 장소 이름 → 위도 / 경도 검색
# ==========================================


@st.cache_data(ttl=3600)
def search_location(search_text):

    url = "https://nominatim.openstreetmap.org/search"

    headers = {"User-Agent": "AstroObservationClubApp/1.0"}

    search_text = search_text.strip()

    search_candidates = [
        search_text,
        f"{search_text}시",
        f"{search_text}군",
        f"{search_text}읍",
    ]

    allowed_types = {"city", "county", "town", "village", "municipality"}

    final_results = []
    seen = set()

    for candidate in search_candidates:

        params = {
            "q": f"{candidate}, 대한민국",
            "format": "jsonv2",
            "countrycodes": "kr",
            "limit": 10,
            "addressdetails": 1,
            "accept-language": "ko",
        }

        response = requests.get(url, params=params, headers=headers, timeout=10)

        response.raise_for_status()

        results = response.json()

        for result in results:

            address_type = result.get("addresstype", "")

            if address_type not in allowed_types:
                continue

            lat = result.get("lat")
            lon = result.get("lon")

            key = (result.get("display_name", ""), lat, lon)

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

with st.sidebar.form("location_search_form"):

    search_text = st.text_input("🔎 장소 검색", placeholder="예: 용인, 안동, 소백산")

    search_pressed = st.form_submit_button("검색", use_container_width=True)


# Enter 또는 검색 버튼
if search_pressed:

    if search_text.strip():

        try:

            results = search_location(search_text.strip())

            if len(results) == 0:

                st.sidebar.warning("검색 결과가 없습니다.")

            else:

                selected = results[0]

                address = selected.get("address", {})

                selected_lat = float(selected["lat"])

                selected_lon = float(selected["lon"])

                selected_name = (
                    selected.get("name")
                    or address.get("city")
                    or address.get("town")
                    or address.get("county")
                    or "선택한 위치"
                )

                st.session_state["applied_latitude"] = selected_lat

                st.session_state["applied_longitude"] = selected_lon

                st.session_state["applied_location_name"] = selected_name

                st.session_state["location_results"] = []

                st.rerun()

        except Exception as e:

            st.sidebar.error("장소 검색 중 오류가 발생했습니다.")

            st.sidebar.code(str(e))

    else:

        st.sidebar.warning("검색할 장소를 입력해주세요.")


# ==========================================
# 검색 결과
# ==========================================

results = st.session_state["location_results"]


if len(results) > 0:

    result_labels = []

    for result in results:

        address = result.get("address", {})

        name = result.get("name", "")

        city = (
            address.get("city")
            or address.get("town")
            or address.get("municipality")
            or address.get("county")
            or ""
        )

        province = address.get("state") or address.get("province") or ""

        lat = float(result["lat"])

        lon = float(result["lon"])

        # 중복 이름 제거
        parts = []

        for part in [name, city, province]:

            if part and part not in parts:
                parts.append(part)

        short_name = " / ".join(parts)

        # 검색 결과를 너무 길지 않게 표시
        label = f"{short_name} " f"({lat:.4f}, {lon:.4f})"

        result_labels.append(label)

    selected_index = st.sidebar.selectbox(
        "검색 결과",
        options=range(len(result_labels)),
        format_func=lambda i: result_labels[i],
    )

    if st.sidebar.button("📍 이 위치 사용", use_container_width=True):

        selected = results[selected_index]

        address = selected.get("address", {})

        selected_lat = float(selected["lat"])

        selected_lon = float(selected["lon"])

        selected_name = (
            selected.get("name")
            or address.get("city")
            or address.get("town")
            or address.get("county")
            or "선택한 위치"
        )

        # 실제 앱에서 사용할 위치 변경
        st.session_state["applied_latitude"] = selected_lat

        st.session_state["applied_longitude"] = selected_lon

        st.session_state["applied_location_name"] = selected_name

        # 검색 결과 닫기
        st.session_state["location_results"] = []

        st.rerun()


# ==========================================
# 실제 앱에서 사용할 현재 위치
# ==========================================

latitude = float(st.session_state["applied_latitude"])

longitude = float(st.session_state["applied_longitude"])

location_name = st.session_state["applied_location_name"]


# ==========================================
# 현재 적용된 관측지 표시
# ==========================================

st.sidebar.divider()

st.sidebar.subheader("📌 현재 적용된 관측지")

st.sidebar.success(location_name)

st.sidebar.write(f"위도: **{latitude:.4f}°**")

st.sidebar.write(f"경도: **{longitude:.4f}°**")


# ==========================================
# 날씨 API
# ==========================================


@st.cache_data(ttl=600)
def get_weather(latitude, longitude):

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "models": "ecmwf_ifs",
        "latitude": latitude,
        "longitude": longitude,
        "timezone": "Asia/Seoul",
        "forecast_days": 8,
        "past_hours": 24,
        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "cloud_cover,"
            "precipitation,"
            "weather_code,"
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
        ),
    }

    response = requests.get(url, params=params, timeout=10)

    response.raise_for_status()

    return response.json()


@st.cache_data
def load_messier_catalog():
    with open(MESSIER_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_constellation_catalog():
    with open(
        CONSTELLATION_PATH,
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


# ==========================================
# 관측 날씨 점수
# ==========================================


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


def calculate_dew_risk(
    temperature,
    humidity,
):
    # Magnus 공식으로 이슬점 계산
    a = 17.62
    b = 243.12

    gamma = (a * temperature) / (b + temperature) + np.log(humidity / 100.0)

    dew_point = b * gamma / (a - gamma)

    temperature_gap = temperature - dew_point

    # 기온과 이슬점의 차이가 작을수록
    # 광학계에 이슬이 생길 가능성이 높음
    if temperature_gap >= 6:
        icon = "🟢"
        advice = "걱정 적음"

    elif temperature_gap >= 4:
        icon = "🟡"
        advice = "렌즈 상태 확인"

    elif temperature_gap >= 2:
        icon = "🟠"
        advice = "듀히터 준비 권장"

    else:
        icon = "🔴"
        advice = "듀히터 사용 권장"

    return {
        "icon": icon,
        "advice": advice,
        "dew_point": round(
            dew_point,
            1,
        ),
        "gap": round(
            temperature_gap,
            1,
        ),
    }


def cloud_cell_style(value):

    if pd.isna(value):
        return ""

    value = max(0, min(100, float(value)))

    # 0% = 검정
    # 100% = 흰색
    gray = round(255 * (value / 100))

    # 밝은 배경에서는 검정 글씨
    # 어두운 배경에서는 흰 글씨
    if value >= 65:
        text_color = "black"
    else:
        text_color = "white"

    return (
        f"background-color: "
        f"rgb({gray}, {gray}, {gray}); "
        f"color: {text_color}; "
        "font-weight: 600;"
    )


def moon_observation_penalty(
    brightness,
    altitude,
):

    if pd.isna(brightness) or pd.isna(altitude):
        return 0

    # ======================================
    # 달이 지평선 아래면 영향 없음
    # ======================================

    if altitude <= 0:
        return 0

    # ======================================
    # 달이 떠 있는 것 자체에 기본 감점
    # ======================================

    presence_penalty = 3

    # ======================================
    # 달 밝기에 따른 추가 감점
    # ======================================

    if brightness < 10:
        brightness_penalty = 0

    elif brightness < 20:
        brightness_penalty = 2

    elif brightness < 40:
        brightness_penalty = 5

    elif brightness < 60:
        brightness_penalty = 9

    elif brightness < 80:
        brightness_penalty = 14

    else:
        brightness_penalty = 20

    # ======================================
    # 달 고도
    #
    # 높이 떠 있을수록 영향 증가
    # ======================================

    if altitude < 10:
        altitude_factor = 0.5

    elif altitude < 20:
        altitude_factor = 0.7

    elif altitude < 30:
        altitude_factor = 0.85

    else:
        altitude_factor = 1.0

    penalty = (presence_penalty + brightness_penalty) * altitude_factor

    return round(
        penalty,
        1,
    )


def calculate_night_moon_effect(engine, night_df):

    if len(night_df) == 0:
        return {
            "brightness": 0,
            "altitude": -90,
            "penalty": 0,
            "moon_up_ratio": 0,
            "status": "🌑 계산 불가",
        }

    brightness_values = []
    altitude_values = []
    penalty_values = []

    for observation_time in night_df["시간"]:

        moon_info = engine.get_moon_at_time(observation_time)

        brightness = float(moon_info["밝기"])

        altitude = float(moon_info["고도"])

        penalty = moon_observation_penalty(
            brightness,
            altitude,
        )

        brightness_values.append(brightness)

        altitude_values.append(altitude)

        penalty_values.append(penalty)

    # 밤 평균 달 밝기
    average_brightness = round(
        sum(brightness_values) / len(brightness_values),
        1,
    )

    # 달이 실제로 떠 있는 시간
    visible_altitudes = [altitude for altitude in altitude_values if altitude > 0]

    moon_up_ratio = len(visible_altitudes) / len(altitude_values)

    # 달이 떠 있을 때 평균 고도
    if visible_altitudes:

        average_altitude = round(
            sum(visible_altitudes) / len(visible_altitudes),
            1,
        )

    else:

        average_altitude = round(
            max(altitude_values),
            1,
        )

    # 기본 밤 평균 감점
    average_penalty = sum(penalty_values) / len(penalty_values)

    # 밤 중 가장 강한 달 영향
    maximum_penalty = max(penalty_values)

    # ======================================
    # 달이 오래 떠 있으면
    # 평균값 때문에 감점이 약해지는 현상 보정
    # ======================================

    effective_penalty = average_penalty

    if moon_up_ratio >= 0.70:

        effective_penalty = max(
            effective_penalty,
            maximum_penalty * 0.90,
        )

    elif moon_up_ratio >= 0.50:

        effective_penalty = max(
            effective_penalty,
            maximum_penalty * 0.80,
        )

    elif moon_up_ratio >= 0.30:

        effective_penalty = max(
            effective_penalty,
            maximum_penalty * 0.65,
        )

    elif moon_up_ratio > 0:

        effective_penalty = max(
            effective_penalty,
            maximum_penalty * 0.40,
        )

    effective_penalty = round(
        effective_penalty,
        1,
    )

    # ======================================
    # 밤 전체 달 상태
    # ======================================

    if moon_up_ratio == 0:

        status = "🌑 밤새 지평선 아래"

    elif moon_up_ratio < 0.30:

        status = "🌙 잠깐 떠 있음"

    elif moon_up_ratio < 0.60:

        status = "🌙 밤 일부 떠 있음"

    else:

        status = "🌕 밤 대부분 떠 있음"

    return {
        "brightness": average_brightness,
        "altitude": average_altitude,
        "penalty": effective_penalty,
        "moon_up_ratio": round(
            moon_up_ratio * 100,
            1,
        ),
        "status": status,
    }


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

    effective_cloud = max(total, low, mid * 0.95, high * 0.85)

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
        row["상층구름"],
    )

    # 실제 관측에 가장 방해가 되는 구름층 기준
    effective_cloud = max(
        row["전체구름"],
        row["하층구름"],
        row["중층구름"] * 0.95,
        row["상층구름"] * 0.85,
    )

    rain_score = max(
        0,
        100 - row["강수확률"] * 1.5,
    )

    visibility_km = row["시정"] / 1000

    visibility_score = min(
        100,
        (visibility_km / 20) * 100,
    )

    if row["풍속"] <= 10:
        wind_score = 100
    else:
        wind_score = max(
            0,
            100 - (row["풍속"] - 10) * 4,
        )

    if row["습도"] <= 70:
        humidity_score = 100
    else:
        humidity_score = max(
            0,
            100 - (row["습도"] - 70) * 3.3,
        )

    # 구름 영향 강화
    score = (
        cloud_score * 0.70
        + rain_score * 0.15
        + visibility_score * 0.06
        + wind_score * 0.04
        + humidity_score * 0.05
    )

    # 실제 강수가 있으면 강한 감점
    if row["강수량"] >= 0.1:
        score = min(score, 30)

    # 구름량에 따른 관측 점수 상한
    if effective_cloud >= 90:
        score = min(score, 10)

    elif effective_cloud >= 80:
        score = min(score, 18)

    elif effective_cloud >= 70:
        score = min(score, 28)

    elif effective_cloud >= 60:
        score = min(score, 38)

    elif effective_cloud >= 50:
        score = min(score, 48)

    elif effective_cloud >= 40:
        score = min(score, 58)

    elif effective_cloud >= 30:
        score = min(score, 68)

    elif effective_cloud >= 20:
        score = min(score, 80)

    return round(max(0, min(100, score)))


def build_weekly_forecast(weather, engine):

    daily = weather["daily"]
    hourly = weather["hourly"]

    # 시간별 날씨 DataFrame
    hourly_df = pd.DataFrame(
        {
            "시간": pd.to_datetime(hourly["time"]),
            "전체구름": hourly["cloud_cover"],
            "하층구름": hourly["cloud_cover_low"],
            "중층구름": hourly["cloud_cover_mid"],
            "상층구름": hourly["cloud_cover_high"],
            "강수확률": hourly["precipitation_probability"],
            "강수량": hourly["precipitation"],
            "시정": hourly["visibility"],
            "풍속": hourly["wind_speed_10m"],
            "습도": hourly["relative_humidity_2m"],
        }
    )

    rows = []

    # ======================================
    # 7일 예보의 첫 관측 날짜 결정
    #
    # 자정 ~ 일출 전:
    # 전날 저녁부터 시작된 관측 밤을 유지
    #
    # 일출 이후:
    # 오늘 저녁부터 시작할 관측 밤 사용
    # ======================================

    now = datetime.now(KST)
    now_naive = now.replace(tzinfo=None)

    sunrise_today = datetime.fromisoformat(daily["sunrise"][0])

    if now_naive < sunrise_today:
        first_observation_date = now.date() - timedelta(days=1)

    else:
        first_observation_date = now.date()

    # ======================================
    # 화면에는 현재 관측 밤부터 7일 표시
    # ======================================

    for i in range(7):

        date = (first_observation_date + timedelta(days=i)).isoformat()

        # ==================================
        # 정확한 천문학적 밤 계산
        #
        # 저녁 천문박명 종료
        # ~
        # 다음날 아침 천문박명 시작
        # ==================================

        astro_start, astro_end = engine.get_astronomical_night(date)

        if astro_start is None or astro_end is None:
            continue

        # ==================================
        # 해당 밤의 중간 시각 달 상태
        # ==================================

        # Open-Meteo 시간 데이터는
        # timezone 정보가 없는 KST 시간이므로
        # 비교를 위해 timezone 제거
        astro_start_naive = astro_start.replace(tzinfo=None)

        astro_end_naive = astro_end.replace(tzinfo=None)

        night = hourly_df[
            (hourly_df["시간"] >= astro_start_naive)
            & (hourly_df["시간"] <= astro_end_naive)
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
                row["상층구름"] * 0.85,
            ),
            axis=1,
        )

        # ==================================
        # 시간별 관측 점수
        # ==================================

        night["시간점수"] = night.apply(hourly_weather_score, axis=1)

        # ==================================
        # 밤 전체 점수용 통계
        # ==================================

        average_score = night["시간점수"].mean()

        lower_score = night["시간점수"].quantile(0.25)

        best_score = night["시간점수"].max()

        # 구름 40% 이상인 시간 비율
        cloudy_ratio = (night["유효구름량"] >= 40).mean()

        # 구름 40~69%인 시간 비율
        moderate_cloudy_ratio = (
            (night["유효구름량"] >= 40) & (night["유효구름량"] < 70)
        ).mean()

        # 구름 70% 이상인 시간 비율
        very_cloudy_ratio = (night["유효구름량"] >= 70).mean()

        # 강수확률 30% 이상인 시간 비율
        rainy_ratio = (night["강수확률"] >= 30).mean()

        # ==================================
        # 최종 밤 점수
        # ==================================

        average_effective_cloud = night["유효구름량"].mean()

        # 평균보다 나쁜 시간대의 영향을 더 크게 반영
        score = average_score * 0.55 + lower_score * 0.35 + best_score * 0.10

        # ==================================
        # 밤 전체 추가 감점
        # ==================================

        # 40~69% 구름인 시간
        score -= moderate_cloudy_ratio * 18

        # 70% 이상 매우 흐린 시간
        score -= very_cloudy_ratio * 25

        # 비 올 가능성이 높은 시간
        score -= rainy_ratio * 12

        # 평균 구름량 추가 반영
        score -= average_effective_cloud * 0.15

        # ==================================
        # 점수 상한
        # ==================================

        # 구름 40% 이상인 시간이 밤의 1/3 이상
        if cloudy_ratio >= 0.35:
            score = min(score, 78)

        # 구름 40% 이상인 시간이 밤의 절반 이상
        if cloudy_ratio >= 0.50:
            score = min(score, 68)

        # 매우 흐린 시간이 30% 이상
        if very_cloudy_ratio >= 0.30:
            score = min(score, 58)

        # 매우 흐린 시간이 절반 이상
        if very_cloudy_ratio >= 0.50:
            score = min(score, 48)

        # 비 가능성이 높은 시간이 30% 이상
        if rainy_ratio >= 0.30:
            score = min(score, 52)

        score = round(max(0, min(100, score)))

        grade = weather_score_grade(score)


        # ==================================
        # 밤 전체의 달 영향 계산
        # ==================================

        moon_effect = calculate_night_moon_effect(
            engine,
            night,
        )

        night_moon_brightness = moon_effect["brightness"]

        night_moon_altitude = moon_effect["altitude"]

        moon_penalty = moon_effect["penalty"]

        moon_up_ratio = moon_effect["moon_up_ratio"]

        night_moon_status = moon_effect["status"]

        # ==================================
        # 날씨 + 달을 고려한 최적 관측 구간
        # 30분 단위 계산
        # ==================================

        night_for_timeline = night.copy()

        night_for_timeline["관측점수"] = night_for_timeline["시간점수"]

        half_hour_timeline = build_half_hour_weather_timeline(night_for_timeline)

        observation_hours = []

        for hour_info in half_hour_timeline:

            observation_time = hour_info["time"]

            weather_hour_score = float(hour_info["score"])

            # ==================================
            # 해당 시간의 달 상태
            # ==================================

            hour_moon_info = engine.get_moon_at_time(observation_time)

            hour_moon_brightness = float(hour_moon_info["밝기"])

            hour_moon_altitude = float(hour_moon_info["고도"])

            # ==================================
            # 관측 가능 조건
            #
            # 1. 시간별 날씨 점수 65점 이상
            # 2. 달이 지평선 아래
            # ==================================

            weather_ok = weather_hour_score >= 65

            moonless = hour_moon_altitude <= 0

            usable = weather_ok and moonless

            observation_hours.append(
                {
                    "time": observation_time,
                    "score": weather_hour_score,
                    "moon_brightness": (hour_moon_brightness),
                    "moon_altitude": (hour_moon_altitude),
                    "weather_ok": weather_ok,
                    "moonless": moonless,
                    "usable": usable,
                }
            )

        # ==================================
        # 30분 단위 연속 관측 가능 구간 찾기
        # ==================================

        observation_ranges = []
        current_range = []

        for hour_info in observation_hours:

            if hour_info["usable"]:

                if current_range:

                    previous_time = current_range[-1]["time"]

                    time_gap = hour_info["time"] - previous_time

                    # 30분 간격이 끊겼으면
                    # 새로운 구간으로 분리
                    if time_gap > timedelta(minutes=35):

                        observation_ranges.append(current_range)

                        current_range = []

                current_range.append(hour_info)

            else:

                if current_range:

                    observation_ranges.append(current_range)

                    current_range = []

        if current_range:

            observation_ranges.append(current_range)

        # ==================================
        # 가장 좋은 연속 구간 선택
        # ==================================

        if observation_ranges:

            # 가장 긴 구간 우선
            # 길이가 같으면 평균 날씨 점수가 높은 구간
            best_range = max(
                observation_ranges,
                key=lambda current: (
                    len(current),
                    sum(item["score"] for item in current) / len(current),
                ),
            )

            best_range_start = best_range[0]["time"]

            # 마지막 관측 가능 시점에서
            # 30분 뒤까지를 구간 끝으로 설정
            best_range_end = best_range[-1]["time"] + timedelta(minutes=30)

            # 천문박명 시작 시간과
            # 시간대 형식을 동일하게 맞춤
            astro_end_compare = pd.Timestamp(astro_end)

            if astro_end_compare.tzinfo is not None:
                astro_end_compare = astro_end_compare.tz_localize(None)

            astro_end_compare = astro_end_compare.to_pydatetime()

            # 마지막 날씨 데이터까지 계속
            # 관측 가능했다면 실제 천문박명 시작까지 연장
            if (
                half_hour_timeline
                and best_range[-1]["time"] == half_hour_timeline[-1]["time"]
                and best_range_end < astro_end_compare
            ):
                best_range_end = astro_end_compare

            # 어두운 시간이 끝난 뒤까지
            # 추천하지 않도록 제한
            if best_range_end > astro_end_compare:
                best_range_end = astro_end_compare

            # 같은 날짜면 시간만 표시
            if best_range_start.date() == best_range_end.date():
                best_time_range = (
                    f"{best_range_start.strftime('%H:%M')}"
                    f" ~ "
                    f"{best_range_end.strftime('%H:%M')}"
                )

            # 자정을 넘으면 날짜까지 표시
            else:
                best_time_range = (
                    f"{best_range_start.strftime('%m/%d %H:%M')}"
                    f" ~ "
                    f"{best_range_end.strftime('%m/%d %H:%M')}"
                )

        else:

            best_time_range = "추천 구간 없음"
        
        # ==================================
        # 밤 시간 평균값 계산
        # ==================================

        avg_total_cloud = night["전체구름"].mean()
        avg_low_cloud = night["하층구름"].mean()
        avg_mid_cloud = night["중층구름"].mean()
        avg_high_cloud = night["상층구름"].mean()

        avg_effective_cloud = night["유효구름량"].mean()

        avg_rain = night["강수확률"].mean()
        avg_humidity = night["습도"].mean()

        avg_visibility = night["시정"].mean() / 1000

        avg_wind = night["풍속"].mean()

        rows.append(
            {
                "날짜": date,
                "천문박명 종료": astro_start.strftime("%H:%M"),
                "천문박명 시작": astro_end.strftime("%H:%M"),
                "관측 점수": score,
                "등급": grade,
                "달 밝기 %": night_moon_brightness,
                "달 고도 °": night_moon_altitude,
                "달 상태": night_moon_status,
                "달 감점": moon_penalty,
                "달 떠있는 시간 %": moon_up_ratio,
                "최적 시간": best_time_range,
                "최고 예상점수": round(best_score),
                "평균 구름 %": round(avg_effective_cloud),
                "전체 구름 %": round(avg_total_cloud),
                "하층 구름 %": round(avg_low_cloud),
                "중층 구름 %": round(avg_mid_cloud),
                "상층 구름 %": round(avg_high_cloud),
                "흐린 시간 비율 %": round(cloudy_ratio * 100),
                "매우 흐린 시간 %": round(very_cloudy_ratio * 100),
                "평균 강수확률 %": round(avg_rain),
                "평균 습도 %": round(avg_humidity),
                "평균 시정 km": round(avg_visibility, 1),
                "평균 풍속 km/h": round(avg_wind, 1),
            }
        )

    return pd.DataFrame(rows)


# ==========================================
# 오늘 밤 시간대 구성
# ==========================================


def build_night_dataframe(
    weather,
    engine,
):

    hourly = weather["hourly"]

    df = pd.DataFrame(
        {
            "시간": pd.to_datetime(hourly["time"]),
            "기온": hourly["temperature_2m"],
            "습도": hourly["relative_humidity_2m"],
            "구름량": hourly["cloud_cover"],
            "전체구름": hourly["cloud_cover"],
            "하층구름": hourly["cloud_cover_low"],
            "중층구름": hourly["cloud_cover_mid"],
            "상층구름": hourly["cloud_cover_high"],
            "강수확률": hourly["precipitation_probability"],
            "강수량": hourly["precipitation"],
            "풍속": hourly["wind_speed_10m"],
            "시정": hourly["visibility"],
        }
    )

    # ======================================
    # 현재 관측 밤의 날짜 결정
    #
    # 자정 ~ 일출 전:
    # 전날 저녁부터 시작된 밤을 계속 사용
    #
    # 일출 이후:
    # 오늘 저녁부터 시작할 밤 사용
    # ======================================

    now = datetime.now(KST)

    now_naive = now.replace(tzinfo=None)

    sunrise_today = datetime.fromisoformat(weather["daily"]["sunrise"][0])

    if now_naive < sunrise_today:

        observation_date = now.date() - timedelta(days=1)

    else:

        observation_date = now.date()

    # ======================================
    # 해당 관측 밤의 천문박명 구간
    # ======================================

    astro_start, astro_end = engine.get_astronomical_night(observation_date.isoformat())

    if astro_start is None or astro_end is None:

        return (
            pd.DataFrame(),
            now_naive,
            now_naive,
        )

    start_time = astro_start.replace(tzinfo=None)

    end_time = astro_end.replace(tzinfo=None)

    # ======================================
    # 해당 밤의 데이터만 사용
    # ======================================

    night_df = df[(df["시간"] >= start_time) & (df["시간"] <= end_time)].copy()

    # ======================================
    # 시간별 관측 점수
    # ======================================

    night_df["관측점수"] = night_df.apply(
        hourly_weather_score,
        axis=1,
    )

    return (
        night_df.reset_index(drop=True),
        start_time,
        end_time,
    )


def build_day_weather_dataframe(weather):

    hourly = weather["hourly"]

    df = pd.DataFrame(
        {
            "시간": pd.to_datetime(hourly["time"]),
            "기온": hourly["temperature_2m"],
            "습도": hourly["relative_humidity_2m"],
            "구름량": hourly["cloud_cover"],
            "전체구름": hourly["cloud_cover"],
            "하층구름": hourly["cloud_cover_low"],
            "중층구름": hourly["cloud_cover_mid"],
            "상층구름": hourly["cloud_cover_high"],
            "강수확률": hourly["precipitation_probability"],
            "강수량": hourly["precipitation"],
            "풍속": hourly["wind_speed_10m"],
            "시정": hourly["visibility"],
        }
    )

    # 현재 시간을 정각 기준으로 맞춤
    current_hour = (
        datetime.now(KST)
        .replace(
            minute=0,
            second=0,
            microsecond=0,
        )
        .replace(tzinfo=None)
    )

    # 현재 시간 이후 데이터만 사용
    day_df = df[df["시간"] >= current_hour].copy()

    # 현재 시간부터 24시간 롤링 표시
    day_df = day_df.head(48)

    day_df["관측점수"] = day_df.apply(
        hourly_weather_score,
        axis=1,
    )

    return day_df.reset_index(drop=True)


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
    # 시간별 날씨 자료를 30분 간격으로 보간

    if len(night_df) == 0:
        return []

    working_df = night_df.copy()

    # 유효구름량이 아직 없으면 여기서 계산
    if "유효구름량" not in working_df.columns:
        working_df["유효구름량"] = working_df.apply(
            lambda row: max(
                row["전체구름"],
                row["하층구름"],
                row["중층구름"] * 0.95,
                row["상층구름"] * 0.85,
            ),
            axis=1,
        )

    score_df = (
        working_df[
            [
                "시간",
                "관측점수",
                "유효구름량",
            ]
        ]
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
            "cloud": float(row["유효구름량"]),
        }
        for _, row in score_df.iterrows()
    ]


def apply_timeline_moon_cap(
    score,
    brightness,
    altitude,
):
    score = float(score)
    brightness = float(brightness)
    altitude = float(altitude)

    # 달이 지평선 아래면 점수 제한 없음
    if altitude <= 0:
        return round(max(0, min(100, score)))

    # 매우 밝은 달
    if brightness >= 70:

        if altitude >= 30:
            cap = 44

        elif altitude >= 15:
            cap = 54

        else:
            cap = 64

    # 중간 밝기의 달
    elif brightness >= 40:

        if altitude >= 30:
            cap = 54

        elif altitude >= 15:
            cap = 64

        else:
            cap = 74

    # 비교적 어두운 달
    elif brightness >= 20:

        if altitude >= 30:
            cap = 64

        elif altitude >= 15:
            cap = 74

        else:
            cap = 79

    # 매우 얇은 달
    else:

        if altitude >= 30:
            cap = 74

        else:
            cap = 84

    return round(
        max(
            0,
            min(
                100,
                score,
                cap,
            ),
        )
    )


def timeline_observation_status(score):

    score = float(score)

    if score >= 90:
        return "🔵 매우 좋음"

    elif score >= 80:
        return "🟢 좋음"

    elif score >= 65:
        return "🟡 관측 가능"

    elif score >= 45:
        return "🟠 관측 주의"

    else:
        return "🔴 관측 비추천"


def get_main_timeline_rows(
    timeline_rows,
):

    now = datetime.now(KST).replace(tzinfo=None)

    rows = [
        item
        for item in timeline_rows
        if (item["_datetime"].minute == 0 and item["_datetime"] >= now)
    ]

    rows = sorted(
        rows,
        key=lambda item: item["_datetime"],
    )

    return rows[:6]


def get_current_weather_visual(current):

    weather_code = int(current.get("weather_code", 0))

    cloud_cover = float(current.get("cloud_cover", 0))

    temperature = float(current.get("temperature_2m", 0))

    precipitation = float(current.get("precipitation", 0))

    # ======================================
    # 눈
    # ======================================

    if weather_code in [71, 73, 75, 77, 85, 86] or (
        precipitation > 0 and temperature <= 1
    ):
        return {
            "icon": "❄️",
            "label": "눈",
        }

    # ======================================
    # 비
    # ======================================

    if (
        weather_code
        in [
            51,
            53,
            55,
            61,
            63,
            65,
            80,
            81,
            82,
            95,
            96,
            99,
        ]
        or precipitation > 0
    ):
        return {
            "icon": "🌧️",
            "label": "비",
        }

    # ======================================
    # 안개
    # ======================================

    if weather_code in [45, 48]:
        return {
            "icon": "🌫️",
            "label": "안개",
        }

    # ======================================
    # 맑음 / 구름
    # ======================================

    if weather_code == 0 or cloud_cover <= 15:
        return {
            "icon": "☀️",
            "label": "맑음",
        }

    elif weather_code in [1, 2] or cloud_cover <= 45:
        return {
            "icon": "⛅",
            "label": "구름 약간",
        }

    else:
        return {
            "icon": "☁️",
            "label": "흐림",
        }


# ==========================================
# 앱 실행
# ==========================================

try:
    weather = get_weather(latitude, longitude)
    current = weather["current"]

    engine = AstronomyEngine(latitude, longitude)

    # ==========================================
    # AAA 동아리 로고 + 제목
    # ==========================================

    club_icon_base64 = base64.b64encode(CLUB_ICON_PATH.read_bytes()).decode("utf-8")

    st.markdown(
        f"""
        <h1 style="margin-bottom: 8px;">
            <img
                src="data:image/png;base64,{club_icon_base64}"
                width="34"
                height="34"
                style="
                    vertical-align: middle;
                    object-fit: contain;
                    margin-right: 8px;
                "
            >
            <span style="vertical-align: middle;">
                AAA 관측 도우미 
            </span>
        </h1>
        """,
        unsafe_allow_html=True,
    )

    st.write("AAA를 위한 관측 지원 도구입니다.")

    st.subheader(f"📍 현재 관측지: {location_name}")
    current_weather_visual = get_current_weather_visual(current)

    st.subheader(f'{current_weather_visual["icon"]} 현재 날씨')

    dew_risk = calculate_dew_risk(
        current["temperature_2m"],
        current["relative_humidity_2m"],
    )

    current_weather_visual = get_current_weather_visual(current)

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
             
                        .current-weather-hero {
                padding: 16px 12px;
                margin-bottom: 10px;
            }

            .current-weather-hero-icon {
                font-size: 44px;
            }

            .current-weather-hero-label {
                font-size: 20px;
            }

            .current-weather-hero-sub {
                font-size: 13px;
            } 


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
        unsafe_allow_html=True,
    )

    current_weather_html = (
        '<div class="current-weather-grid">'
        '<div class="weather-mini-card">'
        '<div class="weather-mini-label">🌡️ 기온</div>'
        f'<div class="weather-mini-value">{current["temperature_2m"]:.1f} °C</div>'
        "</div>"
        '<div class="weather-mini-card">'
        '<div class="weather-mini-label">☁️ 구름량</div>'
        f'<div class="weather-mini-value">{current["cloud_cover"]:.0f}%</div>'
        "</div>"
        '<div class="weather-mini-card">'
        '<div class="weather-mini-label">💧 습도</div>'
        f'<div class="weather-mini-value">{current["relative_humidity_2m"]:.0f}%</div>'
        "</div>"
        '<div class="weather-mini-card">'
        '<div class="weather-mini-label">💧 이슬 위험</div>'
        f'<div class="weather-mini-value">{dew_risk["icon"]} {dew_risk["advice"]}</div>'
        f'<div style="font-size:0.8rem; opacity:0.75; margin-top:4px;">'
        f'이슬점 {dew_risk["dew_point"]:.1f}°C · '
        f'기온차 {dew_risk["gap"]:.1f}°C'
        "</div>"
        "</div>"
        '<div class="weather-mini-card">'
        '<div class="weather-mini-label">💨 풍속</div>'
        f'<div class="weather-mini-value">{current["wind_speed_10m"]:.1f} km/h</div>'
        "</div>"
        '<div class="weather-mini-card">'
        '<div class="weather-mini-label">👁️ 시정</div>'
        f'<div class="weather-mini-value">{current["visibility"] / 1000:.1f} km</div>'
        "</div>"
        '<div class="weather-mini-card">'
        '<div class="weather-mini-label">🌧️ 강수량</div>'
        f'<div class="weather-mini-value">{current["precipitation"]:.1f} mm</div>'
        "</div>"
        "</div>"
    )

    st.markdown(current_weather_html, unsafe_allow_html=True)

    # ======================================
    # 7일 관측 예보
    # ======================================

    st.divider()

    st.header("📅 7일 관측 예보")

    weekly_df = build_weekly_forecast(weather, engine)

    # ======================================
    # 달 밝기 / 고도에 따른 관측 감점
    # ======================================

    weekly_df["달 영향"] = weekly_df["달 감점"].apply(moon_penalty_label)

    # ======================================
    # 달 영향 적용
    # ======================================

    # 기본 달 감점
    # 달 밝기와 달이 떠 있는 시간을 이용한
    # 최종 점수 상한 적용

    def apply_moon_score_cap(row):

        score = row["관측 점수"]

        penalty = row["달 감점"]
        brightness = row["달 밝기 %"]
        moon_up_ratio = row["달 떠있는 시간 %"]

        # ======================================
        # 매우 밝은 달
        # ======================================

        # 밝기 70% 이상 + 밤 대부분 떠 있음
        if brightness >= 70 and moon_up_ratio >= 60:
            score = min(score, 55)

        # 밝기 60% 이상 + 밤 절반 가까이 떠 있음
        elif brightness >= 60 and moon_up_ratio >= 40:
            score = min(score, 60)

        # 밝기 60% 이상 + 밤 일부 떠 있음
        elif brightness >= 60 and moon_up_ratio >= 25:
            score = min(score, 65)

        # ======================================
        # 중간 밝기의 달
        # ======================================

        # 밝기 40% 이상 + 오래 떠 있음
        elif brightness >= 40 and moon_up_ratio >= 40:
            score = min(score, 72)

        # 밝기 40% 이상 + 밤 일부 떠 있음
        elif brightness >= 40 and moon_up_ratio >= 25:
            score = min(score, 78)

        # ======================================
        # 비교적 약한 달
        # ======================================

        # 밝기 25% 이상 + 오래 떠 있음
        elif brightness >= 25 and moon_up_ratio >= 40:
            score = min(score, 82)

        # 밝기 25% 이상 + 밤 일부 떠 있음
        elif brightness >= 25 and moon_up_ratio >= 25:
            score = min(score, 88)

        # ======================================
        # 기존 달 감점 보조 기준
        # ======================================

        elif penalty > 15:
            score = min(score, 60)

        elif penalty > 9:
            score = min(score, 68)

        elif penalty > 4:
            score = min(score, 82)

        return score

    weekly_df["관측 점수"] = weekly_df.apply(
        apply_moon_score_cap,
        axis=1,
    )

    weekly_df["관측 점수"] = weekly_df["관측 점수"].clip(0, 100).round().astype(int)

    weekly_df["등급"] = weekly_df["관측 점수"].apply(weather_score_grade)
    # ======================================
    # 7일 관측 요약 카드
    # ======================================

    st.subheader("🔭 7일 관측 요약")

    card_df = weekly_df.head(7).reset_index(drop=True)

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

        .weekly-card-grade {
            font-size: 17px;
            font-weight: 700;
            margin-bottom: 6px;
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
        grid-template-columns:
            repeat(
                2,
                minmax(0, 1fr)
            );

        gap: 8px;
    }

    .weekly-card {
        padding: 11px 8px;
    }

    .weekly-card-date {
        font-size: 14px;
        margin-bottom: 8px;
    }

    .weekly-card-score {
        font-size: 24px;
    }

    .weekly-card-grade {
        font-size: 12px;
    }

    .weekly-card-info {
        font-size: 11px;
        line-height: 1.5;
    }
}
        </style>
        """,
        unsafe_allow_html=True,
    )

    card_html = '<div class="weekly-card-grid">'

    weekday_names = ["월", "화", "수", "목", "금", "토", "일"]

    for _, row in card_df.iterrows():

        card_date = pd.to_datetime(row["날짜"])

        weekday_name = weekday_names[card_date.weekday()]

        score = int(row["관측 점수"])

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
            f'<div class="weekly-card-date">'
            f'📅 {row["날짜"]}({weekday_name})'
            f"</div>"
            f'<div class="weekly-card-grade">'
            f'{row["등급"]}'
            f"</div>"
            f'<div class="weekly-card-score">'
            f"{score}점"
            f"</div>"
            '<div class="weekly-card-info">'
            f'<b>달 영향</b> : {row["달 영향"]}<br>'
            f"<b>어두운 시간</b> : "
            f'{row["천문박명 종료"]} ~ '
            f'{row["천문박명 시작"]}<br>'
            f"<b>최적 시간</b> : "
            f'{row["최적 시간"]}<br>'
            f"<b>평균 구름</b> : "
            f'{row["평균 구름 %"]:.0f}%'
            "</div>"
            "</div>"
        )

    card_html += "</div>"

    st.markdown(card_html, unsafe_allow_html=True)

    # ======================================
    # 7일 상세 예보 표
    # ======================================

    preferred_columns = [
        "날짜",
        "천문박명 종료",
        "천문박명 시작",
        "관측 점수",
        "등급",
        "달 영향",
        "달 떠있는 시간 %",
        "달 감점",
        "달 밝기 %",
        "달 고도 °",
        "달 상태",
        "최적 시간",
        "최고 예상점수",
        "평균 강수확률 %",
        "평균 습도 %",
    ]

    existing_columns = [col for col in preferred_columns if col in weekly_df.columns]

    weekly_display_df = weekly_df[existing_columns].copy()

    weekly_display_df = weekly_display_df.reset_index(drop=True)

    st.dataframe(weekly_display_df, use_container_width=True, hide_index=True)

    # ======================================
    # 이번 주 관측 추천 TOP 3
    # ======================================

    st.subheader("🏆 이번 주 관측 추천 TOP 3")

    top3 = (
        weekly_df.sort_values(by="관측 점수", ascending=False)
        .head(3)
        .reset_index(drop=True)
    )

    st.markdown(
        """
        <style>
        .top3-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 6px;
            margin-top: 8px;
            margin-bottom: 24px;
        }

        .top3-card {
            border: 1px solid rgba(128, 128, 128, 0.30);
            border-radius: 12px;
            padding: 11px 5px;
            text-align: center;
            min-width: 0;
        }

        .top3-medal {
            font-size: 22px;
        }

        .top3-date {
            font-size: 12px;
            font-weight: 700;
            margin: 3px 0 5px 0;
            white-space: nowrap;
        }

        .top3-score {
            font-size: 23px;
            font-weight: 800;
            margin-bottom: 5px;
        }

        .top3-grade {
            font-size: 11px;
            font-weight: 700;
            margin-bottom: 7px;
            white-space: nowrap;
        }

        .top3-info {
            font-size: 11px;
            line-height: 1.55;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    medals = ["🥇", "🥈", "🥉"]
    weekday_names = ["월", "화", "수", "목", "금", "토", "일"]

    top3_html = '<div class="top3-grid">'

    for i in range(len(top3)):

        row = top3.iloc[i]

        card_date = pd.to_datetime(row["날짜"])

        short_date = (
            f"{card_date.month}/{card_date.day}"
            f"({weekday_names[card_date.weekday()]})"
        )

        score = int(row["관측 점수"])

        top3_html += (
            '<div class="top3-card">'
            f'<div class="top3-medal">{medals[i]}</div>'
            f'<div class="top3-date">{short_date}</div>'
            f'<div class="top3-score">{score}점</div>'
            f'<div class="top3-grade">{row["등급"]}</div>'
            '<div class="top3-info">'
            f'🔭 {row["최적 시간"]}<br>'
            f'☁️ {row["평균 구름 %"]:.0f}%'
            "</div>"
            "</div>"
        )

    top3_html += "</div>"

    st.markdown(top3_html, unsafe_allow_html=True)

    # --------------------------------------
    # 오늘 밤 관측 조건
    # --------------------------------------

    night_df, night_start, night_end = build_night_dataframe(weather, engine)

    st.divider()
    st.header("🔭 오늘 밤 관측 조건")

    if len(night_df) > 0:

        # ======================================
        # 7일 예보의 오늘 점수를 그대로 사용
        # ======================================

        today_string = night_start.strftime("%Y-%m-%d")

        today_forecast = weekly_df[weekly_df["날짜"].astype(str) == today_string]

        if len(today_forecast) > 0:

            today_row = today_forecast.iloc[0]

            average_score = int(today_row["관측 점수"])

            night_grade = today_row["등급"]

        else:

            average_score = 0
            night_grade = "⚪ 계산 불가"

        # ======================================
        # 오늘 밤 추천 시간
        # ======================================

        best_window = find_best_observation_window(night_df)

        if best_window:

            best_start, best_end, best_score = best_window

            if best_start.date() == best_end.date():

                recommended_time = (
                    f"{best_start.strftime('%m/%d %H:%M')}"
                    f" ~ "
                    f"{best_end.strftime('%H:%M')}"
                )

            else:

                recommended_time = (
                    f"{best_start.strftime('%m/%d %H:%M')}"
                    f" ~ "
                    f"{best_end.strftime('%m/%d %H:%M')}"
                )

            recommendation_text = (
                f"🔭 추천 시간: {recommended_time}" f" · 예상 {best_score}점"
            )

        else:

            recommendation_text = "🔭 추천 시간 계산 불가"

        # ======================================
        # 오늘 밤 요약 카드 스타일
        # ======================================

        st.markdown(
            """
            <style>
            .night-summary-grid {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 9px;
                margin-top: 8px;
                margin-bottom: 9px;
            }

            .night-summary-card {
                border: 1px solid rgba(128, 128, 128, 0.30);
                border-radius: 14px;
                padding: 14px 12px;
                text-align: center;
                min-width: 0;
            }

            .night-summary-label {
                font-size: 13px;
                opacity: 0.8;
                margin-bottom: 5px;
            }

            .night-summary-value {
                font-size: 26px;
                font-weight: 800;
                line-height: 1.2;
            }

            .night-summary-grade {
                font-size: 18px;
                font-weight: 700;
                line-height: 1.3;
            }

            .night-recommendation {
                border: 1px solid rgba(128, 128, 128, 0.30);
                border-radius: 14px;
                padding: 12px;
                text-align: center;
                font-size: 14px;
                font-weight: 700;
                margin-bottom: 16px;
            }

            @media (max-width: 768px) {

                .night-summary-grid {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                    gap: 7px;
                }

                .night-summary-card {
                    padding: 12px 7px;
                }

                .night-summary-label {
                    font-size: 12px;
                }

                .night-summary-value {
                    font-size: 24px;
                }

                .night-summary-grade {
                    font-size: 15px;
                }

                .night-recommendation {
                    font-size: 13px;
                    padding: 10px 7px;
                }
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        # ======================================
        # 오늘 밤 요약 카드
        # ======================================

        night_summary_html = (
            '<div class="night-summary-grid">'
            '<div class="night-summary-card">'
            '<div class="night-summary-label">'
            "⭐ 관측 점수"
            "</div>"
            f'<div class="night-summary-value">'
            f"{average_score}점"
            f"</div>"
            "</div>"
            '<div class="night-summary-card">'
            '<div class="night-summary-label">'
            "🌌 관측 등급"
            "</div>"
            f'<div class="night-summary-grade">'
            f"{night_grade}"
            f"</div>"
            "</div>"
            "</div>"
            f'<div class="night-recommendation">'
            f"{recommendation_text}"
            "</div>"
        )

        st.markdown(night_summary_html, unsafe_allow_html=True)

        # ======================================
        # 오늘 밤 30분 단위 관측 타임라인
        # ======================================

        st.subheader("🌙 오늘 밤 관측 타임라인")

        # 기존 시간별 날씨를 30분 단위로 보간
        observation_timeline = build_half_hour_weather_timeline(night_df)

        # ======================================
        # 오늘 밤 천문박명 구간 계산
        # ======================================

        timeline_date = night_start.strftime("%Y-%m-%d")

        astro_start, astro_end = engine.get_astronomical_night(timeline_date)

        timeline_rows = []

        if astro_start is not None and astro_end is not None:

            # 날씨 데이터와 비교하기 위해
            # timezone 제거
            astro_start_naive = astro_start.replace(tzinfo=None)

            astro_end_naive = astro_end.replace(tzinfo=None)

            # ==================================
            # 30분 단위 데이터 구성
            # ==================================

            for item in observation_timeline:

                observation_time = item["time"]

                # 완전히 어두운 천문박명 구간만 표시
                if not (astro_start_naive <= observation_time <= astro_end_naive):
                    continue

                weather_score = float(item["score"])

                cloud = float(item["cloud"])

                # 해당 시각 달 상태
                moon_info = engine.get_moon_at_time(observation_time)

                moon_brightness = float(moon_info["밝기"])

                moon_altitude = float(moon_info["고도"])

                # 달빛 감점
                moon_penalty = moon_observation_penalty(
                    moon_brightness,
                    moon_altitude,
                )

                final_score = weather_score - moon_penalty

                final_score = apply_timeline_moon_cap(
                    final_score,
                    moon_brightness,
                    moon_altitude,
                )

                status = timeline_observation_status(final_score)

                # 달 상태 표시
                if moon_altitude <= 0:
                    moon_text = "🌑 지평선 아래"

                else:
                    moon_text = f"{moon_brightness:.0f}%" f" / {moon_altitude:.0f}°"

                timeline_rows.append(
                    {
                        "_datetime": observation_time,
                        "시간": (observation_time.strftime("%H:%M")),
                        "관측 점수": (final_score),
                        "상태": status,
                        "구름 %": round(cloud),
                        "달": moon_text,
                    }
                )

                # ======================================
        # 화면 출력
        # ======================================

        if timeline_rows:

            st.caption("현재 이후의 관측 조건을 " "1시간 단위로 최대 6개 표시합니다.")

            # ======================================
            # 타임라인 카드 스타일
            # ======================================

            st.markdown(
                """
                <style>

                /* ==============================
                   메인 6개 타임라인
                   ============================== */

                .observation-timeline-grid {
                    display: grid;

                    grid-template-columns:
                        repeat(
                            3,
                            minmax(0, 1fr)
                        );

                    gap: 10px;

                    margin-top: 12px;
                    margin-bottom: 14px;
                }


                /* ==============================
                   전체 시간 타임라인
                   ============================== */

                .observation-timeline-full-grid {
                    display: grid;

                    grid-template-columns:
                        repeat(
                            4,
                            minmax(0, 1fr)
                        );

                    gap: 10px;

                    margin-top: 12px;
                    margin-bottom: 12px;
                }


                /* ==============================
                   공통 카드
                   ============================== */

                .observation-timeline-card {
                    position: relative;
                    border:
                        1px solid
                        rgba(
                            128,
                            128,
                            128,
                            0.30
                        );

                    border-radius: 14px;

                    padding: 13px 11px;

                    min-width: 0;

                    text-align: center;

                    box-shadow:
                        0 2px 7px
                        rgba(
                            0,
                            0,
                            0,
                            0.06
                        );
                }
                
                .timeline-recommend-badge {
    position: absolute;

    top: 8px;
    right: 8px;

    padding: 3px 7px;

    border-radius: 999px;

    font-size: 10px;
    font-weight: 800;

    background:
        rgba(
            255,
            193,
            7,
            0.18
        );

    border:
        1px solid
        rgba(
            255,
            193,
            7,
            0.55
        );

    white-space: nowrap;
}

                .timeline-recommend-reason {
    font-size: 11px;
    font-weight: 700;

    margin-top: -2px;
    margin-bottom: 7px;

    opacity: 0.85;
}

                .timeline-past {
    opacity: 0.38;
}               
 
                .timeline-time {
                    font-size: 19px;

                    font-weight: 800;

                    margin-bottom: 7px;
                }


                .timeline-status {
                    font-size: 14px;

                    font-weight: 700;

                    margin-bottom: 8px;

                    white-space: nowrap;
                }


                .timeline-score {
                    font-size: 25px;

                    font-weight: 800;

                    margin-bottom: 8px;
                }


                .timeline-info {
                    font-size: 12px;

                    line-height: 1.65;

                    opacity: 0.88;
                }


                /* ==============================
                   점수별 카드 색상
                   ============================== */

                .timeline-blue {
                    border-left:
                        5px solid
                        #3b82f6;

                    background:
                        rgba(
                            59,
                            130,
                            246,
                            0.08
                        );
                }


                .timeline-green {
                    border-left:
                        5px solid
                        #22c55e;

                    background:
                        rgba(
                            34,
                            197,
                            94,
                            0.08
                        );
                }


                .timeline-yellow {
                    border-left:
                        5px solid
                        #eab308;

                    background:
                        rgba(
                            234,
                            179,
                            8,
                            0.08
                        );
                }


                .timeline-orange {
                    border-left:
                        5px solid
                        #f97316;

                    background:
                        rgba(
                            249,
                            115,
                            22,
                            0.08
                        );
                }


                .timeline-red {
                    border-left:
                        5px solid
                        #ef4444;

                    background:
                        rgba(
                            239,
                            68,
                            68,
                            0.08
                        );
                }


                /* ==============================
                   태블릿
                   ============================== */

                @media (max-width: 1000px) {

                    .observation-timeline-full-grid {
                        grid-template-columns:
                            repeat(
                                3,
                                minmax(0, 1fr)
                            );
                    }

                }


                /* ==============================
                   모바일
                   ============================== */

                @media (max-width: 768px) {

                    .observation-timeline-grid,
                    .observation-timeline-full-grid {
                        grid-template-columns:
                            repeat(
                                2,
                                minmax(0, 1fr)
                            );

                        gap: 8px;
                    }


                    .observation-timeline-card {
                        padding: 11px 7px;
                    }


                    .timeline-time {
                        font-size: 17px;
                    }


                    .timeline-status {
                        font-size: 12px;
                    }


                    .timeline-score {
                        font-size: 22px;
                    }


                    .timeline-info {
                        font-size: 11px;
                    }

                }

                </style>
                """,
                unsafe_allow_html=True,
            )

            # ======================================
            # 카드 HTML 생성 함수
            # ======================================

            def build_timeline_card_html(
                rows,
                grid_class,
                show_recommendation=False,
                dim_past=False,
            ):

                html = f'<div class="{grid_class}">'

                # ==================================
                # 추천 카드 선택
                # ==================================

                recommended_time = None

                if show_recommendation and rows:

                    recommended_item = max(
                        rows,
                        key=lambda item: (item["관측 점수"]),
                    )

                    recommended_time = recommended_item["_datetime"]

                # ==================================
                # 카드 생성
                # ==================================

                for item in rows:

                    score = int(item["관측 점수"])

                    # ==================================
                    # 지난 시간 카드 흐리게 표시
                    # ==================================

                    past_class = ""

                    if dim_past:

                        current_time = datetime.now(KST).replace(tzinfo=None)

                        if item["_datetime"] < current_time:

                            past_class = " timeline-past"

                    # ==================================
                    # 점수별 카드 색상
                    # ==================================

                    if score >= 90:

                        status_class = "timeline-blue"

                    elif score >= 80:

                        status_class = "timeline-green"

                    elif score >= 65:

                        status_class = "timeline-yellow"

                    elif score >= 45:

                        status_class = "timeline-orange"

                    else:

                        status_class = "timeline-red"

                    # ==================================
                    # 추천 배지 + 추천 이유
                    # ==================================

                    recommend_badge = ""
                    recommend_reason = ""

                    if show_recommendation and item["_datetime"] == recommended_time:

                        recommend_badge = (
                            '<div class="'
                            "timeline-recommend-badge"
                            '">'
                            "⭐ 추천"
                            "</div>"
                        )

                    if "지평선 아래" in item["달"] and item["구름 %"] <= 10:

                        recommend_reason = (
                            '<div class="'
                            "timeline-recommend-reason"
                            '">'
                            "⭐ 달 없음 · 맑음"
                            "</div>"
                        )

                    elif "지평선 아래" in item["달"]:

                        recommend_reason = (
                            '<div class="'
                            "timeline-recommend-reason"
                            '">'
                            "⭐ 달 없음"
                            "</div>"
                        )

                    elif item["구름 %"] <= 10:

                        recommend_reason = (
                            '<div class="'
                            "timeline-recommend-reason"
                            '">'
                            "⭐ 맑음"
                            "</div>"
                        )

                    html += (
                        f'<div class="'
                        f"observation-timeline-card "
                        f"{status_class}"
                        f"{past_class}"
                        f'">'
                        f"{recommend_badge}"
                        f'<div class="'
                        f"timeline-time"
                        f'">'
                        f'{item["시간"]}'
                        f"</div>"
                        f'<div class="'
                        f"timeline-status"
                        f'">'
                        f'{item["상태"]}'
                        f"</div>"
                        f'<div class="'
                        f"timeline-score"
                        f'">'
                        f"{score}점"
                        f"</div>"
                        f"{recommend_reason}"
                        f'<div class="'
                        f"timeline-info"
                        f'">'
                        f"☁️ 구름 "
                        f'{item["구름 %"]}%'
                        f"<br>"
                        f"🌙 달 "
                        f'{item["달"]}'
                        f"</div>"
                        f"</div>"
                    )

                html += "</div>"

                return html

                # ======================================

            # 메인 6개 자동 갱신
            # ======================================

            @st.fragment(run_every="1min")
            def render_live_timeline():

                display_timeline_rows = get_main_timeline_rows(timeline_rows)

                if display_timeline_rows:

                    main_timeline_html = build_timeline_card_html(
                        display_timeline_rows,
                        ("observation-" "timeline-grid"),
                        show_recommendation=True,
                    )

                    st.markdown(
                        main_timeline_html,
                        unsafe_allow_html=True,
                    )

                else:

                    st.info("현재 이후 남아 있는 " "관측 시간이 없습니다.")

            render_live_timeline()
            # ======================================
            # 전체 시간 보기
            # ======================================

            with st.expander(
                "📋 전체 시간 보기",
                expanded=False,
            ):

                st.caption("오늘 밤 천문박명 구간 전체를 " "30분 단위로 표시합니다.")

                full_timeline_html = build_timeline_card_html(
                    timeline_rows, ("observation-" "timeline-full-grid"), dim_past=True
                )

                st.markdown(
                    full_timeline_html,
                    unsafe_allow_html=True,
                )

        else:

            st.info("오늘 밤 관측 타임라인을 " "계산할 수 없습니다.")
        # ======================================
        # 오늘 밤 이슬 위험 요약
        # ======================================

        night_dew_df = night_df[
            [
                "시간",
                "기온",
                "습도",
            ]
        ].copy()

        night_dew_results = night_dew_df.apply(
            lambda row: calculate_dew_risk(
                float(row["기온"]),
                float(row["습도"]),
            ),
            axis=1,
        )

        night_dew_df["이슬점"] = night_dew_results.apply(
            lambda result: result["dew_point"]
        )

        night_dew_df["기온차"] = night_dew_results.apply(lambda result: result["gap"])

        night_dew_df["아이콘"] = night_dew_results.apply(lambda result: result["icon"])

        night_dew_df["안내"] = night_dew_results.apply(lambda result: result["advice"])

        risk_rank = {
            "🟢": 0,
            "🟡": 1,
            "🟠": 2,
            "🔴": 3,
        }

        night_dew_df["위험순위"] = night_dew_df["아이콘"].map(risk_rank)

        worst_rank = int(night_dew_df["위험순위"].max())

        worst_rows = night_dew_df[night_dew_df["위험순위"] == worst_rank]

        first_worst = worst_rows.iloc[0]

        first_worst_time = first_worst["시간"].strftime("%H:%M")

        worst_icon = first_worst["아이콘"]
        worst_advice = first_worst["안내"]

        minimum_gap = night_dew_df["기온차"].min()

        if worst_rank == 0:

            dew_summary_text = (
                "💧 오늘 밤 이슬 위험 : "
                "🟢 걱정 적음"
                f" · 최저 기온차 {minimum_gap:.1f}°C"
            )

            st.info(dew_summary_text)

        else:

            dew_summary_text = (
                f"💧 오늘 밤 이슬 주의 : "
                f"{first_worst_time}부터 "
                f"{worst_icon} {worst_advice}"
                f" · 최저 기온차 {minimum_gap:.1f}°C"
            )

            if worst_rank >= 2:
                st.warning(dew_summary_text)
            else:
                st.info(dew_summary_text)

        # ======================================
        # 시간별 상세 정보
        # ======================================

        @st.fragment(run_every="1m")
        def show_hourly_weather_table():

            # 현재 시각부터 앞으로 48시간을
            # 자동으로 다시 계산
            current_day_weather_df = build_day_weather_dataframe(weather)

            with st.expander("📊 시간별 상세 정보"):

                table_df = current_day_weather_df.copy()

                # ======================================
                # 시간별 이슬점 / 이슬 위험 계산
                # ======================================

                dew_results = table_df.apply(
                    lambda row: calculate_dew_risk(
                        float(row["기온"]),
                        float(row["습도"]),
                    ),
                    axis=1,
                )

                table_df["이슬점"] = dew_results.apply(
                    lambda result: result["dew_point"]
                )

                table_df["이슬 위험"] = dew_results.apply(
                    lambda result: (f"{result['icon']} " f"{result['advice']}")
                )

                # 현재 시간을 정각 기준으로 계산
                current_hour = (
                    datetime.now(KST)
                    .replace(
                        minute=0,
                        second=0,
                        microsecond=0,
                    )
                    .replace(tzinfo=None)
                )

                # ======================================
                # 7일 예보의 모든 천문 관측 밤 구간
                # ======================================

                night_intervals = []

                for _, forecast_row in weekly_df.iterrows():

                    forecast_date = pd.to_datetime(forecast_row["날짜"]).date()

                    astro_start_text = str(forecast_row["천문박명 종료"])

                    astro_end_text = str(forecast_row["천문박명 시작"])

                    astro_start_datetime = pd.to_datetime(
                        f"{forecast_date} {astro_start_text}"
                    )

                    astro_end_datetime = pd.to_datetime(
                        f"{forecast_date} {astro_end_text}"
                    )

                    # 천문박명 시작은 다음 날 새벽
                    if astro_end_datetime <= astro_start_datetime:
                        astro_end_datetime += timedelta(days=1)

                    night_intervals.append(
                        (
                            astro_start_datetime,
                            astro_end_datetime,
                        )
                    )

                # 시간 표시 함수
                def format_hourly_time(time):

                    markers = []

                    # 현재 시간
                    if time == current_hour:
                        markers.append("➡")

                    # 천문 관측 밤 구간
                    is_astronomical_night = any(
                        start <= time <= end for start, end in night_intervals
                    )

                    if is_astronomical_night:
                        markers.append("🌙")

                    time_text = time.strftime("%m/%d %H:%M")

                    if markers:
                        return f"{' '.join(markers)} {time_text}"

                    return time_text

                table_df["시간"] = table_df["시간"].apply(format_hourly_time)

                # 시정 m → km
                table_df["시정"] = (table_df["시정"] / 1000).round(1)

                table_df = table_df[
                    [
                        "시간",
                        "관측점수",
                        "구름량",
                        "하층구름",
                        "중층구름",
                        "상층구름",
                        "이슬 위험",
                        "강수확률",
                        "습도",
                        "이슬점",
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
                        "이슬점": "이슬점 °C",
                        "풍속": "풍속 km/h",
                        "시정": "시정 km",
                    }
                )

                # 밤 시간대 행 강조
                def highlight_night_row(row):

                    if "🌙" in str(row["시간"]):
                        return [
                            (
                                "background-color: #28364f; "
                                "color: white; "
                                "font-weight: 700; "
                                "border-top: 1px solid #52698f; "
                                "border-bottom: 1px solid #52698f;"
                            )
                            for _ in row
                        ]

                    return ["" for _ in row]

                styled_table_df = (
                    table_df.style.map(
                        cloud_cell_style,
                        subset=[
                            "전체 구름 %",
                            "하층 %",
                            "중층 %",
                            "상층 %",
                        ],
                    )
                    .apply(
                        highlight_night_row,
                        axis=1,
                        subset=[
                            "시간",
                            "관측 점수",
                            "강수확률 %",
                            "습도 %",
                            "이슬점 °C",
                            "이슬 위험",
                            "풍속 km/h",
                            "시정 km",
                        ],
                    )
                    .format(
                        {
                            "관측 점수": "{:.0f}",
                            "전체 구름 %": "{:.0f}",
                            "하층 %": "{:.0f}",
                            "중층 %": "{:.0f}",
                            "상층 %": "{:.0f}",
                            "강수확률 %": "{:.0f}",
                            "습도 %": "{:.0f}",
                            "이슬점 °C": "{:.1f}",
                            "풍속 km/h": "{:.1f}",
                            "시정 km": "{:.1f}",
                        }
                    )
                )

                st.dataframe(
                    styled_table_df,
                    use_container_width=True,
                    hide_index=True,
                )

        show_hourly_weather_table()
    else:

        st.warning("오늘 밤 시간대의 날씨 데이터를 찾을 수 없습니다.")

    # --------------------------------------
    # 행성
    # --------------------------------------

    st.divider()
    st.header("🪐 현재 행성 관측 정보")

    with st.spinner("행성 위치를 계산하는 중..."):
        planet_df = engine.get_planets()

    visible_planets = planet_df[planet_df["관측"] == "✅ 관측 가능"]

    total_planets = len(planet_df)
    visible_count = len(visible_planets)

    st.markdown(
        """
        <style>
        .planet-summary-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 8px;
            margin-top: 8px;
            margin-bottom: 10px;
        }

        .planet-summary-card {
            border: 1px solid rgba(128, 128, 128, 0.30);
            border-radius: 14px;
            padding: 13px 10px;
            text-align: center;
        }

        .planet-summary-label {
            font-size: 13px;
            opacity: 0.8;
            margin-bottom: 5px;
        }

        .planet-summary-value {
            font-size: 24px;
            font-weight: 800;
        }

        .planet-recommendation {
            border: 1px solid rgba(128, 128, 128, 0.30);
            border-radius: 14px;
            padding: 11px 10px;
            text-align: center;
            font-size: 14px;
            font-weight: 700;
            margin-bottom: 14px;
        }

        @media (max-width: 768px) {

            .planet-summary-card {
                padding: 11px 7px;
            }

            .planet-summary-label {
                font-size: 12px;
            }

            .planet-summary-value {
                font-size: 22px;
            }

            .planet-recommendation {
                font-size: 13px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    planet_summary_html = (
        '<div class="planet-summary-grid">'
        '<div class="planet-summary-card">'
        '<div class="planet-summary-label">🪐 전체 행성</div>'
        f'<div class="planet-summary-value">{total_planets}개</div>'
        "</div>"
        '<div class="planet-summary-card">'
        '<div class="planet-summary-label">🔭 현재 관측 가능</div>'
        f'<div class="planet-summary-value">{visible_count}개</div>'
        "</div>"
        "</div>"
    )

    st.markdown(planet_summary_html, unsafe_allow_html=True)

    if visible_count > 0:

        visible_names = ", ".join(visible_planets["천체"].tolist())

        st.markdown(
            (
                '<div class="planet-recommendation">'
                f"🔭 현재 추천: {visible_names}"
                "</div>"
            ),
            unsafe_allow_html=True,
        )

    else:

        st.warning("현재 조건에서 고도 15° 이상인 " "관측 추천 행성이 없습니다.")

    with st.expander("📊 행성 상세 정보"):

        st.dataframe(planet_df, use_container_width=True, hide_index=True)
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
    # 별자리
    # --------------------------------------

    st.divider()
    st.header("✨ 현재 별자리 관측 정보")

    constellation_catalog = load_constellation_catalog()

    with st.spinner("별자리 위치를 계산하는 중..."):
        constellation_df = engine.get_constellations(constellation_catalog)

    current_month = datetime.now(KST).month

    if current_month in [3, 4, 5]:
        current_season = "봄"
        season_icon = "🌸"

    elif current_month in [6, 7, 8]:
        current_season = "여름"
        season_icon = "☀️"

    elif current_month in [9, 10, 11]:
        current_season = "가을"
        season_icon = "🍂"

    else:
        current_season = "겨울"
        season_icon = "❄️"

    visible_stars = constellation_df[constellation_df["관측 가능"] == True].copy()

    visible_constellations = visible_stars.drop_duplicates(subset=["별자리"]).copy()

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            f"{season_icon} 현재 계절",
            current_season,
        )

    with col2:
        st.metric(
            "👀 현재 관측 가능",
            f"{len(visible_constellations)}개",
        )

    with st.expander(
        "✨ 현재 보이는 별자리",
        expanded=False,
    ):
        if visible_stars.empty:
            st.info("현재 관측 가능한 별자리가 없습니다.")

        else:
            display_constellations = (
                visible_stars[
                    [
                        "계절",
                        "별자리",
                        "대표별",
                        "등급",
                        "고도 °",
                        "방위각 °",
                        "방향",
                    ]
                ]
                .sort_values(
                    by=[
                        "고도 °",
                        "등급",
                    ],
                    ascending=[
                        False,
                        True,
                    ],
                )
                .reset_index(drop=True)
            )

            st.dataframe(
                display_constellations,
                use_container_width=True,
                hide_index=True,
            )

    st.caption(
        "※ 별자리의 대표별이 고도 15° 이상이고 "
        "태양 고도가 -6° 이하일 때 현재 관측 가능으로 표시합니다."
    )

    # --------------------------------------
    # 달
    # --------------------------------------

    st.divider()
    st.header("🌙 현재 달 관측 정보")

    moon = engine.get_moon()

    moon_rise_set = engine.get_moon_rise_set()

    moonrise = moon_rise_set["월출"]
    moonset = moon_rise_set["월몰"]

    today_date = datetime.now(KST).date()

    if moonrise is not None:

        if moonrise.date() == today_date:
            moonrise_text = moonrise.strftime("%H:%M")

        else:
            moonrise_text = moonrise.strftime("%m/%d %H:%M")

    else:
        moonrise_text = "-"

    if moonset is not None:

        if moonset.date() == today_date:
            moonset_text = moonset.strftime("%H:%M")

        else:
            moonset_text = moonset.strftime("%m/%d %H:%M")

    else:
        moonset_text = "-"

    st.markdown(
        """
        <style>
        .moon-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
            margin-top: 8px;
            margin-bottom: 10px;
        }

        .moon-card {
            border: 1px solid rgba(128, 128, 128, 0.30);
            border-radius: 14px;
            padding: 13px 10px;
            text-align: center;
            min-width: 0;
        }

        .moon-label {
            font-size: 13px;
            opacity: 0.8;
            margin-bottom: 5px;
        }

        .moon-value {
            font-size: 22px;
            font-weight: 800;
            line-height: 1.2;
            overflow-wrap: anywhere;
        }

        .moon-phase-card {
            border: 1px solid rgba(128, 128, 128, 0.30);
            border-radius: 14px;
            padding: 11px 12px;
            text-align: center;
            font-size: 14px;
            line-height: 1.6;
            margin-bottom: 10px;
        }

                .moon-rise-set-line {
            text-align: center;

            font-size: 14px;
            font-weight: 600;

            padding: 4px 6px 10px 6px;

            opacity: 0.9;
        }

        @media (max-width: 768px) {

            .moon-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 8px;
            }

            .moon-card {
                padding: 11px 7px;
            }

            .moon-label {
                font-size: 12px;
            }

            .moon-value {
                font-size: 20px;
            }

            .moon-phase-card {
                font-size: 13px;
            }

                        .moon-rise-set-line {
                font-size: 13px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    moon_html = (
        '<div class="moon-grid">'
        '<div class="moon-card">'
        '<div class="moon-label">🌙 달 밝기</div>'
        f'<div class="moon-value">{moon["밝기"]:.1f}%</div>'
        "</div>"
        '<div class="moon-card">'
        '<div class="moon-label">⬆️ 현재 고도</div>'
        f'<div class="moon-value">{moon["고도"]:.1f}°</div>'
        "</div>"
        '<div class="moon-card">'
        '<div class="moon-label">🧭 방위각</div>'
        f'<div class="moon-value">{moon["방위각"]:.1f}°</div>'
        "</div>"
        '<div class="moon-card">'
        '<div class="moon-label">🧭 방향</div>'
        f'<div class="moon-value">{moon["방향"]}</div>'
        "</div>"
        '<div class="moon-card">'
        '<div class="moon-label">📏 거리</div>'
        f'<div class="moon-value">{moon["거리_km"]:,} km</div>'
        "</div>"
        '<div class="moon-card">'
        '<div class="moon-label">🌌 심우주 영향</div>'
        f'<div class="moon-value">{moon["달빛영향"]}</div>'
        "</div>"
        "</div>"
        '<div class="moon-phase-card">'
        f'🌙 <b>{moon["위상"]}</b>'
        f' · 위상각 {moon["위상각"]:.1f}°'
        f' · {moon["상태"]}'
        "</div>"
        '<div class="moon-rise-set-line">'
        f"🌙 월출 <b>{moonrise_text}</b>"
        f" &nbsp;·&nbsp; "
        f"🌑 월몰 <b>{moonset_text}</b>"
        "</div>"
    )

    st.markdown(moon_html, unsafe_allow_html=True)

    # --------------------------------------
    # 메시에 M1 ~ M110
    # --------------------------------------

    st.divider()
    st.header("🌌 메시에 관측 정보")

    messier_catalog = load_messier_catalog()

    with st.spinner("M1 ~ M110 위치와 관측 조건을 계산하는 중..."):
        messier_df = engine.get_messier_objects(
            messier_catalog,
            weather_score=average_score,
        )

    observable_df = messier_df[messier_df["추천점수"] > 0].copy()

    # ======================================
    # 오늘 밤 최적 관측시간
    # ======================================

    weather_timeline = build_half_hour_weather_timeline(night_df)

    with st.spinner("M1 ~ M110의 오늘 밤 최적 관측시간을 계산하는 중..."):

        messier_best_df = engine.get_messier_best_times(
            messier_catalog,
            weather_timeline,
        )

    tonight_messier = messier_best_df[messier_best_df["오늘 최고점수"] > 0].copy()

    # ======================================
    # 오늘 밤 행성 추천 점수 계산
    # ======================================

    planet_best_df = engine.get_planet_best_times(weather_timeline)

    # ======================================
    # 메시에 + 행성 통합 추천 목록
    # ======================================

    recommended_objects = []

    # 메시에 천체 추가
    for _, row in tonight_messier.iterrows():

        # 추천 관측시간이 없거나
        # 추천 기준 점수 미만이면 제외
        if row["추천 관측시간"] == "-" or int(row["오늘 최고점수"]) < 65:
            continue

        recommended_objects.append(
            {
                "분류": "메시에",
                "이름": (f"{row['메시에']} " f"{row['이름']}"),
                "종류": row["종류"],
                "추천 관측시간": (row["추천 관측시간"]),
                "최적 시각": (row["최적 시각"]),
                "최적 고도 °": (row["최적 고도 °"]),
                "방향": row["방향"],
                "오늘 최고점수": int(row["오늘 최고점수"]),
                "추천": row["추천"],
                "겉보기등급": row["등급"],
                "최적 시각 구름 %": row.get(
                    "최적 시각 구름 %",
                    None,
                ),
                "최적 시각 달 밝기 %": row.get(
                    "최적 시각 달 밝기 %",
                    None,
                ),
                "최적 시각 달 고도 °": row.get(
                    "최적 시각 달 고도 °",
                    None,
                ),
                "달과 각거리 °": row.get(
                    "달과 각거리 °",
                    None,
                ),
            }
        )

    # 행성 추가
    tonight_planets = pd.DataFrame()

    if not planet_best_df.empty and "오늘 최고점수" in planet_best_df.columns:
        tonight_planets = planet_best_df[planet_best_df["오늘 최고점수"] > 0].copy()

    for _, row in tonight_planets.iterrows():

        # 추천 관측시간이 없거나
        # 65점 미만이면 추천 대상에서 제외
        if row["추천 관측시간"] == "-" or int(row["오늘 최고점수"]) < 65:
            continue

        recommended_objects.append(
            {
                "분류": "행성",
                "이름": row["행성"],
                "종류": "행성",
                "추천 관측시간": (row["추천 관측시간"]),
                "최적 시각": (row["최적 시각"]),
                "최적 고도 °": (row["최적 고도 °"]),
                "방향": row["방향"],
                "오늘 최고점수": int(row["오늘 최고점수"]),
                "추천": row["추천"],
                "겉보기등급": None,
                "최적 시각 구름 %": row.get(
                    "최적 시각 구름 %",
                    None,
                ),
            }
        )

    # ======================================
    # 점수순 TOP 3
    # ======================================

    recommended_objects = sorted(
        recommended_objects,
        key=lambda item: item["오늘 최고점수"],
        reverse=True,
    )

    recommended_top3 = recommended_objects[:3]

    st.subheader("🌌 오늘 밤 추천 관측 대상")

    if recommended_top3:

        rank_icons = [
            "🥇",
            "🥈",
            "🥉",
        ]

        for index, item in enumerate(recommended_top3):

            with st.container(border=True):

                if item["분류"] == "행성":
                    title = f"🪐 {item['이름']}"
                else:
                    title = f"🌌 {item['이름']}"

                st.markdown(f"### {rank_icons[index]} " f"{title}")

                st.markdown(f"**{item['추천']} · " f"{item['오늘 최고점수']}점**")

                # ==================================
                # 실제 관측 조건 기반 추천 이유
                # ==================================

                reason_parts = []
                warning_parts = []

                best_altitude = float(item["최적 고도 °"])

                # 고도
                if best_altitude >= 60:
                    reason_parts.append("높은 고도")

                elif best_altitude >= 40:
                    reason_parts.append("양호한 고도")

                # ==================================
                # 메시에 천체
                # ==================================

                if item["분류"] == "메시에":

                    # 실제 최적 시각 구름량
                    cloud_value = item.get(
                        "최적 시각 구름 %",
                        None,
                    )

                    if cloud_value is not None and not pd.isna(cloud_value):
                        cloud_value = float(cloud_value)

                        if cloud_value <= 10:
                            reason_parts.append(f"구름 거의 없음({cloud_value:.0f}%)")

                        elif cloud_value <= 25:
                            reason_parts.append(f"구름 적음({cloud_value:.0f}%)")

                        elif cloud_value <= 40:
                            reason_parts.append(f"구름 비교적 적음({cloud_value:.0f}%)")

                    # 천체 밝기
                    magnitude = item.get(
                        "겉보기등급",
                        None,
                    )

                    if magnitude is not None and not pd.isna(magnitude):
                        magnitude = float(magnitude)

                        if magnitude <= 4:
                            reason_parts.append("밝은 천체")

                        elif magnitude <= 6:
                            reason_parts.append("비교적 밝은 천체")

                    # ==================================
                    # 달 상태
                    # ==================================

                    moon_brightness = item.get(
                        "최적 시각 달 밝기 %",
                        None,
                    )

                    moon_altitude = item.get(
                        "최적 시각 달 고도 °",
                        None,
                    )

                    moon_separation = item.get(
                        "달과 각거리 °",
                        None,
                    )

                    moon_data_valid = (
                        moon_brightness is not None
                        and moon_altitude is not None
                        and moon_separation is not None
                        and not pd.isna(moon_brightness)
                        and not pd.isna(moon_altitude)
                        and not pd.isna(moon_separation)
                    )

                    if moon_data_valid:

                        moon_brightness = float(moon_brightness)

                        moon_altitude = float(moon_altitude)

                        moon_separation = float(moon_separation)

                        if moon_altitude <= 0:
                            reason_parts.append("달 지평선 아래")

                        elif moon_brightness < 25:
                            reason_parts.append("달빛 약함")

                        elif moon_separation >= 70:
                            reason_parts.append("달과 멀리 떨어짐")

                        elif moon_separation < 40 and moon_brightness >= 40:
                            warning_parts.append("달과 가까워 대비 저하 가능")

                        elif moon_brightness >= 60 and moon_separation < 70:
                            warning_parts.append("밝은 달 영향 있음")

                # ==================================
                # 목성 / 토성
                # ==================================

                elif item["분류"] == "행성":

                    cloud_value = item.get(
                        "최적 시각 구름 %",
                        None,
                    )

                    if cloud_value is not None and not pd.isna(cloud_value):
                        cloud_value = float(cloud_value)

                        if cloud_value <= 10:
                            reason_parts.append(f"구름 거의 없음({cloud_value:.0f}%)")

                        elif cloud_value <= 25:
                            reason_parts.append(f"구름 적음({cloud_value:.0f}%)")

                    reason_parts.append("행성 관측에 유리")

                if reason_parts:
                    st.write("💡 추천 이유 : " + " · ".join(reason_parts))

                if warning_parts:
                    st.write("⚠️ 주의 : " + " · ".join(warning_parts))

                st.write(f"🔭 종류 : " f"{item['종류']}")

                st.write(f"⏰ 추천 시간 : " f"{item['추천 관측시간']}")

                st.write(f"✨ 최적 시각 : " f"{item['최적 시각']}")

                st.write(f"📐 최적 고도 : " f"{item['최적 고도 °']}°")

                st.write(f"🧭 방향 : " f"{item['방향']}")

                if item["분류"] == "메시에":
                    st.write(f"👁️ 겉보기등급 : " f"{item['겉보기등급']}")

    else:

        st.info("오늘 밤 추천할 수 있는 " "관측 대상이 없습니다.")

        # ======================================
    # 오늘 밤 메시에 최적 관측시간 TOP 10
    # ======================================

    if len(tonight_messier) > 0:

        with st.expander("⏰ 오늘 밤 메시에 최적 관측시간 TOP 10"):

            st.caption(
                "30분 간격의 날씨 점수, 천체 고도, "
                "달 밝기·각거리, 겉보기등급을 함께 계산합니다."
            )

            st.dataframe(
                tonight_messier.head(10),
                use_container_width=True,
                hide_index=True,
            )

    else:

        st.info(
            "🌙 오늘 밤은 달빛·날씨·천체 고도 조건을 "
            "충족하는 메시에 추천 대상이 없습니다."
        )

    # ======================================
    # 전체 목록
    # ======================================

    with st.expander(
        "🔎 M1 ~ M110 전체 목록",
        expanded=False,
    ):

        filter_col1, filter_col2 = st.columns(2)

        only_observable = filter_col1.checkbox(
            "현재 관측 가능한 천체만",
            value=True,
        )

        type_options = ["전체"] + sorted(messier_df["종류"].dropna().unique().tolist())

        selected_type = filter_col2.selectbox(
            "천체 종류",
            type_options,
        )

        display_messier = messier_df.copy()

        if only_observable:
            display_messier = display_messier[display_messier["추천점수"] > 0]

        if selected_type != "전체":
            display_messier = display_messier[display_messier["종류"] == selected_type]

        st.dataframe(
            display_messier,
            use_container_width=True,
            hide_index=True,
        )

        st.caption(
            "※ 메시에 추천점수는 동아리용 경험식이며 "
            "실제 관측 환경에 따라 차이가 있을 수 있습니다."
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
