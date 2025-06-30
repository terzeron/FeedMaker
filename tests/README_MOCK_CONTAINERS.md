# Mock Containers 사용법

이 문서는 `tests/common_test_util.py`에 구현된 Loki와 MySQL mock containers의 사용법을 설명합니다.

## 개요

외부 저장소 의존성(Loki, MySQL)을 테스트하기 위해 testcontainers를 사용하여 실제 컨테이너를 띄우고 테스트하는 방법을 제공합니다.

## 주요 기능

### 1. Loki Container

- Grafana Loki 컨테이너를 띄워서 로그 저장소 테스트
- HTTP API를 통한 로그 푸시/쿼리 테스트 가능
- 실제 Loki와 동일한 API 인터페이스 제공

### 2. MySQL Container

- MySQL 8.0 컨테이너를 띄워서 데이터베이스 테스트
- SQLAlchemy를 통한 데이터베이스 작업 테스트 가능
- 실제 MySQL과 동일한 SQL 인터페이스 제공

## 사용법

### 기본 사용법

```python
from tests.common_test_util import start_loki_container, start_mysql_container

# Loki 컨테이너 시작
with start_loki_container() as loki:
    loki_url = loki.get_url()
    # Loki API 테스트 코드...

# MySQL 컨테이너 시작
with start_mysql_container() as mysql:
    mysql_url = mysql.get_connection_url()
    # MySQL 테스트 코드...
```

### 병렬 시작 (성능 최적화)

```python
from tests.common_test_util import start_containers_parallel

# Loki와 MySQL을 동시에 시작
with start_containers_parallel() as (loki, mysql):
    loki_url = loki.get_url()
    mysql_url = mysql.get_connection_url()
    # 테스트 코드...
```

### Loki API 테스트 예시

```python
import requests

with start_loki_container() as loki:
    loki_url = loki.get_url()

    # 1. Loki 상태 확인
    response = requests.get(f"{loki_url}/ready")
    assert response.status_code == 200

    # 2. 로그 푸시
    test_logs = {
        "streams": [{
            "stream": {"job": "test"},
            "values": [["1640995200000000000", "Test log message"]]
        }]
    }

    response = requests.post(
        f"{loki_url}/loki/api/v1/push",
        json=test_logs,
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 204

    # 3. 로그 쿼리
    response = requests.get(
        f"{loki_url}/loki/api/v1/query",
        params={"query": "{job=\"test\"}"}
    )
    assert response.status_code == 200
```

### MySQL 테스트 예시

```python
from sqlalchemy import create_engine, text

with start_mysql_container() as mysql:
    mysql_url = mysql.get_connection_url()
    engine = create_engine(mysql_url)

    with engine.connect() as conn:
        # 테이블 생성
        conn.execute(text("""
            CREATE TABLE test_table (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100)
            )
        """))
        conn.commit()

        # 데이터 삽입
        conn.execute(text("INSERT INTO test_table (name) VALUES ('test')"))
        conn.commit()

        # 데이터 조회
        result = conn.execute(text("SELECT * FROM test_table"))
        rows = result.fetchall()
        assert len(rows) == 1
```

## 장점

### 1. 실제 환경과 유사한 테스트

- 실제 Loki/MySQL과 동일한 API/SQL 인터페이스
- 네트워크 통신, 에러 처리 등 실제 환경과 동일한 조건

### 2. 격리된 테스트 환경

- 각 테스트마다 새로운 컨테이너 인스턴스
- 테스트 간 간섭 없음

### 3. 자동 정리

- `with` 문을 사용하면 테스트 완료 후 자동으로 컨테이너 정리
- 리소스 누수 방지

## 주의사항

### 1. Docker 필요

- testcontainers는 Docker가 설치되어 있어야 함
- Docker 데몬이 실행 중이어야 함

### 2. 시작 시간

- 컨테이너 시작에 시간이 걸림 (Loki: ~10-15초, MySQL: ~5-10초)
- 병렬 시작을 사용하면 전체 시간 단축 가능

### 3. 리소스 사용

- 각 컨테이너는 메모리와 CPU를 사용
- 테스트 환경에 따라 리소스 제한 필요할 수 있음

## 기존 코드와의 통합

### test_problem_manager.py에서 사용 예시

```python
from tests.common_test_util import start_loki_container, start_mysql_container

class TestProblemManager(unittest.TestCase):
    def setUp(self):
        # Loki와 MySQL 컨테이너 시작
        self.loki = start_loki_container()
        self.mysql = start_mysql_container()

        # DB 설정
        db_config = {
            "drivername": "mysql+pymysql",
            "username": self.mysql.get_connection_url().split("://")[1].split(":")[0],
            "password": self.mysql.get_connection_url().split(":")[2].split("@")[0],
            "host": "localhost",
            "port": int(self.mysql.get_exposed_port(3306)),
            "database": "test"
        }
        DB.init(db_config)

        # ProblemManager 생성
        self.pm = ProblemManager(self.loki.get_url())

    def tearDown(self):
        # 컨테이너 정리
        self.loki.stop()
        self.mysql.stop()
        DB.dispose_all()
```

## 문제 해결

### 1. 컨테이너 시작 실패

- Docker가 실행 중인지 확인
- 포트 충돌 확인 (3100, 3306)
- 이미지 다운로드 실패 시 네트워크 연결 확인

### 2. 연결 타임아웃

- 컨테이너가 완전히 시작될 때까지 대기 시간 증가
- `wait_for_ready()` 메서드 사용

### 3. 메모리 부족

- 컨테이너 리소스 제한 설정
- 불필요한 컨테이너 정리
