/**
 * @file server.js
 * @author Le Cong Quoc Anh
 * @brief Backend Server ket noi MQTT Broker, cung cap RESTful API va Socket.IO thoi gian thuc
 */

const express = require('express');
const http = require('http');
const cors = require('cors');
const mqtt = require('mqtt');
const { Server } = require('socket.io');

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
    cors: { origin: '*' }
});

app.use(cors());
app.use(express.json());

const PORT = process.env.PORT || 5000;
const MQTT_URL = process.env.MQTT_URL || 'mqtt://localhost:1883';

// Bo nho luu tru lich su nhanh (co the thay bang MongoDB/PostgreSQL)
const telemetryHistory = [];
const alertLogs = [];
let latestTelemetry = {
    device_id: 'ESP32_NODE_01',
    temperature: 28.5,
    humidity: 64.0,
    air_quality: 95,
    relay_state: false,
    timestamp: Math.floor(Date.now() / 1000)
};

// Ket noi MQTT Broker
const mqttClient = mqtt.connect(MQTT_URL);

mqttClient.on('connect', () => {
    console.log('[Backend] Connected to MQTT Broker:', MQTT_URL);
    mqttClient.subscribe(['iot/device/telemetry', 'iot/ai/alert']);
});

mqttClient.on('message', (topic, message) => {
    try {
        const data = JSON.parse(message.toString());
        if (topic === 'iot/device/telemetry') {
            latestTelemetry = data;
            telemetryHistory.push(data);
            if (telemetryHistory.length > 100) telemetryHistory.shift();
            io.emit('telemetry_update', data);
        } else if (topic === 'iot/ai/alert') {
            alertLogs.unshift(data);
            if (alertLogs.length > 50) alertLogs.pop();
            io.emit('ai_alert', data);
        }
    } catch (err) {
        console.error('[Backend] Invalid MQTT JSON payload:', err.message);
    }
});

// RESTful API Routes
app.get('/api/health', (req, res) => {
    res.json({ status: 'OK', author: 'Le Cong Quoc Anh', uptime: process.uptime() });
});

app.get('/api/telemetry/latest', (req, res) => {
    res.json(latestTelemetry);
});

app.get('/api/telemetry/history', (req, res) => {
    const limit = parseInt(req.query.limit || '30', 10);
    res.json(telemetryHistory.slice(-limit));
});

app.get('/api/alerts', (req, res) => {
    res.json(alertLogs);
});

app.post('/api/control', (req, res) => {
    const { device_id = 'ESP32_NODE_01', command = 'SET_RELAY', value = false } = req.body;
    const payload = JSON.stringify({ device_id, command, value: Boolean(value) });
    mqttClient.publish('iot/device/control', payload);
    latestTelemetry.relay_state = Boolean(value);
    io.emit('telemetry_update', latestTelemetry);
    res.json({ success: true, sent: JSON.parse(payload) });
});

// Socket.IO connection
io.on('connection', (socket) => {
    console.log('[WebSocket] Client connected:', socket.id);
    socket.emit('telemetry_update', latestTelemetry);
});

server.listen(PORT, () => {
    console.log(`[Backend] Server running on http://localhost:${PORT}`);
});
