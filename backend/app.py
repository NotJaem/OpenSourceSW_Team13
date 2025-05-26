import json
import requests  # HTTP 요청을 보내기 위한 외부 라이브러리
from flask import Flask, request, jsonify  # Flask는 웹 서버 프레임워크이며 request는 요청, jsonify는 JSON 응답 반환용
from datetime import datetime, timedelta  # 시간 계산을 위한 모듈
from flask_cors import CORS  # 다른 도메인에서 접근할 수 있도록 CORS 허용

app = Flask(__name__)  # Flask 앱 인스턴스 생성
CORS(app)  # 프론트엔드와 연동 시 CORS 문제 방지

GOOGLE_API_KEY = 'YOUR_ACTUAL_API_KEY_HERE'  # 실제 Google Maps API 키를 입력하세요

# json 파일 열기
with open('schedule.json', 'r') as f:
    SCHEDULE = json.load(f)

# 좌표에서 공백 제거
ORIGIN = '37.320184325358106,127.12881179384267'  # 단국대.평화의 광장 버스 정류장
DESTINATION = '37.32410071639112,127.10706291491555'  # 죽전역.신세계사우스시티 버스 정류장
WAYPOINTS = []  # 필요 시 경유지 추가

@app.route('/predict-arrival', methods=['POST'])
def predict_arrival():
    try:
        user_input = request.get_json()
        arrival_str = user_input.get('arrival_time')
        
        if not arrival_str:
            return jsonify({'status': 'error', 'message': '도착 시간을 입력해주세요.'})
        
        # 현재 시간 기준으로 처리
        now = datetime.now()
        
        try:
            arrival_time = datetime.strptime(arrival_str, '%H:%M')
            arrival_time = arrival_time.replace(year=now.year, month=now.month, day=now.day)
        except ValueError:
            return jsonify({'status': 'error', 'message': '올바른 시간 형식(HH:MM)을 입력해주세요.'})

        # 전체 시간 리스트 정렬
        all_departures = []
        for t in SCHEDULE:
            try:
                dep_time = datetime.strptime(t, '%H:%M')
                dep_time = dep_time.replace(year=now.year, month=now.month, day=now.day)
                all_departures.append(dep_time)
            except ValueError:
                continue  # 잘못된 형식의 시간은 건너뛰기
        
        all_departures = sorted(all_departures)
        
        if not all_departures:
            return jsonify({'status': 'error', 'message': '유효한 셔틀버스 시간표가 없습니다.'})

        # 사용자 도착 시간에 맞는 셔틀버스 찾기
        current_time = now
        valid_candidates = []
        
        for dep_time in all_departures:
            # 아직 출발하지 않은 버스만 고려
            if dep_time >= current_time:
                try:
                    # 예상 소요 시간 계산
                    travel_time_sec, _ = get_travel_duration_and_route(dep_time)
                    predicted_arrival = dep_time + timedelta(seconds=travel_time_sec)
                    
                    # 셔틀버스가 사용자 도착 시간 이후에 도착하는 경우만 유효
                    if predicted_arrival >= arrival_time:
                        valid_candidates.append(dep_time)
                        
                    # 최대 3개까지만 선택
                    if len(valid_candidates) >= 3:
                        break
                        
                except Exception:
                    # API 오류 시에도 후보에 포함 (나중에 처리)
                    valid_candidates.append(dep_time)
                    if len(valid_candidates) >= 3:
                        break
        
        if not valid_candidates:
            return jsonify({'status': 'no_bus', 'message': '사용자 도착 시간에 맞는 셔틀버스가 없습니다.'})

        selected_candidates = valid_candidates

        results = []
        for dep in selected_candidates:
            try:
                travel_time_sec, route_steps = get_travel_duration_and_route(dep)
                predicted_arrival = dep + timedelta(seconds=travel_time_sec)
                
                # 다시 한번 확인: 셔틀버스 도착 시간이 사용자 도착 시간보다 늦은 경우만 유효
                if predicted_arrival >= arrival_time:
                    # 현재 시간 기준으로 버스의 현재 위치 추정
                    elapsed = (current_time - dep).total_seconds()
                    
                    if elapsed <= 0:
                        # 아직 출발하지 않은 버스
                        progress = 0
                        current_lat = float(ORIGIN.split(',')[0])
                        current_lng = float(ORIGIN.split(',')[1])
                        remaining = (predicted_arrival - arrival_time).total_seconds()
                        bus_status = "출발 대기 중"
                    elif elapsed >= travel_time_sec:
                        # 이미 도착한 버스 (이론적으로 발생하지 않아야 함)
                        progress = 1.0
                        current_lat = float(DESTINATION.split(',')[0])
                        current_lng = float(DESTINATION.split(',')[1])
                        remaining = 0
                        bus_status = "도착 완료"
                    else:
                        # 운행 중인 버스
                        progress = elapsed / travel_time_sec
                        
                        if route_steps and len(route_steps) > 1:
                            segment_index = int(progress * (len(route_steps) - 1))
                            segment_index = min(segment_index, len(route_steps) - 2)
                            segment_progress = (progress * (len(route_steps) - 1)) % 1
                            
                            start_loc = route_steps[segment_index]['start_location']
                            end_loc = route_steps[segment_index + 1]['start_location']
                            current_lat = start_loc['lat'] + (end_loc['lat'] - start_loc['lat']) * segment_progress
                            current_lng = start_loc['lng'] + (end_loc['lng'] - start_loc['lng']) * segment_progress
                        else:
                            # route_steps가 없는 경우 직선 보간
                            origin_lat = float(ORIGIN.split(',')[0])
                            origin_lng = float(ORIGIN.split(',')[1])
                            dest_lat = float(DESTINATION.split(',')[0])
                            dest_lng = float(DESTINATION.split(',')[1])
                            
                            current_lat = origin_lat + (dest_lat - origin_lat) * progress
                            current_lng = origin_lng + (dest_lng - origin_lng) * progress
                        
                        remaining = (predicted_arrival - arrival_time).total_seconds()
                        bus_status = "운행 중"

                    results.append({
                        'departure_time': dep.strftime('%H:%M'),
                        'predicted_arrival': predicted_arrival.strftime('%H:%M'),
                        'wait_time_minutes': max(0, round(remaining / 60, 1)),
                        'current_location': {'lat': current_lat, 'lng': current_lng},
                        'progress': round(progress * 100, 1),
                        'bus_status': bus_status,
                        'status': 'ok'
                    })
            except Exception as e:
                print(f"Error processing departure {dep}: {e}")  # 디버깅용
                results.append({
                    'departure_time': dep.strftime('%H:%M'),
                    'status': 'error',
                    'message': f'경로 계산 실패: {str(e)}'
                })

        if not results:
            return jsonify({'status': 'no_bus', 'message': '도착 시간에 맞는 셔틀버스가 없습니다.'})

        # 대기 시간이 짧은 순으로 정렬
        valid_results = [r for r in results if r.get('status') == 'ok']
        valid_results.sort(key=lambda x: x.get('wait_time_minutes', float('inf')))

        return jsonify({'status': 'ok', 'candidates': valid_results})

    except Exception as e:
        print(f"Unexpected error: {e}")  # 디버깅용
        return jsonify({'status': 'error', 'message': f'서버 오류가 발생했습니다: {str(e)}'})


def get_travel_duration_and_route(departure_time):
    """Google Directions API를 사용하여 이동 시간과 경로를 계산"""
    try:
        timestamp = int(departure_time.timestamp())
        now_ts = int(datetime.now().timestamp())

        # 과거 시간인 경우 현재 시간으로 조정
        if timestamp < now_ts:
            timestamp = now_ts

        url = 'https://maps.googleapis.com/maps/api/directions/json'
        
        # 여러 모드 시도
        modes = ['driving', 'transit']
        
        for mode in modes:
            params = {
                'origin': ORIGIN,
                'destination': DESTINATION,
                'mode': mode,
                'key': GOOGLE_API_KEY,
                'language': 'ko'
            }
            
            # driving 모드일 때만 departure_time과 traffic_model 사용
            if mode == 'driving':
                params['departure_time'] = timestamp
                params['traffic_model'] = 'best_guess'
            
            if WAYPOINTS:
                params['waypoints'] = '|'.join(WAYPOINTS)

            print(f"API 요청 URL: {url}")
            print(f"파라미터: {params}")
            
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            
            print(f"API 응답 상태: {data.get('status')}")
            
            if data['status'] == 'OK' and data.get('routes'):
                route = data['routes'][0]
                if route.get('legs'):
                    leg = route['legs'][0]
                    
                    # 교통 상황을 고려한 시간이 있으면 사용, 없으면 일반 시간 사용
                    if 'duration_in_traffic' in leg:
                        duration = leg['duration_in_traffic']['value']
                    else:
                        duration = leg['duration']['value']
                    
                    steps = leg.get('steps', [])
                    print(f"경로 계산 성공: {duration}초, {len(steps)}개 단계")
                    return duration, steps
            elif data['status'] == 'ZERO_RESULTS':
                print(f"{mode} 모드에서 경로를 찾을 수 없음")
                continue
            else:
                print(f"API 오류: {data.get('status')} - {data.get('error_message', '')}")

        # 모든 모드에서 실패한 경우 기본값 사용
        print("API 호출 실패, 기본 예상 시간 사용")
        return 1200, []  # 기본 20분 (1200초)

    except requests.exceptions.Timeout:
        print("API 요청 시간 초과, 기본 시간 사용")
        return 1200, []
    except requests.exceptions.RequestException as e:
        print(f"네트워크 오류: {e}, 기본 시간 사용")
        return 1200, []
    except Exception as e:
        print(f"예상치 못한 오류: {e}, 기본 시간 사용")
        return 1200, []


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)