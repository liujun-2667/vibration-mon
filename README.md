# 设备振动频谱在线监测与预警系统

基于 FastAPI + Svelte + Tauri 的工业设备振动监测与分析系统，支持实时数据采集、频谱分析、趋势监测、报警管理和报告生成。

## 目录

- [项目简介](#项目简介)
- [项目架构](#项目架构)
- [功能列表](#功能列表)
- [技术栈](#技术栈)
- [快速启动](#快速启动)
  - [方式一：一键启动脚本（推荐）](#方式一一键启动脚本推荐)
  - [方式二：Docker 启动后端](#方式二docker-启动后端)
  - [方式三：手动启动](#方式三手动启动)
- [Tauri 桌面应用](#tauri-桌面应用)
- [API 文档](#api-文档)
- [项目结构](#项目结构)
- [环境变量](#环境变量)

## 项目简介

本系统是一套完整的工业设备振动监测解决方案，提供从数据采集、信号分析到报警预警的全流程功能。系统支持时域/频域分析、特征频率计算、趋势监测、数据回放等多种分析工具，帮助运维人员及时发现设备潜在故障。

## 项目架构

```
┌─────────────────────────────────────────────────────────────┐
│                     Tauri 桌面应用层                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ 监控概览     │  │ 数据分析     │  │ 报警中心     │     │
│  │ Dashboard    │  │ Analysis     │  │ Alarms       │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ 趋势监测     │  │ 信号模拟     │  │ 报告生成     │     │
│  │ Trend        │  │ Simulator    │  │ Reports      │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP / WebSocket
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI 后端服务层                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ 设备管理 │ │ 采样管理 │ │ 报警管理 │ │ 数据分析 │      │
│  │ Devices  │ │ Sampling │ │ Alarms   │ │ Analysis │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│  ┌──────────┐ ┌──────────┐                                  │
│  │ 数据管理 │ │ 报告生成 │                                  │
│  │ Data     │ │ Reports  │                                  │
│  └──────────┘ └──────────┘                                  │
└─────────────────────────────────────────────────────────────┘
```

## 功能列表

### 监控概览 (Dashboard)
- 设备状态总览（在线/警告/离线）
- 实时报警统计
- 关键指标卡片展示
- 设备快速跳转

### 设备管理 (Device Manager)
- 设备信息增删改查
- 设备状态监控
- 设备参数配置

### 数据分析 (Device Analysis)
- 时域波形图展示
- 频域频谱分析 (FFT)
- 实时数据刷新
- 多维度数据对比

### 趋势监测 (Trend Monitor)
- 历史数据趋势曲线
- 多时间维度切换
- 趋势异常识别

### 特征频率 (Feature Calculator)
- 轴承故障特征频率计算
- 齿轮啮合频率计算
- 转频/倍频分析

### 信号模拟 (Signal Simulator)
- 振动信号仿真生成
- 多种故障类型模拟
- 参数化信号配置

### 数据回放 (Data Replay)
- 历史数据回放
- 播放速度控制
- 时间轴精确定位

### 报警中心 (Alarm Center)
- 实时报警列表
- 报警确认与处理
- 报警历史查询

### 报警规则 (Alarm Config)
- 报警阈值配置
- 报警规则管理
- 多级报警设置

### 报告生成 (Report Generator)
- PDF 报告导出
- 自定义报告模板
- 数据可视化图表

## 技术栈

### 后端
- **框架**: FastAPI
- **服务器**: Uvicorn
- **数据处理**: NumPy, SciPy
- **信号分析**: PyHHT (希尔伯特黄变换)
- **报告生成**: ReportLab
- **数据验证**: Pydantic

### 前端
- **框架**: Svelte
- **构建工具**: Vite
- **图表库**: Chart.js + chartjs-plugin-annotation
- **日期处理**: date-fns
- **PDF导出**: jsPDF + html2canvas

### 桌面应用
- **框架**: Tauri
- **语言**: Rust
- **平台**: Windows / macOS / Linux

## 快速启动

### 前置要求

- Python 3.8+
- Node.js 16+
- npm 或 yarn

### 方式一：一键启动脚本（推荐）

#### Windows

```bash
start.bat
```

脚本会自动：
1. 创建 Python 虚拟环境并安装依赖
2. 启动后端服务（端口 8000）
3. 等待后端就绪
4. 安装前端依赖
5. 启动前端开发服务器（端口 1420）

#### Linux / macOS

```bash
chmod +x start.sh
./start.sh
```

### 方式二：Docker 启动后端

仅启动后端服务：

```bash
docker-compose up -d
```

后端服务将在 `http://localhost:8000` 启动。

前端仍需手动启动：

```bash
npm install
npm run dev
```

### 方式三：手动启动

#### 1. 启动后端服务

```bash
cd python

# 创建虚拟环境（可选）
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate    # Windows

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn main:app --reload --port 8000
```

后端服务地址: `http://localhost:8000`

#### 2. 启动前端开发服务器

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端地址: `http://localhost:1420`

## Tauri 桌面应用

### 前置要求

- Rust 工具链 ([安装指南](https://www.rust-lang.org/tools/install))
- 平台特定依赖（参见 [Tauri 文档](https://tauri.app/v1/guides/getting-started/prerequisites)）

### 开发模式

```bash
# 安装 Tauri CLI（如未安装）
npm install

# 启动 Tauri 开发模式
npm run tauri dev
```

这将同时启动前端开发服务器和 Tauri 桌面窗口。

### 构建生产版本

```bash
npm run tauri build
```

构建完成后，安装包将位于 `src-tauri/target/release/bundle/` 目录下。

### 注意事项

1. **后端服务**: Tauri 桌面应用需要后端服务运行。在使用桌面应用前，请确保后端服务已启动。
2. **Sidecar 模式**: 生产环境中，后端服务可以作为 Tauri 的 sidecar 进程打包（需自行配置）。

## API 文档

后端服务启动后，可以通过以下地址访问 API 文档：

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### 主要 API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/` | GET | 系统信息 |
| `/health` | GET | 健康检查 |
| `/ws/{device_id}` | WebSocket | 实时数据传输 |
| `/api/v1/devices` | GET/POST | 设备管理 |
| `/api/v1/sampling` | GET/POST | 采样参数 |
| `/api/v1/alarms` | GET/POST | 报警管理 |
| `/api/v1/analysis` | POST | 数据分析 |
| `/api/v1/data` | GET/POST | 数据管理 |
| `/api/v1/reports` | POST | 报告生成 |

## 项目结构

```
vibration-mon/
├── python/                      # 后端代码
│   ├── main.py                  # FastAPI 入口文件
│   ├── requirements.txt         # Python 依赖
│   ├── models.py                # 数据模型
│   ├── database.py              # 数据库操作
│   ├── device_manager.py        # 设备管理
│   ├── alarm_rules.py           # 报警规则
│   ├── signal_simulator.py      # 信号模拟器
│   ├── time_domain.py           # 时域分析
│   ├── frequency_domain.py      # 频域分析
│   ├── feature_frequency.py     # 特征频率计算
│   ├── trend_analysis.py        # 趋势分析
│   ├── report_generator.py      # 报告生成器
│   └── routers/                 # API 路由
│       ├── devices.py
│       ├── sampling.py
│       ├── alarms.py
│       ├── analysis.py
│       ├── data.py
│       └── reports.py
├── src/                         # 前端代码
│   ├── main.js                  # 入口文件
│   ├── App.svelte               # 根组件
│   ├── api.js                   # API 封装
│   ├── store.js                 # 状态管理
│   ├── global.css               # 全局样式
│   ├── components/              # 通用组件
│   │   ├── Sidebar.svelte
│   │   ├── TimeDomainChart.svelte
│   │   ├── FrequencyChart.svelte
│   │   ├── TrendChart.svelte
│   │   └── StatusIndicator.svelte
│   └── pages/                   # 页面组件
│       ├── Dashboard.svelte
│       ├── DeviceManager.svelte
│       ├── DeviceAnalysis.svelte
│       ├── TrendMonitor.svelte
│       ├── FeatureCalculator.svelte
│       ├── SignalSimulator.svelte
│       ├── DataReplay.svelte
│       ├── AlarmConfig.svelte
│       └── ReportGenerator.svelte
├── src-tauri/                   # Tauri 桌面应用
│   ├── src/
│   │   └── main.rs              # Rust 入口
│   ├── Cargo.toml               # Rust 依赖
│   ├── tauri.conf.json          # Tauri 配置
│   └── build.rs                 # 构建脚本
├── docker-compose.yml           # Docker Compose 配置
├── .env.example                 # 环境变量示例
├── start.bat                    # Windows 一键启动脚本
├── start.sh                     # Linux/macOS 一键启动脚本
├── package.json                 # 前端依赖
├── vite.config.js               # Vite 配置
├── svelte.config.js             # Svelte 配置
└── index.html                   # HTML 入口
```

## 环境变量

复制 `.env.example` 为 `.env` 并根据需要修改：

```bash
cp .env.example .env
```

| 变量名 | 默认值 | 描述 |
|--------|--------|------|
| `BACKEND_HOST` | `0.0.0.0` | 后端监听地址 |
| `BACKEND_PORT` | `8000` | 后端端口 |
| `FRONTEND_PORT` | `1420` | 前端端口 |
| `ENV` | `development` | 运行环境 |
| `LOG_LEVEL` | `INFO` | 日志级别 |

## License

MIT
