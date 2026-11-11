# 파일 경로를 다루는 도구(Path)를 가져온다
from pathlib import Path
# SQLite(파일 하나짜리 DB)를 다루는 도구를 가져온다
import sqlite3
# 다 쓰고 나면 연결을 꼭 닫아 주는 도구를 가져온다
from contextlib import closing

# 이 파일(db.py) 옆에 reviews.db 위치를 적어 둔다 (어느 폴더에서 켜도 DB 파일이 엉뚱한 곳에 생기지 않는다)
DB_PATH = Path(__file__).parent / "reviews.db"


# 표(reviews)가 없으면 만들어 주는 함수. 이미 있으면 아무것도 하지 않는다 (IF NOT EXISTS)
def create_table(con):
    # 표를 만드는 SQL 문장. 값이 들어갈 자리는 없고 칸의 규칙만 적는다
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS reviews (
            -- 후기 번호: 넣을 때마다 1, 2, 3... 자동으로 붙는다
            id         INTEGER PRIMARY KEY,
            -- 어느 클래스의 후기인지 (꼭 있어야 한다)
            class_id   INTEGER NOT NULL,
            -- 닉네임: 꼭 있어야 하고 1~20글자
            nickname   TEXT    NOT NULL CHECK (length(nickname) BETWEEN 1 AND 20),
            -- 별점: 꼭 있어야 하고 1~5 사이 숫자만 받는다
            rating     INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
            -- 후기 내용: 꼭 있어야 하고 1~500글자
            content    TEXT    NOT NULL CHECK (length(content) BETWEEN 1 AND 500),
            -- 저장 시각: 안 넣으면 DB가 지금 한국 시간을 자동으로 적는다
            created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
        """
    )


# DB에 연결하는 함수. 연결할 때 표가 없으면 함께 만든다
def connect():
    # reviews.db 파일에 연결한다 (파일이 없으면 새로 생긴다)
    con = sqlite3.connect(DB_PATH)
    # 꺼낸 줄을 칸 이름(row["nickname"])으로도 읽을 수 있게 한다
    con.row_factory = sqlite3.Row
    # 표가 없으면 만든다
    create_table(con)
    # 연결을 돌려준다
    return con


# 후기 한 개를 저장하는 함수. 값 네 개를 받는다
def add_review(class_id, nickname, rating, content):
    # 연결을 열고, 블록이 끝나면 연결을 닫는다
    with closing(connect()) as con:
        # 이 블록이 무사히 끝나면 저장(commit)하고, 에러가 나면 되돌린다(rollback)
        with con:
            # 사용자 값은 SQL 문장에 이어 붙이지 않고, 문장 속 ? 자리에 따로 넘긴다. 그래야 값이 명령이 되지 않는다
            con.execute(
                "INSERT INTO reviews (class_id, nickname, rating, content) VALUES (?, ?, ?, ?)",
                (class_id, nickname, rating, content),
            )


# 그 클래스의 후기를 최신순(나중에 쓴 것이 위)으로 꺼내 주는 함수
def list_reviews(class_id):
    # 연결을 열고, 블록이 끝나면 연결을 닫는다
    with closing(connect()) as con:
        # 이 클래스 번호의 후기만 id가 큰 순서로 꺼낸다. 번호는 ? 자리에 넘긴다 (뒤의 쉼표는 값이 한 개짜리 묶음임을 뜻한다)
        rows = con.execute(
            "SELECT id, class_id, nickname, rating, content, created_at "
            "FROM reviews WHERE class_id = ? ORDER BY id DESC",
            (class_id,),
        ).fetchall()
    # 한 줄씩 사전으로 바꿔서 돌려준다 (템플릿에서 r.nickname처럼 읽을 수 있다)
    return [dict(row) for row in rows]
