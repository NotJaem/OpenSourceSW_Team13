import json
import requests
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

NAVER_CLIENT_ID = 'x32e45dhiv'      # <-- NAVER API Client ID 입력
NAVER_CLIENT_SECRET = 'WgPseVxDKg8NYjVcxdOFmOTtIzTnf98ffnIauAYu'  # <-- NAVER API Client Secret 입력



# 도로명 주소 기반 지명
ORIGIN_NAME = "경기도 용인시 수지구 죽전로 152"
DESTINATION_NAME = "경기도 용인시 수지구 포은대로 536"
WAYPOINT_NAME_LIST = [
    "경기도 용인시 수지구 죽전동 1442",
    "경기도 용인시 기흥구 보정동 1353"
]

# JSON 시간 데이터를 datetime 리스트로 변환
with open('schedule.json', 'r') as f:
    raw_schedule = json.load(f)
    now = datetime.now()
    SCHEDULE = sorted([
        datetime.strptime(t, '%H:%M').replace(year=now.year, month=now.month, day=now.day)
        for t in raw_schedule
    ])


def get_coordinates_from_name(place_name):
    url = 'https://maps.apigw.ntruss.com/map-geocode/v2/geocode'
    headers = {
        'X-NCP-APIGW-API-KEY-ID': NAVER_CLIENT_ID,
        'X-NCP-APIGW-API-KEY': NAVER_CLIENT_SECRET
    }
    params = {'query': place_name}
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    if 'addresses' not in data or not data['addresses']:
        raise Exception(f'지명 "{place_name}"에 대한 좌표를 찾을 수 없습니다.')
    addr = data['addresses'][0]
    return f"{addr['x']},{addr['y']}"


try:
    ORIGIN = get_coordinates_from_name(ORIGIN_NAME)
    DESTINATION = get_coordinates_from_name(DESTINATION_NAME)
    DEFAULT_WAYPOINTS = [get_coordinates_from_name(name) for name in WAYPOINT_NAME_LIST]
except Exception as e:
    print("지오코딩 실패:", e)
    exit(1)


@app.route('/predict-arrival', methods=['POST'])
def predict_arrival():
    try:
        user_input = request.get_json()
        arrival_str = user_input.get('arrival_time')
        arrival_time = datetime.strptime(arrival_str, '%H:%M').replace(
            year=datetime.now().year, month=datetime.now().month, day=datetime.now().day)

        # 출발 후보(과거 2개 + 미래 1개) 선택
        candidate_departures = [t for t in SCHEDULE if t <= arrival_time]
        past_two = candidate_departures[-2:] if len(candidate_departures) >= 2 else candidate_departures
        future_one = [t for t in SCHEDULE if t > arrival_time][:1]
        selected_candidates = past_two + future_one

        if not selected_candidates:
            return jsonify({'status': 'no_bus', 'message': '후보 셔틀이 없습니다.'})

        valid_results = []

        for dep in selected_candidates:
            try:
                travel_time_sec, route = get_travel_duration_and_route(
                    ORIGIN, DESTINATION, DEFAULT_WAYPOINTS
                )
                predicted_arrival = dep + timedelta(seconds=travel_time_sec)

                # ———— doyun 쪽 로직 유지 ————
                # predicted_arrival이 arrival_time보다 작거나 같으면 다음 후보로
                if predicted_arrival <= arrival_time:
                    continue

                # 경과 시간, 진행률, ETA 계산
                elapsed = (arrival_time - dep).total_seconds()
                progress = min(max(elapsed / travel_time_sec, 0), 1.0)

                remaining_sec = (predicted_arrival - arrival_time).total_seconds()
                eta_minutes = remaining_sec / 60.0

                # progress가 0인 경우 (아직 출발 전) → 제외
                if progress == 0:
                    continue

                # progress가 1.0 이면서 ETA < -2분인 경우 (이미 종점 도착 후 2분 이상 경과) → 제외
                if progress == 1.0 and eta_minutes < -2:
                    continue
                # ————————————————

                # 경로(path) 정보 유효성 검사
                path = route.get('path')
                if not path or len(path) < 2:
                    continue

                # 보간(interpolation)으로 현재 위치 계산
                index_float = progress * (len(path) - 1)
                lower_index = int(index_float)
                upper_index = min(lower_index + 1, len(path) - 1)
                ratio = index_float - lower_index

                x1, y1 = path[lower_index]
                x2, y2 = path[upper_index]
                lng = x1 + (x2 - x1) * ratio
                lat = y1 + (y2 - y1) * ratio

                # 결과 항목 생성 및 valid_results에 추가
                result_item = {
                    'departure_time': dep.strftime('%H:%M'),
                    'predicted_arrival': predicted_arrival.strftime('%H:%M'),
                    'eta_minutes': round(eta_minutes, 1),
                    'current_location': {'lat': lat, 'lng': lng},
                    'progress': round(progress * 100, 1)
                }
                valid_results.append(result_item)

            except Exception as e:
                print(f'  - dep={dep.strftime("%H:%M")} 처리 중 오류: {e}')
                continue

        if not valid_results:
            return jsonify({'status': 'no_bus', 'message': '운행 가능한 셔틀이 없습니다.'})

        return jsonify({'status': 'ok', 'results': valid_results})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})  


def get_travel_duration_and_route(origin, destination, waypoints):
    url = 'https://maps.apigw.ntruss.com/map-direction/v1/driving'
    headers = {
        'X-NCP-APIGW-API-KEY-ID': NAVER_CLIENT_ID,
        'X-NCP-APIGW-API-KEY': NAVER_CLIENT_SECRET
    }
    params = {
        'start': origin,
        'goal': destination,
        'waypoints': '|'.join(waypoints),
        'option': 'trafast'
    }

    response = requests.get(url, headers=headers, params=params)
    data = response.json()

    if data.get('code') != 0:
        raise Exception('NAVER API 호출 실패: ' + data.get('message', '') + ' / 응답 전문: ' + json.dumps(data))

    route = data['route']['trafast'][0]
    duration = route['summary']['duration'] / 1000  # ms -> sec

    return duration, route


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, port=5001)
