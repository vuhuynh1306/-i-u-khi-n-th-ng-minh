# ESP32 MicroPython - local monitoring over phone hotspot
import network, socket, time, _thread, json

WIFI_SSID = 'Redmi Note 13'       # Replace with phone hotspot name
WIFI_PASSWORD = '29032006'    # Replace locally; do not share your password

state = {
 'distance': None, 'left': None, 'right': None, 'servo': 90,
 'motor_left': 0, 'motor_right': 0, 'action': 'KHOI DONG',
 'avoid_count': 0, 'wifi': 'Dang ket noi', 'ip': '',
 'threshold': 20, 'slow_threshold': 25, 'start_ms': time.ticks_ms(),
 'events': []
}

def event(message):
    events = state['events']
    events.insert(0, {'t': time.ticks_diff(time.ticks_ms(), state['start_ms']) // 1000, 'msg': message})
    if len(events) > 12:
        events.pop()

def update(**kwargs):
    state.update(kwargs)

HTML = '''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ESP32 Robot Monitor</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#0b1220;color:#e7eef9;font-family:system-ui,-apple-system,Arial,sans-serif}main{max-width:780px;margin:auto;padding:18px}header{display:flex;justify-content:space-between;align-items:center;gap:12px}h1{font-size:21px;margin:0}small,.muted{color:#9aaec8}.pill{border-radius:99px;padding:7px 12px;background:#14532d;color:#a7f3d0;font-weight:700}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:15px 0}.card{background:#172339;border:1px solid #293950;border-radius:15px;padding:15px}.label{font-size:13px;color:#a9b9d1}.value{font-size:26px;font-weight:750;margin-top:6px}.wide{grid-column:1/-1}.status{font-size:20px;font-weight:700}.warn{color:#fbbf24}.ok{color:#86efac}canvas{width:100%;height:170px;display:block}ul{list-style:none;padding:0;margin:8px 0}li{padding:9px 0;border-bottom:1px solid #293950;font-size:13px}footer{font-size:12px;color:#9aaec8;margin:14px 0}@media(max-width:360px){.value{font-size:22px}}
</style></head><body><main><header><div><h1>XE TỰ HÀNH ESP32</h1><small>Giám sát trực tiếp · AUTO</small></div><span class="pill">AUTO</span></header><div class="grid"><section class="card"><div class="label">Khoảng cách phía trước</div><div class="value" id="distance">-- cm</div><div id="safety" class="muted">Đang chờ</div></section><section class="card"><div class="label">Số lần phát hiện vật cản</div><div class="value" id="count">0</div></section><section class="card wide"><div class="label">Trạng thái xe</div><div class="status" id="action">Đang khởi động</div></section><section class="card"><div class="label">Quét trái</div><div class="value" id="left">--</div></section><section class="card"><div class="label">Quét phải</div><div class="value" id="right">--</div></section><section class="card"><div class="label">Góc đặt servo</div><div class="value" id="servo">--</div></section><section class="card"><div class="label">PWM đặt trái / phải</div><div class="value" id="motors" style="font-size:20px">--</div></section><section class="card wide"><div class="label">Khoảng cách theo thời gian (60 mẫu gần nhất)</div><canvas id="chart" width="700" height="180"></canvas></section><section class="card wide"><div class="label">Nhật ký sự kiện</div><ul id="events"></ul></section></div><footer><div>Wi-Fi: <span id="wifi">--</span> · IP: <span id="ip">--</span></div><div>Thời gian chạy: <span id="uptime">--</span> · Cập nhật mỗi 0,5 giây</div><div id="connection" class="warn">Đang kết nối dữ liệu...</div></footer></main><script>
const $=id=>document.getElementById(id),history=[];function format(x,u=''){return x===null||x===undefined?'--':x+u}function draw(){const c=$('chart'),ctx=c.getContext('2d'),w=c.width,h=c.height;ctx.clearRect(0,0,w,h);ctx.strokeStyle='#30445f';ctx.lineWidth=1;for(let i=0;i<4;i++){let y=15+i*45;ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke()}let vals=history.filter(x=>x!==null);if(!vals.length)return;let max=Math.max(50,...vals)*1.1;ctx.strokeStyle='#38bdf8';ctx.lineWidth=3;ctx.beginPath();let started=false;history.forEach((v,i)=>{if(v===null){started=false;return}let x=10+i*(w-20)/59,y=h-10-v/max*(h-25);if(!started){ctx.moveTo(x,y);started=true}else ctx.lineTo(x,y)});ctx.stroke();ctx.strokeStyle='#f59e0b';let threshold=20,y=h-10-threshold/max*(h-25);ctx.setLineDash([6,5]);ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();ctx.setLineDash([])}
async function poll(){try{const r=await fetch('/api/status',{cache:'no-store'});if(!r.ok)throw Error(r.status);const s=await r.json();$('distance').textContent=format(s.distance,' cm');$('safety').textContent=s.distance===null?'Không có phép đo hợp lệ':s.distance<=s.threshold?'Có vật cản':'Đường thông thoáng';$('safety').className=s.distance!==null&&s.distance<=s.threshold?'warn':'ok';$('count').textContent=s.avoid_count;$('action').textContent=s.action;$('left').textContent=format(s.left,' cm');$('right').textContent=format(s.right,' cm');$('servo').textContent=format(s.servo,'°');$('motors').textContent=s.motor_left+'% / '+s.motor_right+'%';$('wifi').textContent=s.wifi;$('ip').textContent=s.ip;$('uptime').textContent=Math.floor(s.uptime/60)+' phút '+s.uptime%60+' giây';$('events').innerHTML='';(s.events||[]).forEach(e=>{const li=document.createElement('li');li.textContent='+'+e.t+'s · '+e.msg;$('events').appendChild(li)});history.push(s.distance);if(history.length>60)history.shift();draw();$('connection').textContent='Đang nhận dữ liệu';$('connection').className='ok'}catch(e){$('connection').textContent='Mất kết nối ESP32 · Đang thử lại';$('connection').className='warn'}}setInterval(poll,500);poll();
</script></body></html>'''

def _reply(client, code, content_type, body):
    if isinstance(body, str):
        body = body.encode('utf-8')
    header = ('HTTP/1.0 '+code+'\r\nContent-Type: '+content_type+'\r\nCache-Control: no-store\r\nConnection: close\r\nContent-Length: '+str(len(body))+'\r\n\r\n')
    client.write(header.encode('utf-8'))
    client.write(body)

def _server_loop():
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    server = None
    while True:
        try:
            if not sta.isconnected():
                state['wifi'] = 'Mat ket noi'
                state['ip'] = ''
                if server:
                    server.close()
                    server = None
                try:
                    sta.disconnect()
                except Exception:
                    pass
                sta.connect(WIFI_SSID, WIFI_PASSWORD)
                state['wifi'] = 'Dang ket noi'
                # This wait is in the web thread, not the motor control loop
                for _ in range(20):
                    if sta.isconnected():
                        break
                    time.sleep_ms(500)
                if not sta.isconnected():
                    time.sleep_ms(2000)
                    continue
                state['ip'] = sta.ifconfig()[0]
                state['wifi'] = 'Da ket noi'
                print('WEB: http://'+state['ip'])
            if server is None:
                server = socket.socket()
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.bind(('0.0.0.0',80))
                server.listen(2)
                server.settimeout(1)
            try:
                client, address = server.accept()
            except OSError:
                continue
            try:
                client.settimeout(1)
                request = client.recv(512)
                path = request.split(b' ')[1] if b' ' in request else b'/'
                if path.startswith(b'/api/status'):
                    payload = dict(state)
                    payload['uptime'] = time.ticks_diff(time.ticks_ms(), state['start_ms']) // 1000
                    payload['events'] = list(state['events'])
                    _reply(client, '200 OK', 'application/json; charset=utf-8', json.dumps(payload))
                elif path == b'/' or path.startswith(b'/?'):
                    _reply(client, '200 OK', 'text/html; charset=utf-8', HTML)
                else:
                    _reply(client, '404 Not Found', 'text/plain', 'Not found')
            except Exception as e:
                print('WEB client:', e)
            finally:
                client.close()
        except Exception as e:
            print('WEB server:', e)
            if server:
                try: server.close()
                except Exception: pass
                server = None
            time.sleep_ms(2000)

def start():
    _thread.start_new_thread(_server_loop, ())
