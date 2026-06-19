import os
import sqlite3
import json
import logging
import asyncio
from typing import Optional, List, Dict, Any, Tuple, AsyncGenerator
from datetime import datetime, timedelta
from pathlib import Path

from models import (
    VibrationData,
    VibrationDataCreate,
    AnalysisResult,
    TimeDomainFeatures,
    FrequencyDomainFeatures,
    HHTFeatures,
    DeviceStatus,
    DiagnosisTask,
    DiagnosisStatus,
    FeatureSnapshot,
    FaultModeKnowledge,
    FaultMatchResult,
    SeverityLevel,
)

logger = logging.getLogger(__name__)


def adapt_datetime(dt: datetime) -> str:
    return dt.isoformat()


def convert_datetime(s: bytes) -> datetime:
    return datetime.fromisoformat(s.decode())


def adapt_list(lst: List[Any]) -> str:
    return json.dumps(lst)


def convert_list(s: bytes) -> List[Any]:
    return json.loads(s.decode())


def adapt_dict(dct: Dict[Any, Any]) -> str:
    return json.dumps(dct)


def convert_dict(s: bytes) -> Dict[Any, Any]:
    return json.loads(s.decode())


sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("DATETIME", convert_datetime)
sqlite3.register_adapter(list, adapt_list)
sqlite3.register_converter("LIST", convert_list)
sqlite3.register_adapter(dict, adapt_dict)
sqlite3.register_converter("DICT", convert_dict)


class Database:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            data_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "data"
            )
            Path(data_dir).mkdir(parents=True, exist_ok=True)
            db_path = os.path.join(data_dir, "vibration.db")

        self.db_path = db_path
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS vibration_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER NOT NULL,
                    channel INTEGER DEFAULT 0,
                    timestamp DATETIME NOT NULL,
                    sample_rate INTEGER NOT NULL,
                    data LIST NOT NULL,
                    is_fault_sample INTEGER DEFAULT 0,
                    fault_type TEXT,
                    remark TEXT,
                    marked_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER NOT NULL,
                    data_id INTEGER,
                    channel INTEGER DEFAULT 0,
                    timestamp DATETIME NOT NULL,
                    time_domain DICT NOT NULL,
                    frequency_domain DICT NOT NULL,
                    hht_features DICT,
                    health_index REAL NOT NULL,
                    status TEXT NOT NULL,
                    anomalies LIST,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (data_id) REFERENCES vibration_data(id) ON DELETE CASCADE
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS replay_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER NOT NULL,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME NOT NULL,
                    speed_multiplier REAL DEFAULT 1.0,
                    is_paused INTEGER DEFAULT 0,
                    current_position DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_vibration_device_time ON vibration_data(device_id, timestamp)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_vibration_fault_sample ON vibration_data(is_fault_sample)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_analysis_device_time ON analysis_results(device_id, timestamp)"
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS fault_mode_knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT NOT NULL,
                    key_frequency_features TEXT NOT NULL,
                    severity_level TEXT NOT NULL DEFAULT 'medium',
                    maintenance_action TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS diagnosis_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER NOT NULL,
                    device_name TEXT,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    feature_snapshot DICT,
                    match_results LIST,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    completed_at DATETIME
                )
                """
            )

            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_diagnosis_device_time ON diagnosis_tasks(device_id, created_at)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_diagnosis_status ON diagnosis_tasks(status)"
            )

            self._init_default_knowledge(cursor)

            conn.commit()
            logger.info(f"数据库初始化完成: {self.db_path}")

    def _init_default_knowledge(self, cursor) -> None:
        cursor.execute("SELECT COUNT(*) as count FROM fault_mode_knowledge")
        count = cursor.fetchone()["count"]
        if count > 0:
            return

        default_knowledge = [
            {
                "name": "转子不平衡",
                "description": "1X频率幅值异常升高且相位稳定，径向振动大",
                "key_frequency_features": "1X转频幅值显著升高，相位稳定",
                "severity_level": "high",
                "maintenance_action": "动平衡校正",
            },
            {
                "name": "轴不对中",
                "description": "2X频率显著且轴向振动大，联轴器两侧振动相位差180度",
                "key_frequency_features": "2X转频占主导，轴向振动大",
                "severity_level": "high",
                "maintenance_action": "对中调整",
            },
            {
                "name": "机械松动",
                "description": "出现大量次谐波和高次谐波，振动具有随机性",
                "key_frequency_features": "0.5X、1.5X等次谐波及高次谐波",
                "severity_level": "medium",
                "maintenance_action": "紧固检查",
            },
            {
                "name": "滚动轴承外圈缺陷",
                "description": "BPFO频率及其倍频出现，伴有边带调制",
                "key_frequency_features": "BPFO(外圈故障频率)及其2倍、3倍频",
                "severity_level": "high",
                "maintenance_action": "更换轴承",
            },
            {
                "name": "齿轮磨损",
                "description": "啮合频率边带增宽，调制现象明显",
                "key_frequency_features": "啮合频率FM及其边带",
                "severity_level": "medium",
                "maintenance_action": "检查润滑或更换齿轮",
            },
            {
                "name": "共振",
                "description": "某频率振幅随转速接近时急剧放大，通过临界转速时振动最大",
                "key_frequency_features": "共振频率处幅值急剧变化",
                "severity_level": "critical",
                "maintenance_action": "避开共振区或修改结构",
            },
        ]

        for item in default_knowledge:
            cursor.execute(
                """
                INSERT INTO fault_mode_knowledge (
                    name, description, key_frequency_features, severity_level, maintenance_action
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    item["name"],
                    item["description"],
                    item["key_frequency_features"],
                    item["severity_level"],
                    item["maintenance_action"],
                ),
            )

        logger.info("初始化默认故障模式知识库完成")

    def insert_vibration_data(
        self, data_create: VibrationDataCreate
    ) -> VibrationData:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO vibration_data (
                    device_id, channel, timestamp, sample_rate, data
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    data_create.device_id,
                    data_create.channel,
                    data_create.timestamp,
                    data_create.sample_rate,
                    data_create.data,
                ),
            )
            data_id = cursor.lastrowid
            conn.commit()

            cursor.execute(
                "SELECT * FROM vibration_data WHERE id = ?", (data_id,)
            )
            row = cursor.fetchone()
            logger.info(
                f"插入振动数据: 设备ID={data_create.device_id}, 数据ID={data_id}"
            )
            return self._row_to_vibration_data(row)

    def get_vibration_data(
        self,
        page: int = 1,
        page_size: int = 10,
        device_id: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        is_fault_sample: Optional[bool] = None,
    ) -> Tuple[List[VibrationData], int]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM vibration_data WHERE 1=1"
            params: List[Any] = []

            if device_id is not None:
                query += " AND device_id = ?"
                params.append(device_id)

            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time)

            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time)

            if is_fault_sample is not None:
                query += " AND is_fault_sample = ?"
                params.append(1 if is_fault_sample else 0)

            count_query = query.replace("SELECT *", "SELECT COUNT(*)")
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]

            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([page_size, (page - 1) * page_size])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return (
                [self._row_to_vibration_data(row) for row in rows],
                total,
            )

    def get_vibration_data_by_id(self, data_id: int) -> Optional[VibrationData]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM vibration_data WHERE id = ?", (data_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_vibration_data(row)
            return None

    def _row_to_vibration_data(self, row: sqlite3.Row) -> VibrationData:
        return VibrationData(
            id=row["id"],
            device_id=row["device_id"],
            channel=row["channel"],
            timestamp=row["timestamp"],
            sample_rate=row["sample_rate"],
            data=row["data"],
            created_at=row["created_at"],
        )

    def insert_analysis_result(self, result: AnalysisResult) -> AnalysisResult:
        with self._get_connection() as conn:
            cursor = conn.cursor()

            hht_dict = None
            if result.hht_features:
                hht_dict = result.hht_features.model_dump(mode="json")

            cursor.execute(
                """
                INSERT INTO analysis_results (
                    device_id, data_id, channel, timestamp,
                    time_domain, frequency_domain, hht_features,
                    health_index, status, anomalies
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.device_id,
                    result.data_id,
                    result.channel,
                    result.timestamp,
                    result.time_domain.model_dump(mode="json"),
                    result.frequency_domain.model_dump(mode="json"),
                    hht_dict,
                    result.health_index,
                    result.status,
                    result.anomalies,
                ),
            )
            result_id = cursor.lastrowid
            conn.commit()

            cursor.execute(
                "SELECT * FROM analysis_results WHERE id = ?", (result_id,)
            )
            row = cursor.fetchone()
            logger.info(
                f"插入分析结果: 设备ID={result.device_id}, 结果ID={result_id}"
            )
            return self._row_to_analysis_result(row)

    def get_analysis_results(
        self,
        page: int = 1,
        page_size: int = 10,
        device_id: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        status: Optional[str] = None,
    ) -> Tuple[List[AnalysisResult], int]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM analysis_results WHERE 1=1"
            params: List[Any] = []

            if device_id is not None:
                query += " AND device_id = ?"
                params.append(device_id)

            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time)

            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time)

            if status:
                query += " AND status = ?"
                params.append(status)

            count_query = query.replace("SELECT *", "SELECT COUNT(*)")
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]

            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([page_size, (page - 1) * page_size])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return (
                [self._row_to_analysis_result(row) for row in rows],
                total,
            )

    def get_analysis_result_by_id(
        self, result_id: int
    ) -> Optional[AnalysisResult]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM analysis_results WHERE id = ?", (result_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_analysis_result(row)
            return None

    def _row_to_analysis_result(self, row: sqlite3.Row) -> AnalysisResult:
        hht_features = None
        if row["hht_features"]:
            hht_features = HHTFeatures.model_validate(row["hht_features"])

        return AnalysisResult(
            id=row["id"],
            device_id=row["device_id"],
            data_id=row["data_id"],
            channel=row["channel"],
            timestamp=row["timestamp"],
            time_domain=TimeDomainFeatures.model_validate(row["time_domain"]),
            frequency_domain=FrequencyDomainFeatures.model_validate(
                row["frequency_domain"]
            ),
            hht_features=hht_features,
            health_index=row["health_index"],
            status=row["status"],
            anomalies=row["anomalies"],
            created_at=row["created_at"],
        )

    def mark_fault_sample(
        self,
        data_id: int,
        fault_type: str,
        remark: Optional[str] = None,
    ) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE vibration_data
                SET is_fault_sample = 1,
                    fault_type = ?,
                    remark = ?,
                    marked_at = ?
                WHERE id = ?
                """,
                (fault_type, remark, datetime.now(), data_id),
            )
            conn.commit()

            if cursor.rowcount == 0:
                raise ValueError(f"振动数据 {data_id} 不存在")

            logger.info(
                f"标记故障样本: 数据ID={data_id}, 故障类型={fault_type}"
            )

    def unmark_fault_sample(self, data_id: int) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE vibration_data
                SET is_fault_sample = 0,
                    fault_type = NULL,
                    remark = NULL,
                    marked_at = NULL
                WHERE id = ?
                """,
                (data_id,),
            )
            conn.commit()

            if cursor.rowcount == 0:
                raise ValueError(f"振动数据 {data_id} 不存在")

            logger.info(f"取消故障样本标记: 数据ID={data_id}")

    def update_fault_remark(
        self, data_id: int, remark: str
    ) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE vibration_data
                SET remark = ?
                WHERE id = ? AND is_fault_sample = 1
                """,
                (remark, data_id),
            )
            conn.commit()

            if cursor.rowcount == 0:
                raise ValueError(
                    f"振动数据 {data_id} 不存在或未标记为故障样本"
                )

            logger.info(f"更新故障备注: 数据ID={data_id}")

    def get_fault_samples(
        self,
        page: int = 1,
        page_size: int = 10,
        device_id: Optional[int] = None,
        fault_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT id, device_id, channel, timestamp, sample_rate,
                       fault_type, remark, marked_at, created_at
                FROM vibration_data
                WHERE is_fault_sample = 1
            """
            params: List[Any] = []

            if device_id is not None:
                query += " AND device_id = ?"
                params.append(device_id)

            if fault_type:
                query += " AND fault_type = ?"
                params.append(fault_type)

            if start_time:
                query += " AND marked_at >= ?"
                params.append(start_time)

            if end_time:
                query += " AND marked_at <= ?"
                params.append(end_time)

            count_query = query.replace(
                "SELECT id, device_id", "SELECT COUNT(*)"
            )
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]

            query += " ORDER BY marked_at DESC LIMIT ? OFFSET ?"
            params.extend([page_size, (page - 1) * page_size])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            samples = []
            for row in rows:
                samples.append(
                    {
                        "id": row["id"],
                        "device_id": row["device_id"],
                        "channel": row["channel"],
                        "timestamp": row["timestamp"],
                        "sample_rate": row["sample_rate"],
                        "fault_type": row["fault_type"],
                        "remark": row["remark"],
                        "marked_at": row["marked_at"],
                        "created_at": row["created_at"],
                    }
                )

            return samples, total

    def get_fault_types(self) -> List[str]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT DISTINCT fault_type
                FROM vibration_data
                WHERE is_fault_sample = 1 AND fault_type IS NOT NULL
                ORDER BY fault_type
                """
            )
            rows = cursor.fetchall()
            return [row["fault_type"] for row in rows]

    async def replay_data(
        self,
        device_id: int,
        start_time: datetime,
        end_time: datetime,
        speed_multiplier: float = 1.0,
        include_analysis: bool = False,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        if speed_multiplier <= 0:
            raise ValueError("倍速必须大于0")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM vibration_data
                WHERE device_id = ? AND timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp ASC
                """,
                (device_id, start_time, end_time),
            )
            data_rows = cursor.fetchall()

            if not data_rows:
                logger.warning(
                    f"回放时间段内无数据: 设备ID={device_id}, {start_time} ~ {end_time}"
                )
                return

            logger.info(
                f"开始数据回放: 设备ID={device_id}, {len(data_rows)} 条数据, {speed_multiplier}x 倍速"
            )

            session_id = self._create_replay_session(
                device_id, start_time, end_time, speed_multiplier
            )

            prev_timestamp = None
            total = len(data_rows)

            for index, row in enumerate(data_rows):
                current_timestamp = row["timestamp"]

                if prev_timestamp and index > 0:
                    time_diff = (
                        current_timestamp - prev_timestamp
                    ).total_seconds()
                    adjusted_delay = time_diff / speed_multiplier
                    if adjusted_delay > 0:
                        await asyncio.sleep(adjusted_delay)

                prev_timestamp = current_timestamp

                vibration_data = self._row_to_vibration_data(row)

                response = {
                    "type": "vibration_data",
                    "session_id": session_id,
                    "progress": {"current": index + 1, "total": total},
                    "data": vibration_data.model_dump(mode="json"),
                    "timestamp": datetime.now().isoformat(),
                }

                if include_analysis and row["id"]:
                    cursor.execute(
                        """
                        SELECT * FROM analysis_results
                        WHERE data_id = ?
                        ORDER BY created_at DESC
                        LIMIT 1
                        """,
                        (row["id"],),
                    )
                    analysis_row = cursor.fetchone()
                    if analysis_row:
                        analysis_result = self._row_to_analysis_result(
                            analysis_row
                        )
                        response["analysis"] = analysis_result.model_dump(
                            mode="json"
                        )

                self._update_replay_position(session_id, current_timestamp)
                yield response

            logger.info(f"数据回放完成: 会话ID={session_id}")

    def _create_replay_session(
        self,
        device_id: int,
        start_time: datetime,
        end_time: datetime,
        speed_multiplier: float,
    ) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO replay_sessions (
                    device_id, start_time, end_time, speed_multiplier
                ) VALUES (?, ?, ?, ?)
                """,
                (device_id, start_time, end_time, speed_multiplier),
            )
            conn.commit()
            return cursor.lastrowid

    def _update_replay_position(
        self, session_id: int, current_position: datetime
    ) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE replay_sessions
                SET current_position = ?
                WHERE id = ?
                """,
                (current_position, session_id),
            )
            conn.commit()

    def get_replay_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM replay_sessions WHERE id = ?", (session_id,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "device_id": row["device_id"],
                    "start_time": row["start_time"],
                    "end_time": row["end_time"],
                    "speed_multiplier": row["speed_multiplier"],
                    "is_paused": bool(row["is_paused"]),
                    "current_position": row["current_position"],
                    "created_at": row["created_at"],
                }
            return None

    def pause_replay(self, session_id: int) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE replay_sessions SET is_paused = 1 WHERE id = ?",
                (session_id,),
            )
            conn.commit()

    def resume_replay(self, session_id: int) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE replay_sessions SET is_paused = 0 WHERE id = ?",
                (session_id,),
            )
            conn.commit()

    def get_data_statistics(
        self,
        device_id: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            params: List[Any] = []
            where_clause = "WHERE 1=1"

            if device_id is not None:
                where_clause += " AND device_id = ?"
                params.append(device_id)

            if start_time:
                where_clause += " AND timestamp >= ?"
                params.append(start_time)

            if end_time:
                where_clause += " AND timestamp <= ?"
                params.append(end_time)

            cursor.execute(
                f"""
                SELECT
                    COUNT(*) as total_records,
                    COUNT(DISTINCT device_id) as device_count,
                    MIN(timestamp) as earliest_time,
                    MAX(timestamp) as latest_time,
                    SUM(CASE WHEN is_fault_sample = 1 THEN 1 ELSE 0 END) as fault_samples
                FROM vibration_data
                {where_clause}
                """,
                params,
            )
            data_row = cursor.fetchone()

            cursor.execute(
                f"""
                SELECT
                    COUNT(*) as total_analysis,
                    AVG(health_index) as avg_health_index,
                    SUM(CASE WHEN status = ? THEN 1 ELSE 0 END) as normal_count,
                    SUM(CASE WHEN status = ? THEN 1 ELSE 0 END) as warning_count,
                    SUM(CASE WHEN status = ? THEN 1 ELSE 0 END) as error_count
                FROM analysis_results
                {where_clause}
                """,
                [DeviceStatus.ONLINE.value, DeviceStatus.WARNING.value, DeviceStatus.ERROR.value]
                + params,
            )
            analysis_row = cursor.fetchone()

            cursor.execute(
                f"""
                SELECT fault_type, COUNT(*) as count
                FROM vibration_data
                {where_clause} AND is_fault_sample = 1
                GROUP BY fault_type
                ORDER BY count DESC
                """,
                params,
            )
            fault_type_rows = cursor.fetchall()
            fault_type_distribution = [
                {"type": row["fault_type"], "count": row["count"]}
                for row in fault_type_rows
            ]

            return {
                "data": {
                    "total_records": data_row["total_records"] or 0,
                    "device_count": data_row["device_count"] or 0,
                    "earliest_time": data_row["earliest_time"],
                    "latest_time": data_row["latest_time"],
                    "fault_samples": data_row["fault_samples"] or 0,
                },
                "analysis": {
                    "total_analysis": analysis_row["total_analysis"] or 0,
                    "avg_health_index": round(
                        analysis_row["avg_health_index"] or 0, 2
                    ),
                    "status_distribution": {
                        "normal": analysis_row["normal_count"] or 0,
                        "warning": analysis_row["warning_count"] or 0,
                        "error": analysis_row["error_count"] or 0,
                    },
                },
                "fault_type_distribution": fault_type_distribution,
            }

    def delete_old_data(self, days_to_keep: int) -> int:
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM vibration_data WHERE timestamp < ?",
                (cutoff_date,),
            )
            count = cursor.fetchone()[0]

            cursor.execute(
                "DELETE FROM vibration_data WHERE timestamp < ?",
                (cutoff_date,),
            )
            conn.commit()

            logger.info(f"清理历史数据: 删除 {count} 条记录 (保留最近 {days_to_keep} 天)")
            return count

    def export_data(
        self,
        output_path: str,
        device_id: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        include_analysis: bool = True,
    ) -> int:
        data_list, total = self.get_vibration_data(
            page=1,
            page_size=100000,
            device_id=device_id,
            start_time=start_time,
            end_time=end_time,
        )

        export_data = {
            "export_time": datetime.now().isoformat(),
            "time_range": {
                "start": start_time.isoformat() if start_time else None,
                "end": end_time.isoformat() if end_time else None,
            },
            "device_id": device_id,
            "total_records": total,
            "vibration_data": [
                d.model_dump(mode="json") for d in data_list
            ],
        }

        if include_analysis and total > 0:
            analysis_list, _ = self.get_analysis_results(
                page=1,
                page_size=100000,
                device_id=device_id,
                start_time=start_time,
                end_time=end_time,
            )
            export_data["analysis_results"] = [
                a.model_dump(mode="json") for a in analysis_list
            ]

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        logger.info(f"数据导出完成: {output_path}, 共 {total} 条记录")
        return total

    def create_diagnosis_task(
        self,
        device_id: int,
        device_name: Optional[str],
        start_time: datetime,
        end_time: datetime,
    ) -> DiagnosisTask:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO diagnosis_tasks (
                    device_id, device_name, start_time, end_time, status
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    device_id,
                    device_name,
                    start_time,
                    end_time,
                    DiagnosisStatus.PENDING.value,
                ),
            )
            task_id = cursor.lastrowid
            conn.commit()
            return self.get_diagnosis_task(task_id)

    def get_diagnosis_task(self, task_id: int) -> Optional[DiagnosisTask]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM diagnosis_tasks WHERE id = ?", (task_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_diagnosis_task(row)
            return None

    def get_diagnosis_tasks(
        self,
        page: int = 1,
        page_size: int = 10,
        device_id: Optional[int] = None,
        status: Optional[DiagnosisStatus] = None,
    ) -> Tuple[List[DiagnosisTask], int]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM diagnosis_tasks WHERE 1=1"
            params: List[Any] = []

            if device_id is not None:
                query += " AND device_id = ?"
                params.append(device_id)

            if status:
                query += " AND status = ?"
                params.append(status.value)

            count_query = query.replace("SELECT *", "SELECT COUNT(*)")
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]

            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([page_size, (page - 1) * page_size])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return (
                [self._row_to_diagnosis_task(row) for row in rows],
                total,
            )

    def update_diagnosis_task(
        self,
        task_id: int,
        status: Optional[DiagnosisStatus] = None,
        feature_snapshot: Optional[FeatureSnapshot] = None,
        match_results: Optional[List[FaultMatchResult]] = None,
    ) -> Optional[DiagnosisTask]:
        with self._get_connection() as conn:
            cursor = conn.cursor()

            update_fields = []
            update_params = []

            if status is not None:
                update_fields.append("status = ?")
                update_params.append(status.value)

            if feature_snapshot is not None:
                update_fields.append("feature_snapshot = ?")
                update_params.append(feature_snapshot.model_dump(mode="json"))

            if match_results is not None:
                update_fields.append("match_results = ?")
                update_params.append([m.model_dump(mode="json") for m in match_results])

            if status == DiagnosisStatus.COMPLETED or (status is None and match_results is not None):
                update_fields.append("completed_at = ?")
                update_params.append(datetime.now())

            if not update_fields:
                return self.get_diagnosis_task(task_id)

            update_params.append(task_id)

            cursor.execute(
                f"UPDATE diagnosis_tasks SET {', '.join(update_fields)} WHERE id = ?",
                update_params,
            )
            conn.commit()

            if cursor.rowcount == 0:
                return None

            return self.get_diagnosis_task(task_id)

    def _row_to_diagnosis_task(self, row: sqlite3.Row) -> DiagnosisTask:
        feature_snapshot = None
        if row["feature_snapshot"]:
            feature_snapshot = FeatureSnapshot.model_validate(row["feature_snapshot"])

        match_results = None
        if row["match_results"]:
            match_results = [
                FaultMatchResult.model_validate(m) for m in row["match_results"]
            ]

        return DiagnosisTask(
            id=row["id"],
            device_id=row["device_id"],
            device_name=row["device_name"],
            start_time=row["start_time"],
            end_time=row["end_time"],
            status=DiagnosisStatus(row["status"]),
            feature_snapshot=feature_snapshot,
            match_results=match_results,
            created_at=row["created_at"],
            completed_at=row["completed_at"],
        )

    def get_fault_knowledge(
        self,
        page: int = 1,
        page_size: int = 100,
    ) -> Tuple[List[FaultModeKnowledge], int]:
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) as count FROM fault_mode_knowledge")
            total = cursor.fetchone()["count"]

            cursor.execute(
                "SELECT * FROM fault_mode_knowledge ORDER BY id LIMIT ? OFFSET ?",
                (page_size, (page - 1) * page_size),
            )
            rows = cursor.fetchall()

            return (
                [self._row_to_fault_knowledge(row) for row in rows],
                total,
            )

    def get_all_fault_knowledge(self) -> List[FaultModeKnowledge]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM fault_mode_knowledge ORDER BY id"
            )
            rows = cursor.fetchall()
            return [self._row_to_fault_knowledge(row) for row in rows]

    def create_fault_knowledge(
        self,
        name: str,
        description: str,
        key_frequency_features: str,
        severity_level: SeverityLevel,
        maintenance_action: str,
    ) -> FaultModeKnowledge:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO fault_mode_knowledge (
                        name, description, key_frequency_features, severity_level, maintenance_action
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        name,
                        description,
                        key_frequency_features,
                        severity_level.value,
                        maintenance_action,
                    ),
                )
                knowledge_id = cursor.lastrowid
                conn.commit()
            except sqlite3.IntegrityError as e:
                raise ValueError(f"故障模式名称已存在: {name}") from e

            cursor.execute(
                "SELECT * FROM fault_mode_knowledge WHERE id = ?", (knowledge_id,)
            )
            row = cursor.fetchone()
            return self._row_to_fault_knowledge(row)

    def delete_fault_knowledge(self, knowledge_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM fault_mode_knowledge WHERE id = ?", (knowledge_id,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def _row_to_fault_knowledge(self, row: sqlite3.Row) -> FaultModeKnowledge:
        return FaultModeKnowledge(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            key_frequency_features=row["key_frequency_features"],
            severity_level=SeverityLevel(row["severity_level"]),
            maintenance_action=row["maintenance_action"],
            created_at=row["created_at"],
        )


_database_instance: Optional[Database] = None


def get_database() -> Database:
    global _database_instance
    if _database_instance is None:
        _database_instance = Database()
    return _database_instance
