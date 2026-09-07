import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from skyfield import almanac
from skyfield.api import Star, load, wgs84


KST = ZoneInfo("Asia/Seoul")

PLANETS = {
    "수성": "mercury",
    "금성": "venus",
    "화성": "mars",
    "목성": "jupiter barycenter",
    "토성": "saturn barycenter",
    "천왕성": "uranus barycenter",
    "해왕성": "neptune barycenter",
}

MESSIER_TYPE_KO = {
    "OC": "산개성단",
    "GC": "구상성단",
    "PN": "행성상성운",
    "DN": "성운",
    "AS": "성군",
    "DS": "이중성",
    "MW": "은하수 별구름",
    "SG": "나선은하",
    "BG": "막대나선은하",
    "LG": "렌즈형은하",
    "EG": "타원은하",
    "IG": "불규칙은하",
    "SN": "초신성 잔해",
}

MESSIER_KOREAN_NAMES = {
    "M1": "게 성운",
    "M6": "나비 성단",
    "M7": "프톨레마이오스 성단",
    "M8": "석호 성운",
    "M11": "들오리 성단",
    "M13": "헤르쿨레스 대성단",
    "M16": "독수리 성운",
    "M17": "오메가 성운",
    "M20": "삼렬 성운",
    "M22": "사수자리 성단",
    "M24": "사수자리 별구름",
    "M27": "아령 성운",
    "M31": "안드로메다 은하",
    "M33": "삼각형자리 은하",
    "M40": "위네케 4",
    "M42": "오리온 대성운",
    "M43": "드 메랑 성운",
    "M44": "벌집 성단",
    "M45": "플레이아데스 성단",
    "M51": "소용돌이 은하",
    "M57": "고리 성운",
    "M63": "해바라기 은하",
    "M64": "검은눈 은하",
    "M76": "작은 아령 성운",
    "M81": "보데 은하",
    "M82": "시가 은하",
    "M83": "남쪽 바람개비 은하",
    "M97": "올빼미 성운",
    "M101": "바람개비 은하",
    "M104": "솜브레로 은하",
}


def azimuth_to_direction(azimuth):
    directions = ["북", "북동", "동", "남동", "남", "남서", "서", "북서"]
    return directions[round(azimuth / 45) % 8]


def moon_phase_name(phase):
    if phase < 22.5 or phase >= 337.5:
        return "🌑 삭"
    if phase < 67.5:
        return "🌒 초승달"
    if phase < 112.5:
        return "🌓 상현달"
    if phase < 157.5:
        return "🌔 차오르는 달"
    if phase < 202.5:
        return "🌕 보름달"
    if phase < 247.5:
        return "🌖 기우는 달"
    if phase < 292.5:
        return "🌗 하현달"
    return "🌘 그믐달"


def moonlight_effect(illumination, altitude):
    if altitude < 0:
        return "🟢 거의 없음"
    if illumination < 20:
        return "🟢 매우 낮음"
    if illumination < 40:
        return "🟢 낮음"
    if illumination < 60:
        return "🟡 보통"
    if illumination < 80:
        return "🟠 높음"
    return "🔴 매우 높음"


def parse_ra_hours(text):
    """Messier JSON의 '5h 34.5m' 같은 RA 문자열을 시간 단위 실수로 변환."""
    hours_match = re.search(r"([0-9.]+)\s*h", text)
    minutes_match = re.search(r"([0-9.]+)\s*m", text)
    seconds_match = re.search(r"([0-9.]+)\s*s", text)

    hours = float(hours_match.group(1)) if hours_match else 0.0
    minutes = float(minutes_match.group(1)) if minutes_match else 0.0
    seconds = float(seconds_match.group(1)) if seconds_match else 0.0
    return hours + minutes / 60.0 + seconds / 3600.0


def parse_dec_degrees(text):
    """Messier JSON의 '+22° 01′' 같은 Dec 문자열을 도 단위 실수로 변환."""
    sign = -1.0 if text.strip().startswith("-") else 1.0
    cleaned = text.replace("−", "-")

    deg_match = re.search(r"([0-9.]+)\s*°", cleaned)
    min_match = re.search(r"([0-9.]+)\s*[′']", cleaned)
    sec_match = re.search(r"([0-9.]+)\s*[″\"]", cleaned)

    degrees = float(deg_match.group(1)) if deg_match else 0.0
    minutes = float(min_match.group(1)) if min_match else 0.0
    seconds = float(sec_match.group(1)) if sec_match else 0.0
    return sign * (degrees + minutes / 60.0 + seconds / 3600.0)


def score_grade(score):
    if score >= 90:
        return "★★★★★"
    if score >= 80:
        return "★★★★☆"
    if score >= 65:
        return "★★★☆☆"
    if score >= 45:
        return "★★☆☆☆"
    return "★☆☆☆☆"


def _brightness_score(magnitude):
    # 겉보기등급은 확장천체끼리 완전히 동일한 난이도 척도는 아니므로 비중을 낮게 사용한다.
    return max(10.0, min(100.0, 100.0 - max(0.0, magnitude - 2.0) * 9.0))


def _altitude_score(altitude):
    if altitude <= 10:
        return 0.0
    return max(0.0, min(100.0, (altitude - 10.0) / 50.0 * 100.0))


def _moon_sensitivity(type_code):
    return {
        "SG": 1.00,
        "BG": 1.00,
        "LG": 1.00,
        "EG": 1.00,
        "IG": 1.00,
        "DN": 0.90,
        "SN": 0.80,
        "MW": 0.70,
        "PN": 0.50,
        "GC": 0.40,
        "OC": 0.25,
        "AS": 0.10,
        "DS": 0.10,
    }.get(type_code, 0.50)


def _moon_separation_factor(separation_deg):
    if separation_deg < 20:
        return 1.00
    if separation_deg < 40:
        return 0.75
    if separation_deg < 70:
        return 0.50
    return 0.25


class AstronomyEngine:

    def __init__(self, latitude, longitude):

        self.latitude = latitude
        self.longitude = longitude

        self.ts = load.timescale()
        self.eph = load("de421.bsp")

        self.earth = self.eph["earth"]
        self.sun = self.eph["sun"]
        self.moon = self.eph["moon"]

        self.topos = wgs84.latlon(
            latitude_degrees=latitude,
            longitude_degrees=longitude
        )

        self.observer = (
            self.earth
            + self.topos
        )


    def get_sun_altitude(self, t):

        apparent = (
            self.observer
            .at(t)
            .observe(self.sun)
            .apparent()
        )

        altitude, _, _ = apparent.altaz()

        return altitude.degrees


    def get_astronomical_night(self, date_str):

        local_noon = (
            datetime.strptime(
                date_str,
                "%Y-%m-%d"
            )
            .replace(
                hour=12,
                minute=0,
                second=0,
                microsecond=0,
                tzinfo=KST
            )
        )

        next_noon = (
            local_noon
            + timedelta(days=1)
        )

        t0 = self.ts.from_datetime(
            local_noon
        )

        t1 = self.ts.from_datetime(
            next_noon
        )

        twilight_function = (
            almanac.dark_twilight_day(
                self.eph,
                self.topos
            )
        )

        times, events = (
            almanac.find_discrete(
                t0,
                t1,
                twilight_function
            )
        )

        previous_state = int(
            twilight_function(t0).item()
        )

        astronomical_night_start = None
        astronomical_night_end = None

        for t, event in zip(
            times,
            events
        ):

            new_state = int(event)

            local_time = t.astimezone(KST)

            if (
                previous_state == 1
                and new_state == 0
            ):
                astronomical_night_start = local_time

            elif (
                previous_state == 0
                and new_state == 1
            ):
                astronomical_night_end = local_time

            previous_state = new_state

        return (
            astronomical_night_start,
            astronomical_night_end
        )


    def get_planets(self):
        now = datetime.now(KST)
        t = self.ts.from_datetime(now)
        sun_alt = self.get_sun_altitude(t)
        results = []

        for korean_name, skyfield_name in PLANETS.items():
            planet = self.eph[skyfield_name]
            apparent = self.observer.at(t).observe(planet).apparent()
            altitude, azimuth, distance = apparent.altaz()

            alt = altitude.degrees
            az = azimuth.degrees

            if alt < 0:
                position_status = "지평선 아래"
            elif alt < 15:
                position_status = "매우 낮음"
            elif alt < 30:
                position_status = "낮음"
            elif alt < 60:
                position_status = "좋음"
            else:
                position_status = "매우 좋음"

            if alt >= 15 and sun_alt <= -6:
                observation_text = "✅ 관측 가능"
            elif alt < 0:
                observation_text = "❌ 지평선 아래"
            elif alt < 15:
                observation_text = "⚠️ 고도가 너무 낮음"
            elif sun_alt > -6:
                observation_text = "☀️ 아직 하늘이 밝음"
            else:
                observation_text = "⚠️ 관측 조건 확인"

            results.append(
                {
                    "천체": korean_name,
                    "고도 °": round(alt, 1),
                    "방위각 °": round(az, 1),
                    "방향": azimuth_to_direction(az),
                    "상태": position_status,
                    "관측": observation_text,
                    "거리 AU": round(distance.au, 3),
                }
            )

        df = pd.DataFrame(results)
        return df.sort_values(by="고도 °", ascending=False).reset_index(drop=True)

    def get_moon_at_time(self, target_datetime):

        if target_datetime.tzinfo is None:
            target_datetime = target_datetime.replace(
                tzinfo=KST
            )

        t = self.ts.from_datetime(
            target_datetime
        )

        apparent = (
            self.observer
            .at(t)
            .observe(self.moon)
            .apparent()
        )

        altitude, azimuth, distance = apparent.altaz()

        illumination = (
            almanac.fraction_illuminated(
                self.eph,
                "moon",
                t
            )
            * 100
        )

        return {
            "밝기": round(illumination, 1),
            "고도": round(
                altitude.degrees,
                1
            ),
            "방위각": round(
                azimuth.degrees,
                1
            )
        }

    def get_moon(self):
        now = datetime.now(KST)
        t = self.ts.from_datetime(now)
        apparent = self.observer.at(t).observe(self.moon).apparent()
        altitude, azimuth, distance = apparent.altaz()

        alt = altitude.degrees
        az = azimuth.degrees
        phase_angle = almanac.moon_phase(self.eph, t).degrees
        illumination = almanac.fraction_illuminated(self.eph, "moon", t) * 100

        if alt < 0:
            status = "지평선 아래"
        elif alt < 15:
            status = "매우 낮음"
        elif alt < 30:
            status = "낮음"
        elif alt < 60:
            status = "좋음"
        else:
            status = "매우 높음"

        return {
            "고도": round(alt, 1),
            "방위각": round(az, 1),
            "방향": azimuth_to_direction(az),
            "거리_km": round(distance.km),
            "밝기": round(illumination, 1),
            "위상각": round(phase_angle, 1),
            "위상": moon_phase_name(phase_angle),
            "상태": status,
            "달빛영향": moonlight_effect(illumination, alt),
        }

    @staticmethod
    def _ensure_kst(dt):
        """naive datetime은 KST로 간주하고, aware datetime은 KST로 변환한다."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=KST)
        return dt.astimezone(KST)

    @staticmethod
    def _datetime_range(start_dt, end_dt, step_minutes=10):
        values = []
        current = start_dt
        step = timedelta(minutes=step_minutes)
        while current <= end_dt:
            values.append(current)
            current += step
        return values

    @staticmethod
    def _mask_runs(mask):
        runs = []
        start = None
        for i, flag in enumerate(mask):
            if bool(flag) and start is None:
                start = i
            elif not bool(flag) and start is not None:
                runs.append((start, i - 1))
                start = None
        if start is not None:
            runs.append((start, len(mask) - 1))
        return runs

    @staticmethod
    def _fmt_time(dt):
        if dt is None:
            return "-"
        return dt.astimezone(KST).strftime("%m/%d %H:%M")

    def get_planet_night_schedule(
        self,
        night_start,
        night_end,
        step_minutes=5,
        min_altitude=15.0,
    ):
        """오늘 밤 행성의 출·남중·몰과 실제 추천 관측시간을 계산한다."""
        night_start = self._ensure_kst(night_start)
        night_end = self._ensure_kst(night_end)

        # 출/몰까지 잡기 위해 관측 밤 앞뒤를 조금 넓게 계산한다.
        search_start = night_start - timedelta(hours=8)
        search_end = night_end + timedelta(hours=8)
        times = self._datetime_range(search_start, search_end, step_minutes)
        sky_times = self.ts.from_datetimes(times)
        observer_at = self.observer.at(sky_times)

        sun_alt = np.asarray(
            observer_at.observe(self.sun).apparent().altaz()[0].degrees,
            dtype=float,
        )

        night_mask = np.asarray(
            [(dt >= night_start and dt <= night_end) for dt in times],
            dtype=bool,
        )
        midpoint = night_start + (night_end - night_start) / 2

        rows = []

        for korean_name, skyfield_name in PLANETS.items():
            planet = self.eph[skyfield_name]
            apparent = observer_at.observe(planet).apparent()
            alt = np.asarray(apparent.altaz()[0].degrees, dtype=float)

            # 출/몰: 고도 0° 교차점. 5분 간격이므로 시각 오차는 대략 몇 분 수준이다.
            rise_idx = np.where((alt[:-1] < 0.0) & (alt[1:] >= 0.0))[0] + 1
            set_idx = np.where((alt[:-1] >= 0.0) & (alt[1:] < 0.0))[0] + 1

            # 남중 후보는 고도 국소 최대값 중 오늘 밤 중앙에 가장 가까운 것으로 선택한다.
            local_max = np.where(
                (alt[1:-1] >= alt[:-2]) & (alt[1:-1] > alt[2:])
            )[0] + 1

            if len(local_max) > 0:
                transit_idx = min(
                    local_max,
                    key=lambda i: abs((times[int(i)] - midpoint).total_seconds()),
                )
            else:
                transit_idx = int(np.argmax(alt))

            rise_before = rise_idx[rise_idx <= transit_idx]
            set_after = set_idx[set_idx >= transit_idx]

            rise_time = times[int(rise_before[-1])] if len(rise_before) else None
            set_time = times[int(set_after[0])] if len(set_after) else None
            transit_time = times[int(transit_idx)]

            observable = (
                night_mask
                & (alt >= float(min_altitude))
                & (sun_alt <= -6.0)
            )

            runs = self._mask_runs(observable)
            if runs:
                # 최고 고도를 포함하는 관측 가능 구간을 우선 선택한다.
                observable_indices = np.where(observable)[0]
                best_idx = int(observable_indices[np.argmax(alt[observable])])
                selected = next(
                    ((s, e) for s, e in runs if s <= best_idx <= e),
                    runs[0],
                )
                s, e = selected
                window_start = times[s]
                window_end = min(
                    night_end,
                    times[e] + timedelta(minutes=step_minutes),
                )
                best_time = times[best_idx]
                best_alt = float(alt[best_idx])
                window_text = (
                    f"{window_start.strftime('%H:%M')} ~ "
                    f"{window_end.strftime('%H:%M')}"
                )
                best_text = best_time.strftime("%H:%M")
            else:
                best_alt = float(np.max(alt[night_mask])) if np.any(night_mask) else float(np.max(alt))
                window_text = "-"
                best_text = "-"

            rows.append(
                {
                    "행성": korean_name,
                    "출": self._fmt_time(rise_time),
                    "남중": self._fmt_time(transit_time),
                    "몰": self._fmt_time(set_time),
                    "오늘밤 최고고도 °": round(best_alt, 1),
                    "관측 가능 시간": window_text,
                    "최적 시각": best_text,
                }
            )

        df = pd.DataFrame(rows)
        return df.sort_values(
            by="오늘밤 최고고도 °",
            ascending=False,
        ).reset_index(drop=True)

    def get_messier_best_times(self, catalog, weather_timeline):
        """시간대별 날씨와 천체 고도/달빛을 합쳐 M1~M110의 오늘 밤 최적 시간을 계산한다."""
        if not weather_timeline:
            return pd.DataFrame()

        times = [self._ensure_kst(item["time"]) for item in weather_timeline]
        weather_scores = np.asarray(
            [float(item["score"]) for item in weather_timeline],
            dtype=float,
        )

        sky_times = self.ts.from_datetimes(times)
        observer_at = self.observer.at(sky_times)

        sun_alt = np.asarray(
            observer_at.observe(self.sun).apparent().altaz()[0].degrees,
            dtype=float,
        )

        moon_apparent = observer_at.observe(self.moon).apparent()
        moon_alt = np.asarray(moon_apparent.altaz()[0].degrees, dtype=float)
        moon_phase = np.asarray(almanac.moon_phase(self.eph, sky_times).radians, dtype=float)
        moon_illumination = 0.5 * (1.0 - np.cos(moon_phase)) * 100.0

        if len(times) >= 2:
            step_minutes = max(
                1,
                round((times[1] - times[0]).total_seconds() / 60),
            )
        else:
            step_minutes = 30

        objects = catalog.get("objects", catalog) if isinstance(catalog, dict) else catalog
        rows = []

        for obj in objects:
            ra_hours = parse_ra_hours(obj["RA"])
            dec_degrees = parse_dec_degrees(obj["Dec"])
            target = Star(ra_hours=ra_hours, dec_degrees=dec_degrees)

            apparent = observer_at.observe(target).apparent()
            altitude, azimuth, _ = apparent.altaz()
            alt = np.asarray(altitude.degrees, dtype=float)
            az = np.asarray(azimuth.degrees, dtype=float)
            separation = np.asarray(
                apparent.separation_from(moon_apparent).degrees,
                dtype=float,
            )

            magnitude = float(obj.get("V", 10.0))
            type_code = obj.get("T", "")

            altitude_scores = np.clip((alt - 10.0) / 50.0 * 100.0, 0.0, 100.0)
            brightness_score = _brightness_score(magnitude)

            moon_factor = np.where(
                separation < 20.0,
                1.00,
                np.where(
                    separation < 40.0,
                    0.75,
                    np.where(separation < 70.0, 0.50, 0.25),
                ),
            )

            moon_penalty = np.where(
                moon_alt > 0.0,
                (moon_illumination / 100.0)
                * 35.0
                * _moon_sensitivity(type_code)
                * moon_factor,
                0.0,
            )

            raw_scores = (
                weather_scores * 0.45
                + altitude_scores * 0.40
                + brightness_score * 0.15
                - moon_penalty
            )

            observable = (alt >= 15.0) & (sun_alt <= -6.0)
            final_scores = np.clip(raw_scores, 0.0, 100.0)
            final_scores = np.where(observable, final_scores, 0.0)

            if np.max(final_scores) <= 0.0:
                best_score = 0
                best_time_text = "-"
                best_alt_text = "-"
                best_direction = "-"
                window_text = "-"
            else:
                best_idx = int(np.argmax(final_scores))
                best_score = round(float(final_scores[best_idx]))
                best_time_text = times[best_idx].strftime("%H:%M")
                best_alt_text = round(float(alt[best_idx]), 1)
                best_direction = azimuth_to_direction(float(az[best_idx]))

                # 최고점수에서 크게 떨어지지 않는 시간대를 추천 구간으로 묶는다.
                threshold = max(45.0, float(final_scores[best_idx]) - 12.0)
                good_mask = observable & (final_scores >= threshold)
                runs = self._mask_runs(good_mask)
                selected = next(
                    ((s, e) for s, e in runs if s <= best_idx <= e),
                    None,
                )

                if selected:
                    s, e = selected
                    end_time = times[e] + timedelta(minutes=step_minutes)
                    window_text = (
                        f"{times[s].strftime('%H:%M')} ~ "
                        f"{end_time.strftime('%H:%M')}"
                    )
                else:
                    window_text = best_time_text

            messier_id = obj["M"]
            common_name = MESSIER_KOREAN_NAMES.get(messier_id, obj.get("N", ""))

            rows.append(
                {
                    "메시에": messier_id,
                    "이름": common_name,
                    "종류": MESSIER_TYPE_KO.get(type_code, type_code),
                    "등급": magnitude,
                    "최적 시각": best_time_text,
                    "최적 고도 °": best_alt_text,
                    "방향": best_direction,
                    "추천 관측시간": window_text,
                    "오늘 최고점수": best_score,
                    "추천": score_grade(best_score) if best_score > 0 else "-",
                }
            )

        df = pd.DataFrame(rows)
        return df.sort_values(
            by=["오늘 최고점수", "등급"],
            ascending=[False, True],
        ).reset_index(drop=True)

    def get_messier_objects(self, catalog, weather_score=70):
        """현재 위치/시각 기준 M1~M110의 고도·방위각·추천점수를 계산한다."""
        now = datetime.now(KST)
        t = self.ts.from_datetime(now)
        observer_at_t = self.observer.at(t)
        sun_alt = self.get_sun_altitude(t)

        moon_apparent = observer_at_t.observe(self.moon).apparent()
        moon_altitude, _, _ = moon_apparent.altaz()
        moon_alt = moon_altitude.degrees
        moon_illumination = almanac.fraction_illuminated(self.eph, "moon", t) * 100

        objects = catalog.get("objects", catalog) if isinstance(catalog, dict) else catalog
        rows = []

        for obj in objects:
            ra_hours = parse_ra_hours(obj["RA"])
            dec_degrees = parse_dec_degrees(obj["Dec"])
            target = Star(ra_hours=ra_hours, dec_degrees=dec_degrees)

            apparent = observer_at_t.observe(target).apparent()
            altitude, azimuth, _ = apparent.altaz()
            alt = altitude.degrees
            az = azimuth.degrees
            separation = apparent.separation_from(moon_apparent).degrees

            magnitude = float(obj.get("V", 10.0))
            type_code = obj.get("T", "")

            altitude_score = _altitude_score(alt)
            brightness_score = _brightness_score(magnitude)

            moon_penalty = 0.0
            if moon_alt > 0:
                moon_penalty = (
                    (moon_illumination / 100.0)
                    * 35.0
                    * _moon_sensitivity(type_code)
                    * _moon_separation_factor(separation)
                )

            raw_score = (
                float(weather_score) * 0.45
                + altitude_score * 0.40
                + brightness_score * 0.15
                - moon_penalty
            )

            # 실제 추천 목록은 최소 고도 15° + 시민박명 종료 이후만 인정한다.
            observable = alt >= 15 and sun_alt <= -6
            final_score = round(max(0.0, min(100.0, raw_score))) if observable else 0

            if alt < 0:
                observation = "❌ 지평선 아래"
            elif alt < 15:
                observation = "⚠️ 고도 낮음"
            elif sun_alt > -6:
                observation = "☀️ 하늘이 밝음"
            else:
                observation = "✅ 관측 가능"

            messier_id = obj["M"]
            common_name = MESSIER_KOREAN_NAMES.get(messier_id, obj.get("N", ""))

            rows.append(
                {
                    "메시에": messier_id,
                    "이름": common_name,
                    "NGC/IC": obj.get("NGC", "-"),
                    "종류": MESSIER_TYPE_KO.get(type_code, type_code),
                    "등급": magnitude,
                    "크기(분각)": obj.get("S", "-"),
                    "고도 °": round(alt, 1),
                    "방위각 °": round(az, 1),
                    "방향": azimuth_to_direction(az),
                    "달과 각거리 °": round(separation, 1),
                    "관측": observation,
                    "추천점수": final_score,
                    "추천": score_grade(final_score) if final_score > 0 else "-",
                }
            )

        df = pd.DataFrame(rows)
        return df.sort_values(
            by=["추천점수", "고도 °"],
            ascending=[False, False],
        ).reset_index(drop=True)
