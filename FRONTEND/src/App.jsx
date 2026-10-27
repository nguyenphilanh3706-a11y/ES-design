import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
} from 'chart.js';
import { Line } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend
);

const API = (
  import.meta.env.VITE_API_URL ||
  'https://es-design.onrender.com'
).replace(/\/+$/, '');

const DEVICE = import.meta.env.VITE_DEVICE_ID || 'esp32_v1';

const METRICS = [
  {
    key: 'soilMoisture',
    name: 'Độ ẩm đất',
    unit: '%',
    digits: 1,
    color: '#34d399',
    tint: '#064e3b',
    icon: 'drop',
    max: 100,
    hint: 'Ngưỡng chặn tưới: 60%',
  },
  {
    key: 'light',
    name: 'Ánh sáng',
    unit: 'Lux',
    digits: 0,
    color: '#fbbf24',
    tint: '#78350f',
    icon: 'sun',
    max: 100000,
    hint: 'Cường độ ánh sáng',
  },
  {
    key: 'temperature',
    name: 'Nhiệt độ',
    unit: '°C',
    digits: 1,
    color: '#f87171',
    tint: '#7f1d1d',
    icon: 'temp',
    max: 50,
    hint: 'Nhiệt độ môi trường',
  },
  {
    key: 'humidity',
    name: 'Độ ẩm khí',
    unit: '%',
    digits: 1,
    color: '#38bdf8',
    tint: '#0369a1',
    icon: 'waves',
    max: 100,
    hint: 'Độ ẩm tương đối',
  },
  {
    key: 'vpd',
    name: 'VPD',
    unit: 'kPa',
    digits: 2,
    color: '#a78bfa',
    tint: '#4c1d95',
    icon: 'activity',
    max: 4,
    hint: 'Độ thiếu hụt áp suất hơi',
  },
];

const TABS = [
  ['live', 'activity', 'Trực tiếp'],
  ['history', 'clock', 'Lịch sử 24h'],
  ['events', 'list', 'Nhật ký'],
  ['ai', 'spark', 'Dự đoán AI'],
];

const fmt = (value, digits = 1) =>
  Number.isFinite(value)
    ? value.toLocaleString('vi-VN', {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      })
    : '—';

function dateText(value, options) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isFinite(date.getTime())
    ? date.toLocaleString('vi-VN', options)
    : '—';
}

async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    ...options,
    cache: 'no-store',
    signal: AbortSignal.timeout(options.timeout || 30000),
  });

  let body;
  try {
    body = await response.json();
  } catch {
    throw new Error(
      `Máy chủ chưa sẵn sàng (mã ${response.status}, phản hồi không phải JSON; có thể đang khởi động lại).`
    );
  }

  if (!response.ok) {
    throw new Error(
      typeof body.detail === 'string'
        ? body.detail
        : `Yêu cầu thất bại (${response.status}).`
    );
  }

  return body;
}

function Icon({ name, size = 22 }) {
  const shapes = {
    leaf: (
      <>
        <path d="M20 4C10 2 3 7 5 14c2 7 13 6 15-10Z" />
        <path d="M4 21 15 10M8 16l-1-5m5 1 5 1" />
      </>
    ),
    drop: (
      <path d="M12 3S5 11 5 15a7 7 0 0 0 14 0c0-4-7-12-7-12Zm-3 12c0 2 1 3 3 3" />
    ),
    sun: (
      <>
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l2 2m10 10 2 2M5 19l2-2M17 7l2-2" />
      </>
    ),
    temp: (
      <>
        <path d="M9 14V5a3 3 0 0 1 6 0v9a5 5 0 1 1-6 0Z" />
        <path d="M12 8v10" />
      </>
    ),
    waves: (
      <path d="M3 7c3-4 6 4 9 0s6 4 9 0M3 12c3-4 6 4 9 0s6 4 9 0M3 17c3-4 6 4 9 0s6 4 9 0" />
    ),
    activity: <path d="M2 12h5l3-8 4 16 3-8h5" />,
    clock: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 6v6l4 2" />
      </>
    ),
    list: <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" />,
    spark: <path d="m13 2-9 12h7l-1 8 10-13h-7l1-7Z" />,
    hand: (
      <>
        <path d="M8 13V7a2 2 0 0 1 4 0v5-7a2 2 0 0 1 4 0v7-4a2 2 0 0 1 4 0v8c0 4-3 6-7 6-3 0-5-2-7-5l-3-4a2 2 0 0 1 3-2l2 2Z" />
      </>
    ),
    lock: (
      <>
        <rect x="5" y="10" width="14" height="11" rx="3" />
        <path d="M8 10V7a4 4 0 0 1 8 0v3m-4 5v2" />
      </>
    ),
    settings: (
      <>
        <path d="m9 3-1 3-3 1-2 4 2 2v4l4 3 3-1 3 1 4-3v-4l2-2-2-4-3-1-1-3Z" />
        <circle cx="12" cy="12" r="3" />
      </>
    ),
    download: <path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5" />,
    check: <path d="m5 12 4 4L19 6" />,
    arrow: <path d="M4 12h16m-6-6 6 6-6 6" />,
    alert: (
      <>
        <path d="m12 3 10 18H2L12 3Z" />
        <path d="M12 9v5m0 3h.01" />
      </>
    ),
    wifi: (
      <path d="M5 12.55a11 11 0 0 1 14.08 0M1.42 9a16 16 0 0 1 21.16 0M8.53 16.11a6 6 0 0 1 6.95 0M12 20h.01" />
    ),
  };

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {shapes[name] || shapes.activity}
    </svg>
  );
}

function WateringPot({ data, online }) {
  const [watering, setWatering] = useState({
    phase: 'idle',
    before: null,
    after: null,
  });

  const previous = useRef(null);
  const cycle = useRef(null);

  const real = data?.simulated === false;
  const validSoil =
    online &&
    real &&
    Number.isFinite(data?.soilMoisture) &&
    data.soilMoisture >= 0 &&
    data.soilMoisture <= 100;

  const moisture = validSoil ? data.soilMoisture : null;
  const pumping = online && real && data?.pump === 'ON';

  const waterMissing =
    online &&
    (data?.waterAvailable === false ||
      String(data?.fault || '').trim().toUpperCase() === 'NO WATER (FLOAT)');

  // Chu kỳ theo dõi trước/sau tưới
  useEffect(() => {
    const stamp = Date.parse(data?.sampled_at || '');
    const pumpKnown = data?.pump === 'ON' || data?.pump === 'OFF';

    if (!validSoil || !Number.isFinite(stamp) || !pumpKnown) {
      if (cycle.current) {
        setWatering({
          phase: 'interrupted',
          before: cycle.current.before,
          after: null,
        });
      }
      cycle.current = null;
      previous.current = null;
      return;
    }

    const current = {
      id: data.sample_id,
      time: stamp,
      soil: data.soilMoisture,
      pump: data.pump,
    };

    const last = previous.current;

    if (last && current.id && current.id === last.id) return;
    if (last && current.time < last.time) return;

    const gap = last ? current.time - last.time : 0;

    if (last && gap > 10000) {
      if (cycle.current) {
        setWatering({
          phase: 'interrupted',
          before: cycle.current.before,
          after: null,
        });
      }
      cycle.current = null;
      previous.current = current;
      return;
    }

    if (!last) {
      if (current.pump === 'ON') {
        cycle.current = { phase: 'pumping', before: null, stoppedAt: null };
        setWatering({ phase: 'pumping', before: null, after: null });
      }
      previous.current = current;
      return;
    }

    if (last.pump === 'OFF' && current.pump === 'ON') {
      cycle.current = { phase: 'pumping', before: last.soil, stoppedAt: null };
      setWatering({ phase: 'pumping', before: last.soil, after: null });
    }

    const active = cycle.current;

    if (active?.phase === 'pumping' && current.pump === 'OFF') {
      if (active.before === null) {
        setWatering({ phase: 'interrupted', before: null, after: null });
        cycle.current = null;
      } else {
        active.phase = 'settling';
        active.stoppedAt = current.time;
        setWatering({ phase: 'settling', before: active.before, after: null });
      }
    } else if (
      active?.phase === 'settling' &&
      current.pump === 'OFF' &&
      current.time - active.stoppedAt >= 30000
    ) {
      setWatering({ phase: 'done', before: active.before, after: current.soil });
      cycle.current = null;
    }

    previous.current = current;
  }, [data, online, validSoil]);

  const number = value =>
    value.toLocaleString('vi-VN', {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    });

  const band = moisture === null
    ? 'Chờ số đo mới'
    : moisture < 30
      ? 'Dưới ngưỡng đất khô'
      : moisture < 60
        ? 'Trong khoảng 30–60%'
        : 'Đã đạt ngưỡng chặn tưới';

  const tone = moisture === null
    ? '#94a3b8'
    : moisture < 30
      ? '#fbbf24'
      : moisture < 60
        ? '#34d399'
        : '#38bdf8';

  let report = 'Giữ trang mở để theo dõi độ ẩm trước và sau một chu kỳ tưới.';

  if (watering.phase === 'pumping') {
    report = watering.before === null
      ? 'Bơm đang chạy. Chưa có mẫu trước tưới để so sánh.'
      : `Bơm đang chạy. Độ ẩm trước tưới: ${number(watering.before)}%.`;
  } else if (watering.phase === 'settling') {
    report = 'Đang chờ mẫu đo sau khi bơm dừng ít nhất 30 giây để quan sát nước thấm.';
  } else if (watering.phase === 'interrupted') {
    report = 'Chưa đủ dữ liệu liên tục để đánh giá chu kỳ tưới này.';
  } else if (watering.phase === 'done') {
    const delta = watering.after - watering.before;
    const change = Math.abs(delta) < 0.05
      ? 'Chưa thay đổi ở mức hiển thị'
      : `${delta > 0 ? 'Tăng' : 'Giảm'} ${number(Math.abs(delta))} điểm %`;

    report = `${number(watering.before)}% → ${number(watering.after)}%. ${change} sau chu kỳ vừa quan sát.`;
  }

  return (
    <section className={`garden-card basic-pot-widget ${pumping ? 'is-pumping' : ''} ${!validSoil ? 'is-stale' : ''}`}>
      <style>{`
        .basic-pot-widget {
          padding: 25px;
          margin-bottom: 24px;
          background: linear-gradient(145deg, #131c2e, #0d1422);
          color: #e2e8f0;
          transition: filter 0.3s ease, opacity 0.3s ease;
        }
        
        .basic-pot-widget.is-stale .pot-visual-area {
          opacity: 0.4;
          filter: grayscale(60%);
        }

        .pot-heading {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 14px;
          flex-wrap: wrap;
        }

        .pot-heading small {
          color: #34d399;
          font-size: 10px;
          font-weight: 800;
          letter-spacing: 2px;
        }

        .pot-heading h2 {
          margin: 7px 0 0;
          font-size: 24px;
          color: #f8fafc;
        }

        .pot-badge {
          padding: 8px 12px;
          border-radius: 999px;
          border: 1px solid #334155;
          background: #0f172a;
          font-size: 11px;
          color: #cbd5e1;
        }

        .is-pumping .pot-badge {
          border-color: #0284c7;
          color: #38bdf8;
        }

        .pot-body {
          display: grid;
          grid-template-columns: minmax(200px, 1fr) minmax(180px, 1fr);
          gap: 30px;
          align-items: center;
          margin-top: 30px;
        }

        .pot-visual-area {
          position: relative;
          height: 220px;
          display: flex;
          align-items: flex-end;
          justify-content: center;
          transition: all 0.3s ease;
        }

        /* Hình chậu 2D */
        .pot-vessel {
          width: 150px;
          height: 140px;
          border: 5px solid #475569;
          border-top: none;
          border-radius: 0 0 35px 35px;
          position: relative;
          overflow: hidden;
          background: #1e293b; /* Màu đất khô mờ */
          z-index: 10;
        }
        
        .pot-base-rim {
          position: absolute;
          top: -5px; left: -10px; right: -10px;
          height: 10px;
          background: #475569;
          border-radius: 5px;
          z-index: 12;
        }

        /* Lớp nền mô phỏng đất */
        .soil-bg {
          position: absolute;
          inset: 0;
          background: #2a1610; /* Màu đất nâu tối */
          z-index: 1;
        }

        /* Lớp nước dâng lên dựa vào % độ ẩm */
        .water-level {
          position: absolute;
          bottom: 0;
          left: 0;
          right: 0;
          background: rgba(14, 165, 233, 0.65); /* Xanh nước biển trong suốt */
          transition: height 0.8s cubic-bezier(0.4, 0, 0.2, 1);
          z-index: 2;
        }

        /* Vạch mặt nước */
        .water-surface {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          height: 4px;
          background: rgba(125, 211, 252, 0.9);
        }

        /* Cây mọc từ chậu */
        .plant-svg {
          position: absolute;
          bottom: 135px;
          left: 50%;
          transform: translateX(-50%);
          color: #10b981;
          z-index: 5;
        }

        /* Hiệu ứng tia nước (ẩn khi không bơm) */
        .rain-drops {
          position: absolute;
          bottom: 140px;
          left: 50%;
          transform: translateX(-50%);
          width: 90px;
          height: 80px;
          display: flex;
          justify-content: space-around;
          opacity: 0;
          transition: opacity 0.3s ease;
          pointer-events: none;
          z-index: 20;
        }

        .is-pumping .rain-drops {
          opacity: 1;
        }

        .rain-drops i {
          width: 3px;
          height: 16px;
          background: #38bdf8;
          border-radius: 3px;
          animation: rain-fall 0.5s linear infinite;
        }

        .rain-drops i:nth-child(1) { animation-delay: 0.1s; }
        .rain-drops i:nth-child(2) { animation-delay: 0.3s; }
        .rain-drops i:nth-child(3) { animation-delay: 0.0s; }
        .rain-drops i:nth-child(4) { animation-delay: 0.4s; }
        .rain-drops i:nth-child(5) { animation-delay: 0.2s; }

        @keyframes rain-fall {
          0% { transform: translateY(-10px); opacity: 0; }
          30% { opacity: 1; }
          100% { transform: translateY(70px); opacity: 0; }
        }

        .pot-reading {
          display: flex;
          flex-direction: column;
          justify-content: center;
        }

        .pot-reading-label {
          color: #94a3b8;
          font-size: 13px;
        }

        .pot-number {
          margin: 6px 0;
          font-size: clamp(40px, 6vw, 60px);
          font-weight: 800;
          line-height: 1.1;
          font-variant-numeric: tabular-nums;
        }

        .pot-number span {
          font-size: 20px;
          margin-left: 5px;
        }

        .pot-band {
          font-size: 13px;
          margin-bottom: 20px;
          font-weight: 600;
        }

        .pot-limits {
          display: grid;
          gap: 10px;
          padding: 15px;
          background: #0f172a;
          border: 1px solid #1e293b;
          border-radius: 12px;
          color: #cbd5e1;
          font-size: 11px;
          line-height: 1.5;
        }

        .pot-limits div {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .pot-limits span.limit-dot {
          display: inline-block;
          width: 8px; height: 8px;
          border-radius: 50%;
        }

        .pot-report {
          margin-top: 25px;
          padding: 16px;
          border: 1px solid #1e293b;
          border-radius: 15px;
          background: #0f172a99;
          font-size: 12px;
          line-height: 1.8;
        }

        .pot-report strong { color: #34d399; }
        .pot-report p { margin: 5px 0 0; color: #cbd5e1; }

        .pot-note {
          margin-top: 15px;
          color: #64748b;
          font-size: 10px;
          line-height: 1.7;
        }

        @media (max-width: 600px) {
          .pot-body { grid-template-columns: 1fr; gap: 20px; }
          .pot-reading { text-align: center; }
          .pot-limits { text-align: left; }
        }
      `}</style>

      <div className="pot-heading">
        <div>
          <small>LIVE PLANT · ESP32</small>
          <h2>Chậu cây của bạn</h2>
        </div>

        <span className="pot-badge">
          {!online
            ? 'Chờ kết nối'
            : pumping
              ? 'Đang tưới nước'
              : waterMissing
                ? 'Cần bổ sung nước'
                : 'Đang theo dõi'}
        </span>
      </div>

      <div className="pot-body">
        <div className="pot-visual-area" aria-hidden="true">
          <div className="plant-svg">
            <Icon name="leaf" size={60} />
          </div>

          <div className="rain-drops">
            <i /><i /><i /><i /><i />
          </div>

          <div className="pot-vessel">
            <div className="pot-base-rim"></div>
            <div className="soil-bg"></div>
            <div
              className="water-level"
              style={{ height: `${data?.soilMoisture ?? 0}%` }}
            >
              <div className="water-surface"></div>
            </div>
          </div>
        </div>

        <div className="pot-reading">
          <div className="pot-reading-label">Độ ẩm đất hiện tại</div>

          <div className="pot-number" style={{ color: tone }}>
            {moisture === null ? '—' : number(moisture)}
            <span>%</span>
          </div>

          <div className="pot-band" style={{ color: tone }}>
            {band}
          </div>

          <div className="pot-limits">
            <div><span className="limit-dot" style={{ background: '#fbbf24' }}></span> Dưới 30%: ngưỡng đất khô.</div>
            <div><span className="limit-dot" style={{ background: '#34d399' }}></span> Từ 30% – dưới 60%: khoảng lý tưởng.</div>
            <div><span className="limit-dot" style={{ background: '#38bdf8' }}></span> Từ 60%: tự động chặn/dừng tưới.</div>
          </div>
        </div>
      </div>

      <div className="pot-report" role="status">
        <strong>
          {watering.phase === 'done'
            ? 'Kết quả chu kỳ gần nhất đã quan sát'
            : 'Theo dõi sau tưới'}
        </strong>
        <p>{report}</p>
      </div>

      <p className="pot-note">
        Lượng nước (màu xanh) dâng trong chậu mô phỏng trực tiếp theo phần trăm độ ẩm đất thực tế cuối cùng nhận được. 
        Hiệu ứng tia nước hiển thị khi thiết bị thực sự xác nhận trạng thái bơm ON.
      </p>
    </section>
  );
}

export default function App() {
  const [snapshot, setSnapshot] = useState(null);
  const [apiError, setApiError] = useState('');
  const [samples, setSamples] = useState([]);
  const [clock, setClock] = useState(Date.now());

  const [tab, setTab] = useState('live');
  const [metric, setMetric] = useState('all');
  const [settings, setSettings] = useState(false);

  const [sending, setSending] = useState(false);
  const [command, setCommand] = useState(null);
  const [notice, setNotice] = useState('');
  const [events, setEvents] = useState([]);

  const [history, setHistory] = useState([]);
  const [historyBusy, setHistoryBusy] = useState(false);
  const [historyError, setHistoryError] = useState('');
  const [cursor, setCursor] = useState(null);

  const commandLock = useRef(false);
  const historyLock = useRef(false);
  const lastDevice = useRef(null);
  const lastAI = useRef(null);

  const logEvent = useCallback((message, status = 'info') => {
    setEvents(previous => [
      {
        id: crypto.randomUUID(),
        time: new Date().toISOString(),
        message,
        status,
      },
      ...previous,
    ].slice(0, 100));
  }, []);

  useEffect(() => {
    let stopped = false;
    let timer;

    let lastSampledMs = 0;

    function applyLatest(result) {
        if (result.status !== 'success') {
          throw new Error('API chưa trả dữ liệu hợp lệ.');
        }

        if (stopped) return;

        const item = result.data?.simulated === false
          ? result.data
          : null;

        // Bỏ qua bản cũ hơn bản đã hiển thị (SSE và polling có thể đến lệch thứ tự)
        const sampledMs = item ? Date.parse(item.sampled_at || item.time) : NaN;
        if (Number.isFinite(sampledMs)) {
          if (sampledMs < lastSampledMs) return;
          lastSampledMs = sampledMs;
        }

        setSnapshot({
          ...result,
          data: item,
          fetchedAt: Date.now(),
        });

        setApiError('');

        if (!item) {
          setSamples([]);
          lastDevice.current = null;
          lastAI.current = null;
        }

        if (item) {
          const deviceState = [
            item.mode,
            item.pump,
            item.fsm,
            item.waterAvailable,
            item.fault,
            item.simulated,
          ].join('|');

          if (lastDevice.current !== deviceState) {
            logEvent(
              `${lastDevice.current === null ? 'Nhận trạng thái' : 'Thiết bị cập nhật'}: ${
                item.mode
              } · Bơm ${item.pump} · ${item.fsm}${
                item.fault ? ` · ${item.fault}` : ''
              }`,
              item.fault ? 'error' : 'info'
            );
            lastDevice.current = deviceState;
          }

          const aiState = [
            item.aiReady,
            item.aiMessage,
            item.soilPredictionSource,
            item.lightPredictionSource,
          ].join('|');

          if (lastAI.current !== aiState && item.aiMessage) {
            logEvent(
              `AI: ${item.aiMessage}`,
              item.aiReady ? 'success' : 'info'
            );
          }

          lastAI.current = aiState;
        }

        if (item?.sample_id) {
          setSamples(previous => {
            const index = previous.findIndex(
              value => value.sample_id === item.sample_id
            );

            if (index >= 0) {
              const updated = [...previous];
              updated[index] = item;
              return updated;
            }

            return [...previous, item].slice(-60);
          });
        }
    }

    let failures = 0;
    let busy = false;

    async function poll() {
      if (busy || stopped) return;
      busy = true;
      clearTimeout(timer);

      try {
        const result = await request(
          `/api/telemetry/latest?device_id=${encodeURIComponent(DEVICE)}`,
          { timeout: 8000 }
        );

        applyLatest(result);
        failures = 0;
      } catch (error) {
        failures += 1;

        if (!stopped && failures >= 3) {
          setApiError(`${error.message} Đang tự kết nối lại…`);
        }
      } finally {
        busy = false;

        if (!stopped) {
          timer = setTimeout(
            poll,
            Math.min(2000 * 2 ** Math.min(failures, 3), 10000)
          );
        }
      }
    }

    poll();
    const tick = setInterval(() => setClock(Date.now()), 1000);

    let source = null;
    let sseTimer;
    let sseFails = 0;

    function connectSSE() {
      if (stopped) return;

      try {
        source = new EventSource(
          `${API}/api/telemetry/stream?device_id=${encodeURIComponent(DEVICE)}`
        );

        source.onopen = () => {
          sseFails = 0;
        };

        source.onmessage = event => {
          try {
            applyLatest(JSON.parse(event.data));
          } catch {
          }
        };

        source.onerror = () => {
          if (source && source.readyState === EventSource.CLOSED) {
            source.close();
            source = null;
            sseFails += 1;
            sseTimer = setTimeout(
              connectSSE,
              Math.min(2000 * 2 ** Math.min(sseFails, 4), 30000)
            );
          }
        };
      } catch {
        sseTimer = setTimeout(connectSSE, 5000);
      }
    }

    connectSSE();

    function wake() {
      if (document.visibilityState === 'visible') {
        failures = 0;
        poll();
      }
    }

    document.addEventListener('visibilitychange', wake);
    window.addEventListener('online', wake);

    return () => {
      stopped = true;
      clearTimeout(timer);
      clearTimeout(sseTimer);
      clearInterval(tick);
      document.removeEventListener('visibilitychange', wake);
      window.removeEventListener('online', wake);
      if (source) source.close();
    };
  }, [logEvent]);

  async function loadHistory(older = false) {
    if (historyLock.current) return;

    historyLock.current = true;
    setHistoryBusy(true);
    setHistoryError('');

    try {
      const before = older && cursor
        ? `&before_id=${encodeURIComponent(cursor)}`
        : '';

      const result = await request(
        `/api/telemetry/history?device_id=${encodeURIComponent(DEVICE)}&hours=24&limit=1000${before}`
      );

      if (!Array.isArray(result.data)) {
        throw new Error('Lịch sử trả về không hợp lệ.');
      }

      setHistory(previous => {
        const realRows = result.data.filter(
          item => item.simulated === false
        );

        const merged = older
          ? [...realRows, ...previous].filter(
              item => item.simulated === false
            )
          : realRows;

        return [...new Map(
          merged.map(item => [item.sample_id, item])
        ).values()].sort(
          (a, b) =>
            new Date(a.sampled_at || a.time) -
            new Date(b.sampled_at || b.time)
        );
      });

      setCursor(result.hasMore ? result.nextBeforeId : null);
    } catch (error) {
      setHistoryError(error.message);
    } finally {
      historyLock.current = false;
      setHistoryBusy(false);
    }
  }

  useEffect(() => {
    if (!command?.id) return;

    let stopped = false;
    let timer;
    let previousStatus = '';
    const deadline = Date.now() + 45000;

    async function poll() {
      let terminal = false;

      try {
        const result = await request(`/api/commands/${command.id}`);
        if (stopped) return;

        const record = result.data;
        if (!record?.status) {
          throw new Error('Chưa đọc được trạng thái lệnh.');
        }

        setNotice(
          `Lệnh ${record.status}: ${record.message || 'Đang chờ xác nhận.'}`
        );

        if (previousStatus !== record.status) {
          const failed = [
            'rejected', 'failed', 'publish_failed', 'timeout',
          ].includes(record.status);

          logEvent(
            `${record.status}: ${record.message || 'Cập nhật lệnh'}`,
            failed
              ? 'error'
              : ['applied', 'completed'].includes(record.status)
                ? 'success'
                : 'info'
          );

          previousStatus = record.status;
        }

        terminal = [
          'completed', 'rejected', 'failed', 'publish_failed', 'timeout',
        ].includes(record.status) ||
          (command.kind === 'mode' && record.status === 'applied');

        if (record.status === 'timeout') {
          setNotice(
            'Hết thời gian chờ xác nhận. Kiểm tra trạng thái thiết bị trước khi gửi lại.'
          );
        }
      } catch (error) {
        if (!stopped) {
          setNotice(`Chưa đọc được xác nhận: ${error.message}`);
        }
      }

      if (stopped) return;

      if (terminal || Date.now() >= deadline) {
        if (!terminal) {
          setNotice(
            'Chưa xác nhận được kết quả. Kiểm tra thiết bị trước khi gửi lại.'
          );
        }
        commandLock.current = false;
        setSending(false);
      } else {
        timer = setTimeout(poll, 1500);
      }
    }

    poll();

    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [command, logEvent]);

  const data = snapshot?.data?.simulated === false
    ? snapshot.data
    : null;

  const age = Number.isFinite(data?.dataAgeSeconds)
    ? data.dataAgeSeconds +
      Math.max(0, (clock - snapshot.fetchedAt) / 1000)
    : null;

  const online =
    !apiError &&
    snapshot?.mqttConnected === true &&
    data?.online === true &&
    age !== null &&
    age <= 20;

  const waterFault =
    String(data?.fault || '').trim().toUpperCase() === 'NO WATER (FLOAT)';

  const otherFault = Boolean(data?.fault) && !waterFault;

  const lowWater = data?.waterAvailable === false || waterFault;

  const canControl = online && !sending;

  const canWater =
    canControl &&
    data?.mode === 'MANUAL' &&
    data?.pump === 'OFF' &&
    data?.fsm === 'IDLE' &&
    data?.waterAvailable === true &&
    !data?.fault &&
    Number.isFinite(data?.soilMoisture) &&
    data.soilMoisture < 60;

  async function send(kind, values) {
    if (commandLock.current || !canControl) return;
    if (kind === 'pump' && !canWater) return;

    commandLock.current = true;
    setSending(true);
    setNotice('Đang gửi lệnh…');

    try {
      const result = await request(`/api/control/${kind}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ device_id: DEVICE, ...values }),
      });

      if (!result.command_id) {
        throw new Error('Phản hồi thiếu mã lệnh.');
      }

      setNotice('Đã gửi yêu cầu. Đang chờ thiết bị xác nhận…');
      logEvent(
        kind === 'mode'
          ? `Yêu cầu chuyển sang ${values.mode}.`
          : 'Yêu cầu tưới trong 2,5 giây.'
      );
      setCommand({ id: result.command_id, kind });
    } catch (error) {
      setNotice(
        `${error.message} Nếu mất kết nối, kiểm tra thiết bị trước khi gửi lại.`
      );
      logEvent(error.message, 'error');
      commandLock.current = false;
      setSending(false);
    }
  }

  const wateringReason = !online
    ? 'Chờ dữ liệu mới từ thiết bị.'
    : otherFault
      ? `Thiết bị cần kiểm tra: ${data.fault}`
      : lowWater
        ? 'Bình đang thiếu nước — vui lòng bổ sung nước. Tạm khóa tưới.'
        : sending
          ? 'Đang chờ xác nhận từ thiết bị.'
          : data?.mode !== 'MANUAL'
            ? 'Chọn Thủ công để sử dụng nút tưới.'
            : data?.waterAvailable !== true
              ? 'Chưa xác nhận được nguồn nước.'
              : !Number.isFinite(data?.soilMoisture)
                ? 'Chưa có số đo độ ẩm đất hợp lệ.'
                : data.soilMoisture >= 60
                  ? 'Đất đã đạt 60%: tạm chặn tưới.'
                  : data?.fsm !== 'IDLE' || data?.pump !== 'OFF'
                    ? 'Chờ thiết bị trở về IDLE và bơm OFF.'
                    : 'Sẵn sàng. Bơm tự dừng sau 2,5 giây.';

  const predictionTime = data?.predictionInputAt
    ? new Date(data.predictionInputAt).getTime()
    : NaN;

  const predictionTargetTime = data?.predictionTargetAt
    ? new Date(data.predictionTargetAt).getTime()
    : NaN;

  const sampledTime = Date.parse(data?.sampled_at || data?.time || '');

const predictionAge =
  Number.isFinite(predictionTime) &&
  Number.isFinite(sampledTime) &&
  age !== null
    ? (sampledTime - predictionTime) / 1000 + age
    : null;

  const correctSource =
    data?.soilPredictionSource === 'esp32_week2' &&
    data?.lightPredictionSource === 'esp32_week2';

  const correctHorizon =
    data?.predictionHorizonMinutes === 60 &&
    Number.isFinite(predictionTime) &&
    Number.isFinite(predictionTargetTime) &&
    Math.abs(
      predictionTargetTime - predictionTime - 60 * 60 * 1000
    ) <= 2000;

  const validSoil =
    Number.isFinite(data?.predictedSoil) &&
    data.predictedSoil >= 0 &&
    data.predictedSoil <= 100;

  const validLight =
    Number.isFinite(data?.predictedLight) &&
    data.predictedLight >= 0 &&
    data.predictedLight <= 200000;

  const predictionReady =
    online &&
    data?.simulated === false &&
    data?.aiReady === true &&
    !data?.fault &&
    data?.fsm !== 'FAULT' &&
    correctSource &&
    correctHorizon &&
    predictionAge !== null &&
    predictionAge >= -10 &&
    predictionAge <= 90 &&
    validSoil &&
    validLight;

  const lightReady = predictionReady;

  const backendMessage = typeof data?.aiMessage === 'string'
    ? data.aiMessage.trim()
    : '';

  let aiTitle = 'Đang chờ AI từ ESP32';
  let aiMessage = 'Chờ kit gửi kết quả dự đoán.';

  if (apiError) {
    aiTitle = 'Chưa kết nối được backend';
    aiMessage = 'Tạm ẩn dự đoán cho đến khi kết nối được khôi phục.';
  } else if (!data) {
    aiTitle = 'Đang chờ phần cứng thật';
    aiMessage =
      'Chưa nhận được bản tin cảm biến thật từ ESP32. ' +
      'Hãy bật kit và kết nối Wi-Fi, MQTT.';
  } else if (!online) {
    aiTitle = 'Đang chờ dữ liệu mới';
    aiMessage =
      'Thiết bị hoặc kết nối đang gián đoạn. ' +
      'Dự đoán cũ được tạm ẩn.';
  } else if (lowWater && !otherFault) {
    aiTitle = 'Cần bổ sung nước';
    aiMessage =
      'Phao đang báo thiếu nước. Vui lòng bổ sung nước; ' +
      'tưới và dự đoán đang tạm dừng.';
  } else if (data.fault || data.fsm === 'FAULT') {
    aiTitle = 'Thiết bị đang báo lỗi';
    aiMessage = data.fault || backendMessage ||
      'Chờ kit xử lý lỗi trước khi hiển thị dự đoán.';
  } else if (data.aiReady !== true) {
    aiTitle = 'AI trên kit chưa sẵn sàng';
    aiMessage = backendMessage ||
      'ESP32 đang thu thập dữ liệu hoặc chưa chạy được mô hình.';
  } else if (!correctSource) {
    aiTitle = 'Chưa xác nhận nguồn AI Week 2';
    aiMessage =
      'Cần bản tin có nguồn esp32_week2 cho cả độ ẩm và ánh sáng.';
  } else if (!predictionReady) {
    aiTitle = 'Đang chờ dự đoán hợp lệ';
    aiMessage =
      'Dự đoán đã cũ, thiếu thời điểm hoặc có giá trị không hợp lệ.';
  } else {
    aiTitle = 'AI trên ESP32 đã sẵn sàng';
    aiMessage = 'Độ ẩm đất và ánh sáng được dự đoán bởi mô hình Week 2 trên kit.';
  }

  const heroTitle = !online
    ? 'Chờ khu vườn kết nối'
    : otherFault
      ? 'Thiết bị cần kiểm tra'
      : lowWater
        ? 'Đã đến lúc bổ sung nước'
        : data?.fault || data?.fsm === 'FAULT'
          ? 'Thiết bị cần kiểm tra'
          : data?.pump === 'ON'
            ? 'Đang chăm sóc khu vườn'
            : 'Khu vườn trong tầm tay';

  const source = tab === 'history' ? history : samples;
  const overview = metric === 'all';
  const selected = METRICS.find(item => item.key === metric) || METRICS[0];
  const visibleMetrics = overview ? METRICS : [selected];

  const stride = Math.max(1, Math.ceil(source.length / 500));
  const plotted = source.filter(
    (_, index) => index % stride === 0 || index === source.length - 1
  );

  const ranges = Object.fromEntries(
    METRICS.map(item => {
      let min = 0;
      let max = item.max;
      for (const sample of source) {
        if (Number.isFinite(sample[item.key])) {
          min = Math.min(min, sample[item.key]);
          max = Math.max(max, sample[item.key]);
        }
      }
      return [item.key, { min, max }];
    })
  );

  const chartData = {
    labels: plotted.map(item => dateText(
      item.sampled_at || item.time,
      tab === 'history'
        ? { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }
        : { hour: '2-digit', minute: '2-digit', second: '2-digit' }
    )),
    datasets: visibleMetrics.map(item => ({
      label: `${item.name} (${item.unit})`,
      data: plotted.map(sample => {
        const value = sample[item.key];
        if (!Number.isFinite(value)) return null;
        const range = ranges[item.key];
        return overview
          ? (value - range.min) / (range.max - range.min) * 100
          : value;
      }),
      borderColor: item.color,
      backgroundColor: item.color,
      borderWidth: 2.5,
      pointRadius: plotted.length > 60 ? 0 : 2,
      pointHoverRadius: 5,
      tension: 0.2,
      spanGaps: false,
    })),
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    interaction: { intersect: false, mode: 'index' },
    plugins: {
      legend: {
        display: overview,
        position: 'bottom',
        labels: {
          color: '#94a3b8',
          usePointStyle: true,
          boxWidth: 8,
          boxHeight: 8,
          padding: 18,
          font: { size: 11 },
        },
      },
      tooltip: {
        backgroundColor: '#1e293b',
        titleColor: '#ffffff',
        bodyColor: '#e2e8f0',
        padding: 12,
        callbacks: {
          label(context) {
            const item = visibleMetrics[context.datasetIndex];
            return `${item.name}: ${fmt(
              plotted[context.dataIndex]?.[item.key], item.digits
            )} ${item.unit}`;
          },
          afterBody() {
            return overview ? ['Biểu đồ dùng thang tương đối.'] : [];
          },
        },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        border: { display: false },
        ticks: { color: '#64748b', maxTicksLimit: 6, maxRotation: 0 },
      },
      y: {
        min: overview || ['soilMoisture', 'humidity', 'light', 'vpd'].includes(metric)
          ? 0 : undefined,
        max: overview || ['soilMoisture', 'humidity'].includes(metric)
          ? 100 : undefined,
        border: { display: false },
        grid: { color: '#1e293b' },
        ticks: { color: '#64748b', maxTicksLimit: 6 },
        title: {
          display: true,
          text: overview ? 'Thang tương đối 0–100' : selected.unit,
          color: '#64748b',
        },
      },
    },
  };

  function exportCsv() {
    const fields = [
      'sampled_at', 'device_id', 'temperature', 'humidity',
      'soilMoisture', 'light', 'vpd', 'mode', 'pump', 'simulated',
    ];

    const quote = value => `"${String(value ?? '').replaceAll('"', '""')}"`;
    const csv = [
      fields.join(','),
      ...source.map(row => fields.map(key => quote(row[key])).join(',')),
    ].join('\r\n');

    const url = URL.createObjectURL(
      new Blob(['\uFEFF', csv], { type: 'text/csv;charset=utf-8;' })
    );
    const link = document.createElement('a');
    link.href = url;
    link.download = `plant-${tab}-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return (
    <>
      <style>{STYLES}</style>

      <main className="garden-app">
        <div className="garden-shell">
          <header className="garden-header">
            <div className="garden-brand">
              <div className="garden-logo"><Icon name="leaf" size={29} /></div>
              <div>
                <div className="garden-overline">SMART GARDEN / AIoT</div>
                <h1>Plant Command<span>.</span></h1>
              </div>
            </div>

            <div className="garden-header-actions">
              <span className="garden-device">{DEVICE}</span>
              <span className={`garden-pill ${online ? 'is-green' : 'is-amber'}`}>
                <i />{online ? 'Trực tuyến' : 'Chờ kết nối'}
              </span>
              <button
                className="garden-icon-button"
                aria-label="Mở cài đặt"
                aria-expanded={settings}
                onClick={() => setSettings(value => !value)}
              >
                <Icon name="settings" />
              </button>
            </div>
          </header>

          {settings && (
            <section className="garden-card garden-settings">
              <div>
                <h2>Cài đặt điều khiển</h2>
                <p>Điều khiển trực tiếp từ web. Bơm chỉ hoạt động khi đủ điều kiện.</p>
                <p className="garden-api-address">API: {API}</p>
              </div>
              <button className="garden-soft-button" onClick={() => setSettings(false)}>
                Đóng
              </button>
            </section>
          )}

          <section className="garden-hero">
            <div className="garden-hero-copy">
              <div className="garden-overline">
                <span className={`garden-dot ${online ? '' : 'is-amber'}`} />
                MỖI NGÀY MỘT CHÚT XANH
              </div>
              <h2>{heroTitle}<span>.</span></h2>
              <p>Theo dõi môi trường, dự đoán độ ẩm và chăm sóc cây tại một nơi.</p>
              <div className="garden-hero-tags">
                <span className={`garden-pill ${data?.simulated ? 'is-amber' : 'is-green'}`}>
                  {data?.simulated === true
                    ? 'Đầu vào mô phỏng'
                    : data?.simulated === false
                      ? 'Cảm biến thực tế'
                      : 'Chờ dữ liệu'}
                </span>
                <span>AI chạy trên ESP32 · Week 2</span>
              </div>
            </div>

            <div className="garden-hero-stats">
              <div>
                <Icon name="clock" />
                <span>Tuổi dữ liệu</span>
                <strong>{fmt(age)}<small> giây</small></strong>
                <p>{online ? 'Đang cập nhật' : 'Chờ mẫu mới'}</p>
              </div>
              <div>
                <Icon name="activity" />
                <span>Trạng thái thiết bị</span>
                <strong>{online ? data?.fsm ?? '—' : '—'}</strong>
                <p>{online ? `Chế độ ${data?.mode ?? '—'}` : 'Chưa xác nhận'}</p>
              </div>
            </div>
          </section>

          {apiError && (
            <div className="garden-alert" role="alert">
              <Icon name="alert" />
              <span>
                Không đọc được API: {apiError}.
                {' Tạm ẩn số đo trực tiếp và khóa điều khiển.'}
              </span>
            </div>
          )}

          {online && lowWater && (
            <div className="garden-alert garden-water-warning" role="status">
              <Icon name="alert" />
              <span>
                Bình đang thiếu nước — vui lòng bổ sung nước.
                {' Bơm tạm khóa để tránh chạy khô.'}
              </span>
            </div>
          )}

          {data?.fault && otherFault && (
            <div className="garden-alert" role="alert">
              <Icon name="alert" />
              <span>Lỗi thiết bị: {data.fault}</span>
            </div>
          )}

          <section className="garden-sensors" aria-label="Thông số cảm biến">
            {METRICS.map(item => (
              <article
                key={item.key}
                className={`garden-card garden-sensor ${!online ? 'is-stale' : ''}`}
                style={{ '--sensor-color': item.color, '--sensor-tint': item.tint }}
              >
                <div className="garden-sensor-head">
                  <span>{item.name}</span>
                  <div className="garden-sensor-icon"><Icon name={item.icon} /></div>
                </div>
                <div className="garden-sensor-value">
                  {online ? fmt(data?.[item.key], item.digits) : '—'}
                  <small>{item.unit}</small>
                </div>
                <div className="garden-meter">
                  <span style={{
                    width: `${online && Number.isFinite(data?.[item.key])
                      ? Math.min(100, Math.max(0, data[item.key] / item.max * 100))
                      : 0}%`,
                  }} />
                </div>
                <p>{item.hint}</p>
              </article>
            ))}
          </section>

          <div className="garden-workspace">
            <div className="garden-main">
              <WateringPot
                data={data}
                online={online}
              />

              <nav className="garden-tabs" aria-label="Nội dung theo dõi">
                {TABS.map(([key, icon, label]) => (
                  <button
                    key={key}
                    className={tab === key ? 'is-active' : ''}
                    aria-pressed={tab === key}
                    onClick={() => {
                      setTab(key);
                      if (key === 'history' && !history.length) loadHistory();
                    }}
                  >
                    <Icon name={icon} size={18} />{label}
                  </button>
                ))}
              </nav>

              <div
                className={`garden-ai-status ${predictionReady ? 'is-ready' : 'is-waiting'}`}
                role="status"
              >
                <div className="garden-ai-status-icon">
                  <Icon name={predictionReady ? 'spark' : 'alert'} />
                </div>
                <div>
                  <strong>{aiTitle}</strong>
                  <p>{aiMessage}</p>
                </div>
                {tab !== 'ai' && (
                  <button
                    className="garden-icon-button"
                    aria-label="Xem chi tiết AI"
                    onClick={() => setTab('ai')}
                  >
                    <Icon name="arrow" size={19} />
                  </button>
                )}
              </div>

              {(tab === 'live' || tab === 'history') && (
                <section className="garden-card garden-chart-panel">
                  <div className="garden-section-head">
                    <div>
                      <div className="garden-overline">ENVIRONMENT TELEMETRY</div>
                      <h2>{tab === 'history' ? 'Nhìn lại khu vườn' : 'Nhịp sống khu vườn'}</h2>
                      <p>
                        {tab === 'history'
                          ? `${history.length} mẫu đã tải trong 24 giờ${cursor ? ' · còn mẫu cũ hơn' : ''}`
                          : `${samples.length}/60 mẫu gần nhất kể từ khi mở trang`}
                      </p>
                    </div>
                    <button
                      className="garden-icon-button"
                      disabled={!source.length}
                      onClick={exportCsv}
                      aria-label="Tải CSV"
                    >
                      <Icon name="download" />
                    </button>
                  </div>

                  <div className="garden-metric-switch">
                    <button
                      className={overview ? 'is-active' : ''}
                      aria-pressed={overview}
                      onClick={() => setMetric('all')}
                    >
                      Tổng thể
                    </button>
                    {METRICS.map(item => (
                      <button
                        key={item.key}
                        className={metric === item.key ? 'is-active' : ''}
                        aria-pressed={metric === item.key}
                        onClick={() => setMetric(item.key)}
                      >
                        {item.name}
                      </button>
                    ))}
                  </div>

                  {overview && (
                    <div className="garden-chart-help">
                      <p>
                        Năm thông số dùng thang tương đối. Chạm vào điểm để xem
                        số đo gốc; bấm chú giải để ẩn hoặc hiện từng đường.
                      </p>
                      <details>
                        <summary>Xem khoảng quy đổi</summary>
                        <p>
                          {METRICS.map(item =>
                            `${item.name}: ${fmt(ranges[item.key].min, item.digits)}–${
                              fmt(ranges[item.key].max, item.digits)
                            } ${item.unit}`
                          ).join(' · ')}
                        </p>
                        <p>Thang tương đối không phải điểm sức khỏe cây.</p>
                      </details>
                    </div>
                  )}

                  <div className="garden-chart">
                    {source.length ? (
                      <Line
                        key={`${tab}-${metric}`}
                        data={chartData}
                        options={chartOptions}
                      />
                    ) : (
                      <div className="garden-empty">
                        <Icon name="activity" size={35} />
                        <h3>{historyBusy ? 'Đang tải dữ liệu…' : 'Chưa có mẫu để hiển thị'}</h3>
                        <p>
                          {tab === 'history'
                            ? 'Bấm tải lại để đọc dữ liệu từ backend.'
                            : 'Chờ ESP32 gửi dữ liệu cảm biến thật.'}
                        </p>
                      </div>
                    )}
                  </div>

                  {historyError && tab === 'history' && (
                    <p className="garden-error" role="alert">{historyError}</p>
                  )}

                  <div className="garden-chart-footer">
                    <span>
                      {overview ? 'Tổng thể 5 thông số' : selected.name}
                      {stride > 1 ? ` · ${plotted.length} điểm hiển thị` : ''}
                    </span>
                    {tab === 'history' ? (
                      <div className="garden-inline-actions">
                        <button
                          className="garden-text-button"
                          disabled={historyBusy}
                          onClick={() => loadHistory()}
                        >
                          {historyBusy ? 'Đang tải…' : 'Tải lại'}
                        </button>
                        {cursor && (
                          <button
                            className="garden-text-button"
                            disabled={historyBusy}
                            onClick={() => loadHistory(true)}
                          >
                            Tải thêm
                          </button>
                        )}
                      </div>
                    ) : <span>Thời gian lấy mẫu thực tế</span>}
                  </div>
                </section>
              )}

              {tab === 'events' && (
                <section className="garden-card garden-content-panel">
                  <div className="garden-section-head">
                    <div>
                      <div className="garden-overline">ACTIVITY LOG</div>
                      <h2>Nhật ký phiên làm việc</h2>
                      <p>Các sự kiện kể từ khi mở trang, không phải toàn bộ lịch sử thiết bị.</p>
                    </div>
                  </div>

                  {!events.length ? (
                    <div className="garden-empty">Chưa có sự kiện.</div>
                  ) : (
                    <div className="garden-events">
                      {events.map(event => (
                        <article className="garden-event" key={event.id}>
                          <span className={`garden-event-dot ${event.status}`} />
                          <div>
                            <small>
                              {event.status === 'error'
                                ? 'CẦN KIỂM TRA'
                                : event.status === 'success'
                                  ? 'XÁC NHẬN'
                                  : 'CẬP NHẬT'}
                            </small>
                            <p>{event.message}</p>
                          </div>
                          <time>
                            {dateText(event.time, {
                              hour: '2-digit', minute: '2-digit', second: '2-digit',
                            })}
                          </time>
                        </article>
                      ))}
                    </div>
                  )}
                </section>
              )}

              {tab === 'ai' && (
                <section className="garden-card garden-content-panel">
                  <div className="garden-section-head">
                    <div>
                      <div className="garden-overline">PREDICTIVE INSIGHT</div>
                      <h2>Nhìn trước {data?.predictionHorizonMinutes ?? 60} phút</h2>
                      <p>Mô hình Week 2 trên ESP32 dự đoán độ ẩm đất và ánh sáng.</p>
                    </div>
                  </div>

                  <span className={`garden-pill ${data?.simulated ? 'is-amber' : 'is-green'}`}>
                    {data?.simulated === true
                      ? 'Đầu vào mô phỏng'
                      : data?.simulated === false
                        ? 'Đầu vào cảm biến'
                        : 'Chưa có đầu vào'}
                  </span>

                  <div className="garden-predictions">
                    <div className="garden-prediction soil">
                      <Icon name="drop" size={28} />
                      <span>Độ ẩm đất · LSTM</span>
                      <strong>
                        {predictionReady ? fmt(data.predictedSoil, 2) : '—'}
                        <small> %</small>
                      </strong>
                      <p>
                        {data?.soilPredictionSource === 'esp32_week2'
                          ? 'Mô hình Week 2 chạy trên ESP32'
                          : 'Chưa xác nhận nguồn dự đoán'}
                      </p>
                    </div>
                    <div className="garden-prediction light">
                      <Icon name="sun" size={28} />
                      <span>Ánh sáng · AI trên ESP32</span>
                      <strong>
                        {lightReady ? fmt(data.predictedLight, 0) : '—'}
                        <small> Lux</small>
                      </strong>
                      <p>
                        {data?.lightPredictionSource === 'esp32_week2'
                          ? 'Mô hình Week 2 chạy trên ESP32'
                          : 'Chưa xác nhận nguồn dự báo'}
                      </p>
                    </div>
                  </div>

                  <div className="garden-detail">
                    <span>Thời điểm đầu vào</span>
                    <strong>
                      {predictionReady ? dateText(data.predictionInputAt) : '—'}
                    </strong>
                  </div>
                  <div className="garden-detail">
                    <span>Thời điểm được dự báo</span>
                    <strong>
                      {predictionReady ? dateText(data.predictionTargetAt) : '—'}
                    </strong>
                  </div>
                  <div className="garden-detail">
                    <span>Trạng thái dự đoán</span>
                    <strong>{predictionReady ? 'Sẵn sàng' : 'Chưa sử dụng'}</strong>
                  </div>

                  <div className="garden-ai-explanation">
                    <Icon name="leaf" size={20} />
                    <p>
                      Mô hình Week 2 chạy trực tiếp trên ESP32.
                      Trong chế độ AUTO, firmware kết hợp điều kiện cảm biến
                      và dự đoán để điều khiển tưới.
                      Backend chuyển tiếp dữ liệu và lệnh điều khiển.
                      Độ chính xác của mô hình với cảm biến thật chưa được xác nhận.
                    </p>
                  </div>
                </section>
              )}
            </div>

            <aside className="garden-card garden-controls">
              <div className="garden-overline">IRRIGATION CONTROL</div>
              <h2>Chăm sóc cây</h2>
              <p className="garden-control-subtitle">Một thao tác, thêm một chút xanh.</p>

              <div className="garden-wifi-box">
                <div className="garden-wifi-icon">
                  <Icon name="wifi" size={20} />
                </div>
                <div>
                  <span>TRẠNG THÁI TÍN HIỆU</span>
                  <strong>{online ? 'Đang nhận dữ liệu' : 'Gián đoạn / Offline'}</strong>
                </div>
                <span className={`garden-pill ${online ? 'is-green' : 'is-amber'}`}>
                  {online ? 'Thiết bị online' : 'Chưa nhận dữ liệu'}
                </span>
              </div>

              <div className={`garden-pump ${online && data?.pump === 'ON' ? 'is-running' : ''}`}>
                <div className="garden-pump-symbol"><Icon name="drop" size={29} /></div>
                <div>
                  <span>BƠM NƯỚC</span>
                  <strong>
                    {!online ? 'Chưa xác nhận' : data?.pump === 'ON' ? 'Đang tưới' : 'Đang nghỉ'}
                  </strong>
                </div>
                <span className={`garden-pill ${online && data?.pump === 'ON' ? 'is-green' : 'is-neutral'}`}>
                  {online ? data?.pump ?? '—' : '—'}
                </span>
              </div>

              <div className="garden-detail">
                <span>Nguồn nước</span>
                <strong>
                  {!online
                    ? 'Chưa xác nhận'
                    : data?.waterAvailable === true
                      ? 'Có nước'
                      : data?.waterAvailable === false
                        ? 'Hết nước'
                        : 'Chưa xác nhận'}
                </strong>
              </div>

              <div className="garden-detail">
                <span>Chế độ đã xác nhận</span>
                <strong>{online ? data?.mode ?? '—' : '—'}</strong>
              </div>

              <div className="garden-mode-label">CHỌN CHẾ ĐỘ</div>

              <div className="garden-mode-switch">
                {['AUTO', 'MANUAL'].map(mode => {
                  const active = online && data?.mode === mode;
                  const blocked = !canControl || active;

                  return (
                    <button
                      key={mode}
                      className={`garden-mode-button ${
                        mode === 'AUTO' ? 'automatic' : 'manual'
                      } ${active ? 'is-selected' : ''}`}
                      disabled={blocked}
                      aria-pressed={active}
                      onClick={() => send('mode', { mode })}
                    >
                      <span className="garden-mode-top">
                        <Icon name={mode === 'AUTO' ? 'spark' : 'hand'} size={24} />
                        {active && <Icon name="check" size={17} />}
                      </span>
                      <strong>{mode === 'AUTO' ? 'Tự động' : 'Thủ công'}</strong>
                      <small>{active ? 'Đang chọn' : mode}</small>
                    </button>
                  );
                })}
              </div>

              <button
                className="garden-water-button"
                disabled={!canWater}
                onClick={() => send('pump', { state: 'ON', duration_ms: 2500 })}
              >
                <Icon name="drop" size={24} />
                <span>{sending ? 'Đang xử lý…' : 'Tưới ngay'}</span>
                <small>2,5 s</small>
              </button>

              <p className="garden-control-reason">{wateringReason}</p>

              <div className="garden-command-notice" role="status">
                {notice || 'Chưa gửi lệnh trong phiên này.'}
              </div>

              {command && (
                <a
                  className="garden-command-link"
                  href={`${API}/api/commands/${command.id}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  Xem xác nhận lệnh ↗
                </a>
              )}
            </aside>
          </div>

          <footer className="garden-footer">
            <span><Icon name="leaf" size={16} />PLANT COMMAND / AIoT</span>
            <span>
              API {apiError ? 'lỗi kết nối' : snapshot ? 'đã kết nối' : 'đang chờ'}
              {' · '}
              MQTT {apiError
                ? 'chưa xác nhận'
                : snapshot?.mqttConnected ? 'đã kết nối' : 'đang chờ'}
            </span>
            <span>
              {data?.sampled_at
                ? `Mẫu gần nhất: ${dateText(data.sampled_at)}`
                : 'Chưa nhận mẫu'}
            </span>
          </footer>
        </div>
      </main>
    </>
  );
}

const STYLES = `
  :root {
    font-family: Inter, "Segoe UI", Arial, sans-serif;
    color: #e2e8f0;
    background: #090d16;
    font-synthesis: none;
    text-rendering: optimizeLegibility;
    -webkit-font-smoothing: antialiased;
    color-scheme: dark;
  }

  body {
    margin: 0;
    min-width: 320px;
    display: block;
    background: #090d16;
  }

  #root {
    width: 100%;
    max-width: none;
    margin: 0;
    padding: 0;
    text-align: left;
  }

  .garden-app, .garden-app * { box-sizing: border-box; }
  .garden-app {
    min-height: 100vh;
    padding: 30px;
    color: #e2e8f0;
    background:
      radial-gradient(ellipse at 10% 0%, #064e3b33 0, transparent 40%),
      radial-gradient(ellipse at 90% 10%, #78350f22 0, transparent 35%),
      #090d16;
    font: 14px/1.55 Inter, "Segoe UI", Arial, sans-serif;
  }

  .garden-app h1, .garden-app h2, .garden-app h3,
  .garden-app p { margin: 0; }
  .garden-app button, .garden-app input { font: inherit; }
  .garden-app button {
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
  }
  .garden-app button:disabled { cursor: not-allowed; }
  .garden-app button:focus-visible,
  .garden-app input:focus-visible,
  .garden-app a:focus-visible,
  .garden-app summary:focus-visible {
    outline: 3px solid #38bdf8;
    outline-offset: 4px;
  }
  .garden-app svg { flex-shrink: 0; }
  .garden-shell { max-width: 1500px; margin: auto; }
  
  .garden-card {
    background: linear-gradient(145deg, #131c2e, #0d1422);
    border: 1px solid #1e293b;
    border-radius: 24px;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.05);
  }

  .garden-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 20px;
    background: linear-gradient(145deg, #131c2e, #0f172a);
    border: 1px solid #1e293b;
    border-radius: 24px;
    padding: 21px 26px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.07);
  }
  .garden-brand { display: flex; align-items: center; gap: 15px; min-width: 0; }
  
  .garden-logo {
    width: 53px;
    height: 53px;
    display: grid;
    place-items: center;
    color: white;
    border-radius: 17px;
    background: linear-gradient(145deg, #34d399, #059669);
    border: 1px solid #6ee7b7;
    box-shadow: inset 0 2px 0 rgba(255, 255, 255, 0.4), 0 5px 0 #047857, 0 10px 20px rgba(5, 150, 105, 0.4);
  }
  .garden-overline {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 10px;
    letter-spacing: 1.7px;
    font-weight: 800;
    color: #34d399;
  }
  .garden-brand h1 { font-size: 26px; letter-spacing: -.9px; line-height: 1.3; color: #f8fafc; }
  .garden-brand h1 span { color: #34d399; }
  .garden-header-actions { display: flex; align-items: center; gap: 13px; }
  .garden-device {
    font: 12px ui-monospace, Consolas, monospace;
    color: #94a3b8;
    padding-right: 15px;
    border-right: 1px solid #1e293b;
  }
  .garden-pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 7px;
    padding: 6px 11px;
    border-radius: 30px;
    font-size: 11px;
    font-weight: 750;
    white-space: nowrap;
    border: 1px solid transparent;
  }
  .garden-pill i, .garden-dot {
    display: inline-block;
    width: 7px;
    height: 7px;
    background: currentColor;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .garden-pill.is-green { color: #34d399; background: rgba(52, 211, 153, 0.12); border-color: rgba(52, 211, 153, 0.3); }
  .garden-pill.is-amber { color: #fbbf24; background: rgba(251, 191, 36, 0.12); border-color: rgba(251, 191, 36, 0.3); }
  .garden-pill.is-neutral { color: #94a3b8; background: rgba(148, 163, 184, 0.12); border-color: rgba(148, 163, 184, 0.3); }
  .garden-dot { color: #34d399; }
  .garden-dot.is-amber { color: #fbbf24; }

  .garden-icon-button {
    display: inline-grid;
    place-items: center;
    width: 40px;
    height: 40px;
    padding: 0;
    border: 1px solid #334155;
    border-radius: 13px;
    color: #cbd5e1;
    background: linear-gradient(145deg, #1e293b, #0f172a);
    box-shadow: 0 4px 0 #090d16, 0 6px 12px rgba(0, 0, 0, 0.4);
    transition: transform .15s, box-shadow .15s;
    flex-shrink: 0;
  }
  .garden-icon-button:hover:not(:disabled) { color: #34d399; transform: translateY(-1px); }
  .garden-icon-button:active:not(:disabled) { transform: translateY(3px); box-shadow: 0 1px 0 #090d16; }
  .garden-icon-button:disabled { opacity: .5; }

  .garden-hero {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 28px;
    margin: 24px 0;
    padding: 35px;
    border: 1px solid #1e3a34;
    border-radius: 28px;
    background:
      radial-gradient(ellipse at 85% 10%, rgba(52, 211, 153, 0.08), transparent 60%),
      linear-gradient(115deg, #0f1c2e, #0b1320);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05), 0 10px 30px rgba(0, 0, 0, 0.5);
  }
  .garden-hero-copy { max-width: 650px; }
  .garden-hero h2 {
    margin: 12px 0 10px;
    color: #f8fafc;
    font-size: clamp(25px, 2.6vw, 37px);
    line-height: 1.2;
    letter-spacing: -1.1px;
  }
  .garden-hero h2 > span { color: #34d399; }
  .garden-hero-copy > p { color: #94a3b8; font-size: 13px; }
  .garden-hero-tags { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-top: 19px; }
  .garden-hero-tags > span:last-child { font-size: 11px; color: #94a3b8; }
  
  .garden-hero-stats { display: grid; grid-template-columns: repeat(2, 1fr); gap: 13px; min-width: 310px; }
  .garden-hero-stats > div {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    padding: 18px 21px;
    background: linear-gradient(145deg, #1e293b, #0f172a);
    border: 1px solid #334155;
    border-radius: 20px;
    box-shadow: 0 6px 15px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.08);
  }
  .garden-hero-stats svg { color: #34d399; margin-bottom: 9px; width: 20px; height: 20px; }
  .garden-hero-stats span { color: #94a3b8; font-size: 11px; }
  .garden-hero-stats strong { color: #34d399; font-size: 28px; line-height: 1.5; text-shadow: 0 2px 4px rgba(0,0,0,0.5); }
  .garden-hero-stats small { font-size: 11px; font-weight: 500; }
  .garden-hero-stats p { color: #64748b; font-size: 10px; }

  .garden-sensors { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 16px; margin-bottom: 26px; }
  .garden-sensor { 
    padding: 20px; 
    min-width: 0; 
    background: linear-gradient(145deg, #131c2e, #0d1422);
    border: 1px solid #1e293b;
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.05);
    transition: transform .2s, box-shadow .2s; 
  }
  .garden-sensor:hover { transform: translateY(-3px); box-shadow: 0 12px 30px rgba(0, 0, 0, 0.6); }
  .garden-sensor.is-stale { opacity: .5; }
  .garden-sensor-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
  .garden-sensor-head > span { font-size: 12px; color: #94a3b8; font-weight: 650; }
  .garden-sensor-icon {
    display: grid; place-items: center; width: 37px; height: 37px;
    border-radius: 12px; color: var(--sensor-color); background: var(--sensor-tint);
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.4);
  }
  
  .garden-sensor-value { 
    margin: 17px 0; 
    font-size: clamp(24px, 2.3vw, 35px); 
    font-weight: 800; 
    letter-spacing: -1px; 
    color: var(--sensor-color); 
    text-shadow: 0 2px 8px rgba(0,0,0,0.6);
  }
  .garden-sensor-value small { margin-left: 5px; color: #94a3b8; font-size: 12px; font-weight: 550; letter-spacing: 0; }
  .garden-meter { height: 6px; border-radius: 10px; overflow: hidden; background: #0f172a; border: 1px solid #1e293b; }
  .garden-meter span { display: block; height: 100%; border-radius: inherit; background: var(--sensor-color); box-shadow: 0 0 10px var(--sensor-color); transition: width .3s; }
  .garden-sensor > p { margin-top: 10px; font-size: 10px; color: #64748b; }

  .garden-workspace { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 23px; align-items: start; }
  .garden-main { min-width: 0; }
  
  .garden-tabs { display: flex; gap: 7px; flex-wrap: wrap; margin-bottom: 19px; padding-bottom: 15px; border-bottom: 1px solid #1e293b; }
  .garden-tabs button {
    display: flex; align-items: center; gap: 8px; padding: 10px 15px;
    border: 1px solid #1e293b; border-radius: 12px; color: #94a3b8;
    background: linear-gradient(145deg, #131c2e, #0d1422); font-size: 12px; font-weight: 700;
    box-shadow: 0 4px 0 #090d16;
  }
  .garden-tabs button:hover { background: #1e293b; color: #34d399; }
  .garden-tabs button.is-active {
    background: linear-gradient(145deg, #064e3b, #022c22); border-color: #059669; color: #34d399;
    box-shadow: 0 4px 0 #022c22, 0 6px 15px rgba(5, 150, 105, 0.3);
  }
  
  .garden-ai-status {
    display: flex; align-items: center; gap: 12px; padding: 15px 17px;
    margin-bottom: 18px; border-radius: 17px; border: 1px solid #78350f;
    background: linear-gradient(145deg, #1c1408, #110c04); color: #fbbf24;
    box-shadow: 0 6px 15px rgba(0,0,0,0.4);
  }
  .garden-ai-status.is-ready { border-color: #064e3b; background: linear-gradient(145deg, #062c22, #021a14); color: #34d399; }
  .garden-ai-status-icon { flex-shrink: 0; }
  .garden-ai-status > div:nth-child(2) { flex: 1; min-width: 0; }
  .garden-ai-status strong { display: block; font-size: 12px; }
  .garden-ai-status p { font-size: 11px; margin-top: 3px; opacity: .9; line-height: 1.7; }
  .garden-ai-status .garden-icon-button { width: 33px; height: 33px; background: #1e293b; }

  .garden-chart-panel, .garden-content-panel { padding: 25px; }
  .garden-section-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 15px; margin-bottom: 22px; }
  .garden-section-head h2 { margin: 6px 0; font-size: 22px; letter-spacing: -.6px; color: #f8fafc; }
  .garden-section-head p { color: #94a3b8; font-size: 12px; }
  
  .garden-metric-switch { display: flex; gap: 7px; flex-wrap: wrap; margin-bottom: 15px; }
  .garden-metric-switch button {
    background: #131c2e; border: 1px solid #1e293b; color: #94a3b8;
    padding: 7px 11px; border-radius: 9px; font-size: 11px;
    box-shadow: 0 2px 0 #090d16;
  }
  .garden-metric-switch button.is-active { background: #064e3b; border-color: #059669; color: #34d399; font-weight: 750; box-shadow: 0 2px 0 #022c22; }
  
  .garden-chart-help { color: #94a3b8; font-size: 10px; line-height: 1.8; margin-bottom: 20px; }
  .garden-chart-help summary { cursor: pointer; margin-top: 4px; color: #34d399; }
  .garden-chart { height: 340px; }
  .garden-chart-footer { display: flex; justify-content: space-between; align-items: center; gap: 12px; border-top: 1px solid #1e293b; padding-top: 15px; margin-top: 16px; font-size: 10px; color: #94a3b8; }
  .garden-inline-actions { display: flex; gap: 15px; }
  .garden-text-button { background: none; border: 0; color: #34d399; font-size: 11px; padding: 0; font-weight: 650; }
  .garden-text-button:disabled { opacity: .5; }
  .garden-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; text-align: center; color: #64748b; min-height: 240px; height: 100%; }
  .garden-empty h3 { color: #94a3b8; font-size: 17px; }
  .garden-empty p { font-size: 12px; }

  .garden-controls { padding: 25px; position: sticky; top: 20px; }
  .garden-controls > h2 { font-size: 24px; letter-spacing: -.7px; margin-top: 6px; color: #f8fafc; }
  .garden-control-subtitle { color: #94a3b8; font-size: 11px; margin-top: 5px !important; }
  
  .garden-wifi-box {
    display: flex; align-items: center; gap: 12px;
    padding: 14px 16px; margin-top: 15px;
    background: linear-gradient(145deg, #1e293b, #0f172a);
    border: 1px solid #334155; border-radius: 16px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.05);
  }
  .garden-wifi-icon {
    display: grid; place-items: center; width: 38px; height: 38px;
    background: #0f172a; border-radius: 12px; color: #38bdf8;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.5);
  }
  .garden-wifi-box > div { flex: 1; min-width: 0; }
  .garden-wifi-box span { display: block; color: #64748b; font-size: 9px; letter-spacing: 1px; font-weight: 700; }
  .garden-wifi-box strong { display: block; font-size: 12px; color: #f8fafc; margin-top: 2px; }

  .garden-pump { display: flex; align-items: center; gap: 12px; padding: 15px 0 18px; margin-top: 10px; }
  .garden-pump-symbol { display: grid; place-items: center; width: 52px; height: 52px; background: #1e293b; border-radius: 17px; color: #64748b; box-shadow: inset 0 2px 5px rgba(0,0,0,0.5); }
  .garden-pump.is-running .garden-pump-symbol { background: #064e3b; color: #34d399; box-shadow: inset 0 2px 5px rgba(0,0,0,0.5), 0 0 15px rgba(52,211,153,0.4); animation: garden-pulse 1.8s ease-in-out infinite; }
  .garden-pump > div:nth-child(2) { flex: 1; }
  .garden-pump div > span { display: block; color: #64748b; font-size: 9px; letter-spacing: 1px; }
  .garden-pump strong { display: block; font-size: 15px; margin-top: 4px; color: #f8fafc; }
  .garden-pump > .garden-pill { font-size: 9px; padding: 4px 8px; }
  
  .garden-detail { display: flex; justify-content: space-between; align-items: flex-start; gap: 14px; padding: 12px 0; border-bottom: 1px solid #1e293b; font-size: 11px; }
  .garden-detail > span { color: #94a3b8; }
  .garden-detail strong { color: #f8fafc; text-align: right; font-weight: 650; overflow-wrap: anywhere; }
  
  .garden-mode-label { margin-top: 23px; margin-bottom: 12px; color: #94a3b8; font-size: 9px; font-weight: 800; letter-spacing: 1.4px; }
  .garden-mode-switch { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 26px; }

  .garden-mode-button {
    position: relative;
    min-height: 113px;
    text-align: left;
    border: 1px solid #334155;
    border-radius: 17px;
    padding: 14px;
    color: #94a3b8;
    background: linear-gradient(155deg, #1e293b, #0f172a);
    box-shadow: inset 0 2px 0 rgba(255,255,255,0.08), 0 6px 0 #090d16, 0 10px 20px rgba(0, 0, 0, 0.5);
    transition: transform .16s, box-shadow .16s, background .16s;
  }
  .garden-mode-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
  .garden-mode-button strong { display: block; font-size: 15px; line-height: 1.5; color: #f8fafc; }
  .garden-mode-button small { display: block; font-size: 9px; letter-spacing: .6px; opacity: .78; margin-top: 2px; }
  .garden-mode-button:hover:not(:disabled) { transform: translateY(-2px); box-shadow: inset 0 2px 0 rgba(255,255,255,0.12), 0 8px 0 #090d16, 0 15px 25px rgba(0, 0, 0, 0.6); }
  .garden-mode-button:active:not(:disabled) { transform: translateY(4px); box-shadow: inset 0 1px 0 rgba(255,255,255,0.05), 0 2px 0 #090d16; }
  .garden-mode-button:disabled:not(.is-selected) { opacity: .4; box-shadow: 0 3px 0 #090d16; }
  .garden-mode-button.is-selected { cursor: default; transform: translateY(2px); }
  
  .garden-mode-button.automatic.is-selected {
    color: white; border-color: #059669;
    background: linear-gradient(145deg, #059669, #022c22);
    box-shadow: inset 0 2px 0 rgba(255,255,255,0.25), 0 4px 0 #011c16, 0 10px 22px rgba(5, 150, 105, 0.4);
  }
  .garden-mode-button.manual.is-selected {
    color: #fff; border-color: #0284c7;
    background: linear-gradient(145deg, #0284c7, #033a69);
    box-shadow: inset 0 2px 0 rgba(255,255,255,0.25), 0 4px 0 #01223f, 0 10px 22px rgba(2, 132, 199, 0.4);
  }

  .garden-water-button {
    display: flex; align-items: center; justify-content: center; gap: 10px;
    width: 100%; padding: 16px; margin-top: 23px;
    border: 1px solid #059669; border-radius: 16px;
    color: #fff; font-weight: 800; font-size: 16px;
    background: linear-gradient(165deg, #10b981, #047857);
    box-shadow: inset 0 2px 0 rgba(255,255,255,0.3), 0 6px 0 #022c22, 0 12px 25px rgba(16, 185, 129, 0.4);
    transition: transform .16s, box-shadow .16s;
  }
  .garden-water-button small { margin-left: auto; padding-left: 12px; border-left: 1px solid rgba(255,255,255,0.3); font-size: 11px; font-weight: 600; }
  .garden-water-button > span { flex: 1; text-align: left; }
  .garden-water-button:hover:not(:disabled) { transform: translateY(-2px); box-shadow: inset 0 2px 0 rgba(255,255,255,0.35), 0 8px 0 #022c22, 0 16px 30px rgba(16, 185, 129, 0.5); }
  .garden-water-button:active:not(:disabled) { transform: translateY(5px); box-shadow: inset 0 1px 0 rgba(255,255,255,0.2), 0 1px 0 #022c22; }
  .garden-water-button:disabled {
    color: #64748b; border-color: #1e293b; background: linear-gradient(#1e293b, #0f172a);
    box-shadow: inset 0 2px 0 rgba(255,255,255,0.05), 0 4px 0 #090d16;
  }
  
  .garden-control-reason { color: #94a3b8; font-size: 10px; line-height: 1.8; margin-top: 15px !important; }
  .garden-command-notice { padding: 12px; margin-top: 17px; background: #0b1120; border: 1px dashed #334155; border-radius: 12px; color: #94a3b8; font-size: 10px; overflow-wrap: anywhere; }
  .garden-command-link { display: inline-block; margin-top: 12px; color: #34d399; font-size: 11px; text-decoration: none; }
  .garden-command-link:hover { text-decoration: underline; }

  .garden-predictions { display: grid; grid-template-columns: 1fr 1fr; gap: 17px; margin: 22px 0; }
  .garden-prediction { padding: 23px; border-radius: 19px; border: 1px solid #064e3b; background: linear-gradient(145deg, #062c22, #021a14); color: #34d399; box-shadow: 0 8px 20px rgba(0,0,0,0.4); }
  .garden-prediction.light { border-color: #78350f; background: linear-gradient(145deg, #2c1c06, #140d02); color: #fbbf24; }
  .garden-prediction > span { display: block; margin-top: 17px; font-size: 12px; }
  .garden-prediction strong { display: block; font-size: 35px; margin: 13px 0; text-shadow: 0 2px 6px rgba(0,0,0,0.5); }
  .garden-prediction small { font-size: 14px; font-weight: 500; }
  .garden-prediction p { font-size: 10px; opacity: .85; }
  .garden-ai-explanation { display: flex; gap: 10px; padding: 15px; border-radius: 12px; background: #0b1120; color: #94a3b8; font-size: 11px; margin-top: 20px; line-height: 1.8; border: 1px solid #1e293b; }

  .garden-event { display: flex; align-items: flex-start; gap: 13px; padding: 17px 0; border-bottom: 1px solid #1e293b; }
  .garden-event:last-child { border-bottom: 0; }
  .garden-event-dot { width: 8px; height: 8px; border-radius: 50%; background: #38bdf8; margin-top: 6px; flex-shrink: 0; }
  .garden-event-dot.success { background: #34d399; }
  .garden-event-dot.error { background: #f87171; }
  .garden-event > div { flex: 1; min-width: 0; }
  .garden-event small { font-size: 9px; color: #64748b; font-weight: 750; letter-spacing: .7px; }
  .garden-event p { font-size: 12px; color: #e2e8f0; margin-top: 4px; overflow-wrap: anywhere; }
  .garden-event time { color: #64748b; font-size: 10px; white-space: nowrap; padding-top: 3px; }

  .garden-settings { display: flex; align-items: center; gap: 22px; padding: 22px; margin-top: 18px; }
  .garden-settings > div { flex: 1; min-width: 0; }
  .garden-settings h2 { font-size: 18px; color: #f8fafc; }
  .garden-settings p { font-size: 11px; color: #94a3b8; margin-top: 5px; }
  .garden-api-address { overflow-wrap: anywhere; }
  .garden-soft-button { padding: 10px 18px; background: #1e293b; border: 1px solid #334155; border-radius: 11px; color: #e2e8f0; font-weight: 650; box-shadow: 0 3px 0 #090d16; }
  
  .garden-alert { display: flex; align-items: center; gap: 12px; padding: 16px 19px; margin-bottom: 18px; border-radius: 15px; background: #450a0a; border: 1px solid #7f1d1d; color: #fca5a5; font-size: 12px; }
  .garden-error { color: #f87171; font-size: 12px; margin-top: 12px !important; }
  .garden-alert.garden-water-warning { background: #2b2108; border-color: #a16207; color: #facc15; }
  
  .garden-footer { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; margin-top: 28px; padding: 18px 0 3px; color: #64748b; font-size: 10px; border-top: 1px solid #1e293b; }
  .garden-footer > span:first-child { display: flex; align-items: center; gap: 7px; letter-spacing: .8px; font-weight: 700; color: #94a3b8; }

  @keyframes garden-pulse {
    0%, 100% { box-shadow: inset 0 2px 5px rgba(0,0,0,0.5), 0 0 0 0 rgba(52,211,153,0.4); }
    50% { box-shadow: inset 0 2px 5px rgba(0,0,0,0.5), 0 0 0 10px rgba(52,211,153,0); }
  }

  @media (max-width: 1180px) {
    .garden-app { padding: 22px; }
    .garden-workspace { grid-template-columns: minmax(0, 1fr) 310px; gap: 18px; }
    .garden-hero { padding: 27px; }
    .garden-hero-stats { min-width: 270px; gap: 10px; }
    .garden-hero-stats > div { padding: 15px; }
    .garden-sensors { gap: 12px; }
    .garden-sensor { padding: 16px; }
    .garden-sensor-icon { width: 31px; height: 31px; }
    .garden-controls { padding: 21px; }
    .garden-tabs button { padding: 9px 10px; font-size: 11px; }
  }

  @media (max-width: 940px) {
    .garden-hero { align-items: stretch; flex-direction: column; }
    .garden-hero-stats { min-width: 0; }
    .garden-hero-stats > div { padding: 17px 22px; }
    .garden-sensors { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    .garden-workspace { grid-template-columns: 1fr; }
    .garden-controls { position: static; }
    .garden-mode-button { min-height: 108px; }
    .garden-sensor-value { font-size: 32px; }
    .garden-settings { flex-wrap: wrap; }
  }

  @media (max-width: 580px) {
    .garden-app { padding: 14px 12px; }
    .garden-header { padding: 15px; gap: 14px; flex-wrap: wrap; border-radius: 20px; }
    .garden-brand { gap: 11px; }
    .garden-logo { width: 42px; height: 42px; border-radius: 13px; }
    .garden-logo svg { width: 25px; height: 25px; }
    .garden-brand h1 { font-size: 22px; }
    .garden-overline { font-size: 8px; letter-spacing: 1.2px; }
    .garden-header-actions { width: 100%; justify-content: flex-end; gap: 10px; border-top: 1px solid #1e293b; padding-top: 12px; }
    .garden-device { margin-right: auto; padding-right: 10px; font-size: 11px; }
    .garden-icon-button { width: 35px; height: 35px; }
    .garden-hero { padding: 24px 19px; margin: 17px 0; border-radius: 22px; gap: 20px; }
    .garden-hero h2 { font-size: 28px; }
    .garden-hero-copy > p { font-size: 12px; }
    .garden-hero-stats strong { font-size: 25px; }
    .garden-hero-stats > div { padding: 15px; border-radius: 15px; }
    .garden-sensors { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 11px; margin-bottom: 20px; }
    .garden-sensor { padding: 16px; border-radius: 18px; }
    .garden-sensor:last-child { grid-column: 1 / -1; }
    .garden-sensor-value { font-size: 30px; margin: 12px 0; }
    .garden-sensor:last-child .garden-sensor-value { margin: 5px 0 12px; }
    .garden-sensor-head > span { font-size: 11px; }
    .garden-tabs { gap: 5px; }
    .garden-tabs button { padding: 9px 8px; gap: 5px; font-size: 10px; }
    .garden-tabs svg { width: 15px; height: 15px; }
    .garden-ai-status { padding: 13px; gap: 9px; }
    .garden-ai-status strong { font-size: 11px; }
    .garden-ai-status p { font-size: 10px; }
    .garden-chart-panel, .garden-content-panel { padding: 19px 15px; border-radius: 20px; }
    .garden-section-head h2 { font-size: 20px; }
    .garden-chart { height: 300px; }
    .garden-chart-footer { flex-wrap: wrap; }
    .garden-metric-switch { gap: 5px; }
    .garden-metric-switch button { padding: 6px 8px; font-size: 10px; }
    .garden-predictions { gap: 10px; }
    .garden-prediction { padding: 16px 12px; }
    .garden-prediction strong { font-size: 27px; }
    .garden-prediction > span { font-size: 11px; }
    .garden-detail { font-size: 10px; }
    .garden-event { gap: 9px; }
    .garden-event p { font-size: 11px; }
    .garden-event time { font-size: 9px; }
    .garden-settings { padding: 18px; }
    .garden-settings > div { width: 100%; flex-basis: 100%; }
    .garden-footer { align-items: flex-start; flex-direction: column; font-size: 9px; }
  }

  @media (max-width: 360px) {
    .garden-predictions { grid-template-columns: 1fr; }
    .garden-sensor-value { font-size: 25px; }
  }

  @media (prefers-reduced-motion: reduce) {
    .garden-app *, .garden-app *::before, .garden-app *::after {
      animation: none !important;
      transition: none !important;
    }
  }
`;