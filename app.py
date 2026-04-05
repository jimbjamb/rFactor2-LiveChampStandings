import json
import time
from flask import Flask, render_template
from flask_socketio import SocketIO

try:
    from pyRfactor2SharedMemory.sharedMemoryAPI import SimInfoAPI
except ImportError:
    print("BŁĄD: Nie znaleziono folderu 'pyRfactor2SharedMemory' lub brakuje w nim plików.")
    print("Upewnij się, że rozpakowałeś projekt z GitHuba do folderu obok app.py.")
    exit(1)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

STANDINGS_FILE = "standings.json"

POINT_SYSTEM = [25, 20, 16, 13, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]

info = SimInfoAPI()

def get_data():
    try:
        if not info.isSharedMemoryAvailable:
            return []

        scoring = info.Rf2Scor
        
        with open(STANDINGS_FILE, 'r', encoding='utf-8') as f:
            db = json.load(f)

        m_scoring_info = getattr(scoring, 'mScoringInfo', scoring)
        
        is_race = getattr(m_scoring_info, 'mSession', 0) == 10 
        
        players_name_bytes = getattr(m_scoring_info, 'mPlayerName', b'')
        players_name = players_name_bytes.decode('utf-8', errors='ignore').split('\0', 1)[0].strip()
        
        all_drivers = []
        num_vehicles = getattr(m_scoring_info, 'mNumVehicles', 0)
        vehicles = getattr(scoring, 'mVehicles', [])
        
        drivers_in_session = set()

        for i in range(num_vehicles):
            v = vehicles[i]
            
            name_bytes = getattr(v, 'mDriverName', b'')
            name = name_bytes.decode('utf-8', errors='ignore').split('\0', 1)[0].strip()
            
            if not name:
                continue

            drivers_in_session.add(name)

            veh_desc = getattr(v, 'mVehicleName', b'').decode('utf-8', errors='ignore').split('\0', 1)[0].strip()
            team_color = "#808080"
            for t_name, t_color in db.get('teams', {}).items():
                if veh_desc.startswith(t_name):
                    team_color = t_color
                    break

            pos = getattr(v, 'mPlace', 0)

            is_new = name not in db['standings']
            
            base_points = db['standings'].get(name, 0)
            live_points = 0
            if is_race and 1 <= pos <= len(POINT_SYSTEM):
                live_points = POINT_SYSTEM[pos-1]
            
            all_drivers.append({
                "name": name,
                "base_points": base_points,
                "live_points": live_points,
                "total_points": base_points + live_points,
                "color": team_color,
                "is_player": (name == players_name),
                "is_new": is_new
            })

        for db_name, db_points in db['standings'].items():
            if db_name not in drivers_in_session:
                all_drivers.append({
                    "name": db_name,
                    "base_points": db_points,
                    "live_points": 0,
                    "total_points": db_points,
                    "color": "#555555",
                    "is_player": (db_name == players_name),
                    "is_new": False
                })

        all_drivers.sort(key=lambda x: x['base_points'], reverse=True)
        for index, d in enumerate(all_drivers):
            d['start_pos'] = index + 1

        all_drivers.sort(key=lambda x: x['total_points'], reverse=True)
        for index, d in enumerate(all_drivers):
            d['live_pos'] = index + 1
            if d['is_new']:
                d['pos_change'] = "🔵"
            else:
                diff = d['start_pos'] - d['live_pos']
                if diff > 0:
                    d['pos_change'] = f"▲{diff}"
                elif diff < 0:
                    d['pos_change'] = f"▼{abs(diff)}"
                else:
                    d['pos_change'] = ""

        try:
            p_idx = next(i for i, d in enumerate(all_drivers) if d['is_player'])
        except StopIteration:
            p_idx = 0

        start = max(0, p_idx - 3)
        if start + 7 > len(all_drivers):
            start = max(0, len(all_drivers) - 7)
            
        return {
            "drivers": all_drivers[start:start+7],
            "is_race": is_race
        }
        
    except Exception as e:
        print(f"Błąd odczytu w get_data: {e}")
        return []

def background_thread():
    while True:
        data = get_data()
        if data:
            socketio.emit('update_data', data)
        socketio.sleep(1)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    print("Uruchamianie serwera na http://localhost:5000 ...")
    socketio.start_background_task(background_thread)
    socketio.run(app, port=5000, allow_unsafe_werkzeug=True)