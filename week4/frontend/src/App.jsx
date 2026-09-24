import React, { useState, useEffect } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { Line } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export default function App() {
  const [temperature, setTemperature] = useState('32.5');
  const [humidity, setHumidity] = useState('65.0');
  const [soilMoisture, setSoilMoisture] = useState('45.0');
  const [light, setLight] = useState('12000');
  const [vpd, setVpd] = useState('1.20');
  const [isConnected, setIsConnected] = useState(false);
  const [mode, setMode] = useState('AUTO');
  const [isPumping, setIsPumping] = useState(false);

  const [chartData, setChartData] = useState({
    labels: [],
    datasets: [
      {
        label: 'Nhiệt độ (°C)',
        data: [],
        borderColor: 'rgb(244, 63, 94)',
        backgroundColor: 'rgba(244, 63, 94, 0.1)',
        tension: 0.4,
        fill: true,
      },
      {
        label: 'Độ ẩm (%)',
        data: [],
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        tension: 0.4,
        fill: true,
      },
    ],
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        // ĐÃ CẬP NHẬT LINK CLOUD RENDER
        const response = await fetch('https://es-design.onrender.com/api/telemetry/latest');
        const result = await response.json();
        
        if (result.status === 'success' && result.data) {
          setIsConnected(true);
          const data = result.data;
          const currentTime = new Date().toLocaleTimeString();

          if (data.temperature !== undefined) setTemperature(Number(data.temperature).toFixed(1));
          if (data.humidity !== undefined) setHumidity(Number(data.humidity).toFixed(1));
          if (data.soilMoisture !== undefined) setSoilMoisture(Number(data.soilMoisture).toFixed(1));
          if (data.light !== undefined) setLight(Number(data.light).toFixed(0));
          if (data.vpd !== undefined) setVpd(Number(data.vpd).toFixed(2));

          setChartData(prev => {
            const newLabels = [...prev.labels, currentTime].slice(-10);
            const newTempData = [...prev.datasets[0].data, data.temperature || 30].slice(-10);
            const newHumData = [...prev.datasets[1].data, data.humidity || 60].slice(-10);

            return {
              labels: newLabels,
              datasets: [
                { ...prev.datasets[0], data: newTempData },
                { ...prev.datasets[1], data: newHumData },
              ],
            };
          });
        } else {
          setIsConnected(false);
        }
      } catch (err) {
        setIsConnected(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 2000); 
    return () => clearInterval(interval);
  }, []);

  const handleWaterNow = async () => {
    setIsPumping(true);
    try {
      // ĐÃ CẬP NHẬT LINK CLOUD RENDER
      await fetch('https://es-design.onrender.com/api/control/pump', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ state: 'ON' })
      });
      setTimeout(async () => {
        await fetch('https://es-design.onrender.com/api/control/pump', {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ state: 'OFF' })
        });
        setIsPumping(false);
      }, 2500);
    } catch (e) {
      setIsPumping(false);
    }
  };

  const toggleMode = () => {
    setMode(prev => prev === 'AUTO' ? 'MANUAL' : 'AUTO');
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'top' },
    },
    scales: {
      y: { beginAtZero: false }
    }
  };

  return (
    <div className="min-h-screen bg-slate-100 text-slate-800 p-4 md:p-6 flex flex-col items-center">
      <div className="w-full max-w-7xl bg-white shadow-sm rounded-2xl p-4 mb-6 flex justify-between items-center border border-slate-200">
        <h1 className="text-2xl md:text-3xl font-extrabold text-emerald-700 flex items-center gap-2">
          🌱 Bảng điều khiển cây trồng thông minh AloT
        </h1>
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-slate-500">Trạng thái:</span>
          <span className={`px-3 py-1 rounded-full text-xs font-bold ${
            isConnected ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-600'
          }`}>
            {isConnected ? 'ĐÃ KẾT NỐI API' : 'MẤT KẾT NỐI'}
          </span>
        </div>
      </div>

      <div className="w-full max-w-7xl grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-200 text-center">
          <p className="text-xs font-bold text-slate-400 uppercase mb-1">ĐỘ ẨM ĐẤT</p>
          <p className="text-3xl font-black text-blue-600">{soilMoisture} %</p>
        </div>
        <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-200 text-center">
          <p className="text-xs font-bold text-slate-400 uppercase mb-1">ÁNH SÁNG</p>
          <p className="text-3xl font-black text-amber-500">{light} <span className="text-sm font-medium text-slate-500">Lux</span></p>
          <span className="text-xs font-bold text-amber-600 bg-amber-50 px-2 py-0.5 rounded">CAO</span>
        </div>
        <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-200 text-center">
          <p className="text-xs font-bold text-slate-400 uppercase mb-1">NHIỆT ĐỘ</p>
          <p className="text-3xl font-black text-rose-500">{temperature} °C</p>
        </div>
        <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-200 text-center">
          <p className="text-xs font-bold text-slate-400 uppercase mb-1">ĐỘ ẨM KHÍ</p>
          <p className="text-3xl font-black text-cyan-600">{humidity} %</p>
        </div>
        <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-200 text-center col-span-2 md:col-span-1">
          <p className="text-xs font-bold text-slate-400 uppercase mb-1">CHỈ SỐ VPD</p>
          <p className="text-3xl font-black text-purple-600">{vpd} <span className="text-sm font-medium text-slate-500">kPa</span></p>
        </div>
      </div>

      <div className="w-full max-w-7xl grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex flex-col">
          <h2 className="font-bold text-slate-700 mb-4 flex items-center gap-2">
            📈 Biểu đồ xu hướng AI (Thời gian thực)
          </h2>
          <div className="flex-1 relative min-h-[300px]">
            <Line data={chartData} options={chartOptions} />
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex flex-col justify-between">
          <div>
            <h2 className="font-bold text-slate-700 mb-4 flex items-center gap-2">
              🎛️ BẢNG ĐIỀU KHIỂN
            </h2>
            
            <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 mb-4 flex justify-between items-center text-sm">
              <span className="text-slate-500 font-medium">Độ trễ dữ liệu:</span>
              <span className="bg-emerald-100 text-emerald-700 font-bold px-2.5 py-1 rounded-lg text-xs">
                1.2 giây (Tốt)
              </span>
            </div>

            <button
              onClick={toggleMode}
              className="w-full py-3 mb-4 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 font-bold text-slate-700 transition-all flex items-center justify-center gap-2 shadow-sm"
            >
              ⚙️ CHẾ ĐỘ: {mode} ({mode === 'AUTO' ? 'AUTO' : 'MANUAL'})
            </button>
          </div>

          <button
            onClick={handleWaterNow}
            disabled={isPumping}
            className={`w-full py-4 rounded-xl font-bold text-white text-lg transition-all shadow-md flex items-center justify-center gap-2 ${
              isPumping 
                ? 'bg-amber-500 animate-pulse' 
                : 'bg-blue-600 hover:bg-blue-500 shadow-blue-200'
            }`}
          >
            💧 {isPumping ? 'ĐANG TƯỚI (2.5s)...' : 'TƯỚI NGAY (2.5s)'}
          </button>
        </div>
      </div>
    </div>
  );
}