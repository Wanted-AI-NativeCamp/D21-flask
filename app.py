# 컴퓨터에 적어 둔 환경 변수(비밀 값)를 읽는 도구를 가져온다
import os
# "30일" 같은 기간을 적는 도구를 가져온다
from datetime import timedelta
# .env 파일에 적어 둔 값을 환경 변수로 읽어 오는 도구(python-dotenv)를 가져온다
from dotenv import load_dotenv
# Flask 도구 상자에서 Flask 클래스, 오류를 일부러 내는 abort, 한 번만 보이는 안내를 남기는 flash, JSON으로 답하는 jsonify, 다른 주소로 돌려보내는 redirect, 화면을 만드는 render_template, 주소의 ?조건과 폼 값을 읽는 request, 손님별 기억 상자 session, 함수 이름으로 주소를 만드는 url_for를 가져온다
from flask import Flask, abort, flash, jsonify, redirect, render_template, request, session, url_for
# 같은 폴더의 data.py에서 CSV를 읽고, 번호로 찾고, 거르고 정렬하고, JSON용으로 바꾸고, 통계를 내는 함수들을 가져온다
from data import find_class, get_categories, get_stats, load_classes, search, to_api
# 같은 폴더의 db.py에서 후기를 DB에 저장하는 함수와, 그 클래스의 후기를 꺼내는 함수를 가져온다
from db import add_review, list_reviews

# app.py 옆의 .env 파일을 읽어서 안에 적힌 값을 환경 변수로 만든다. 앱을 만들기 전에 해야 FLASK_DEBUG도 반영된다
# 컴퓨터에 이미 같은 이름의 환경 변수가 있으면(예: 배포 서버에서 직접 넣은 값) 그 값을 우선한다. 서버에는 .env 파일이 없다
load_dotenv()

# 우리 가게(앱)를 하나 만든다. __name__은 "지금 이 파일이 가게 본점이에요"라고 알려 주는 이름표다
app = Flask(__name__)

# flash 안내와 찜 목록(session)은 손님 브라우저의 쪽지(쿠키)에 담겨 오가는데, 이 쪽지에 도장(비밀 열쇠)을 찍어서 위조를 막는다
# 열쇠는 코드에 적지 않고, .env(환경 변수 SECRET_KEY)에서만 가져온다. .env는 깃에 올리지 않는다
app.secret_key = os.environ.get("SECRET_KEY")
# 열쇠가 없거나 비어 있으면, 연습용 값으로 슬쩍 넘어가지 않고 켜는 순간 멈춰서 이유를 알려 준다
if not app.secret_key:
    # 멈추면서 보여 줄 안내 문장: 해야 할 일을 그대로 적는다
    raise RuntimeError("SECRET_KEY가 없어요. .env.example을 .env로 복사하고 SECRET_KEY를 채워 주세요 (만드는 법은 .env.example에 있어요)")
# 세션 쪽지(쿠키)를 브라우저를 닫아도 30일 동안 남긴다. 이 줄이 없으면 브라우저를 닫는 순간 찜 목록이 사라진다
app.permanent_session_lifetime = timedelta(days=30)
# 다른 사이트에서 날아온 POST에는 세션 쪽지를 같이 보내지 않게 한다 (남이 내 찜을 마음대로 바꾸는 것을 줄여 준다)
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


# 이 손님의 찜 목록(클래스 번호들)을 꺼내는 함수. 처음이면 빈 목록이다. list()로 복사해서 돌려주니, 고쳐 써도 session 원본은 그대로다
def get_wishlist():
    # session은 손님별 기억 상자다. "wishlist" 칸에 번호 목록이 들어 있다
    return list(session.get("wishlist", []))


# 모든 화면의 템플릿에 wish_count(찜한 개수)를 자동으로 넘긴다. 메뉴의 '찜 목록 (개수)'가 이 값을 쓴다
@app.context_processor
def inject_wish_count():
    # 찜한 개수를 wish_count라는 이름으로 넘긴다
    return {"wish_count": len(get_wishlist())}

# JSON 설정: 한글을 \uXXXX 같은 암호 모양으로 바꾸지 않고 그대로 내보낸다
app.json.ensure_ascii = False
# JSON 설정: 항목 순서를 알파벳순으로 다시 섞지 않고, 내가 적은 순서 그대로 내보낸다
app.json.sort_keys = False


# 손님이 주소 "/" (맨 첫 페이지)로 들어오면 아래 함수를 실행하라고 연결한다 (홀 직원이 주문을 넘기는 곳)
@app.route("/")
# 주문을 받았을 때 실행할 함수(주방)를 만든다. 이 함수 이름 home을 base.html의 url_for('home')이 찾아 쓴다
def home():
    # CSV에서 클래스 전체를 읽어 온다
    classes = load_classes()
    # templates/home.html에 전체 개수와 카테고리 목록을 넘겨서 화면을 만든다
    return render_template("home.html", total=len(classes), categories=get_categories(classes))


# 손님이 주소 "/classes"로 들어오면 아래 함수를 실행하라고 연결한다. 뒤에 ?category=공예&sort=price 같은 조건이 붙을 수 있다
@app.route("/classes")
# 클래스 목록 화면을 돌려주는 함수(주방)를 만든다. 이름 class_list를 url_for('class_list')가 찾아 쓴다
def class_list():
    # CSV에서 클래스 전체를 읽어 온다
    all_classes = load_classes()
    # 주소의 ?category= 값을 읽는다. 없으면 빈 글자(= 거르지 않음)
    category = request.args.get("category", "").strip()
    # 주소의 ?sort= 값을 읽는다. 없으면 빈 글자(= 정렬하지 않음)
    sort = request.args.get("sort", "").strip()
    # 정해 둔 정렬 이름(price, rating)이 아니면 무시하고 정렬하지 않는다
    if sort not in ("price", "rating"):
        sort = ""
    # 카테고리로 거르고 정렬한 결과를 얻는다
    result = search(all_classes, category, sort)
    # templates/classes.html에 결과와 현재 선택 상태를 넘겨서 화면을 만든다
    return render_template(
        "classes.html",
        classes=result,
        categories=get_categories(all_classes),
        category=category,
        sort=sort,
    )


# 손님이 주소 "/class/번호"로 들어오면 아래 함수를 실행하라고 연결한다. <int:class_id>는 "숫자만 받아서 class_id로 쓸게요"라는 뜻이다
# methods에 GET(엽서: 화면 보기)과 POST(봉투: 후기 보내기)를 둘 다 적는다. POST를 안 적으면 후기를 보낼 때 405가 나온다
@app.route("/class/<int:class_id>", methods=["GET", "POST"])
# 클래스 한 개를 보여 주는 상세 화면 함수(주방)를 만든다. 이름 class_detail을 url_for('class_detail', ...)이 찾아 쓴다
def class_detail(class_id):
    # CSV에서 읽은 전체 목록 안에서, 주소에 적힌 번호의 클래스를 찾는다
    item = find_class(load_classes(), class_id)
    # 그런 번호의 클래스가 없으면
    if item is None:
        # 진짜 404(찾을 수 없음) 상태 코드로 요청을 끝낸다. 보여 줄 화면은 아래 page_not_found가 만든다
        abort(404)
    # 폼 칸에 다시 채워 줄 값. 처음 열 때는 세 칸 모두 비어 있다
    form = {"nickname": "", "rating": "", "content": ""}
    # 틀린 곳을 알려 줄 문장들을 담는 빈 목록
    errors = []
    # 화면에 붙일 상태 코드. 기본은 200(잘 열렸어요)
    status = 200
    # 봉투(POST)로 들어온 경우에만 후기 저장을 시도한다
    if request.method == "POST":
        # 봉투 안의 세 칸을 꺼내서 앞뒤 공백을 지운다. .get을 쓰면 칸이 없어도 에러 대신 빈 글자가 된다
        form = {
            # 닉네임 칸 (name="nickname")
            "nickname": request.form.get("nickname", "").strip(),
            # 별점 칸 (name="rating")
            "rating": request.form.get("rating", "").strip(),
            # 후기 내용 칸 (name="content")
            "content": request.form.get("content", "").strip(),
        }
        # 닉네임이 비어 있으면
        if form["nickname"] == "":
            # 틀린 곳 목록에 문장을 더한다
            errors.append("닉네임을 적어 주세요")
        # 닉네임이 20글자보다 길면
        elif len(form["nickname"]) > 20:
            # 틀린 곳 목록에 문장을 더한다
            errors.append("닉네임은 20글자까지 적을 수 있어요")
        # 별점이 "1"~"5" 중 하나가 아니면 (별점 6, 빈 값, 글자 모두 여기서 걸린다)
        if form["rating"] not in ("1", "2", "3", "4", "5"):
            # 틀린 곳 목록에 문장을 더한다
            errors.append("별점은 1~5 중에서 골라 주세요")
        # 후기 내용이 비어 있으면
        if form["content"] == "":
            # 틀린 곳 목록에 문장을 더한다
            errors.append("후기 내용을 적어 주세요")
        # 후기 내용이 500글자보다 길면
        elif len(form["content"]) > 500:
            # 틀린 곳 목록에 문장을 더한다
            errors.append("후기 내용은 500글자까지 적을 수 있어요")
        # 틀린 곳이 하나도 없으면 저장한다
        if not errors:
            # DB(reviews.db)에 후기 한 개를 저장한다. 별점은 글자("5")를 숫자(5)로 바꿔서 넘긴다
            add_review(class_id, form["nickname"], int(form["rating"]), form["content"])
            # "저장됐어요" 안내를 쪽지에 남긴다. 다음에 화면을 한 번 열면 꺼내 보여 주고, 꺼내면 사라진다
            flash("후기가 저장 됐어요")
            # 저장에 성공하면 같은 상세 화면으로 돌려보낸다(302). 이 뒤의 화면은 POST가 아니라 GET이라서, 새로고침해도 후기가 또 저장되지 않는다
            # _anchor는 주소 뒤에 #review-form-title을 붙여서, 화면이 열릴 때 후기 칸으로 바로 내려가 안내가 보이게 한다
            return redirect(url_for("class_detail", class_id=class_id, _anchor="review-form-title"))
        # 틀린 곳이 있으면 저장하지 않고, 상태 코드를 400(보낸 값이 틀렸어요)으로 바꾼다
        status = 400
    # 클래스 정보, 이 클래스의 후기 목록(DB에서 최신순으로 꺼낸다. 없으면 빈 목록), 폼 칸 값, 틀린 곳 목록을 templates/class_detail.html에 넘겨서 화면을 만들고, 뒤에 상태 코드를 붙인다
    return render_template(
        "class_detail.html",
        item=item,
        reviews=list_reviews(class_id),
        # 이 클래스를 이미 찜했는지(참/거짓). 버튼 글자를 '찜하기'와 '찜 취소' 중에서 고르는 데 쓴다
        is_wished=class_id in get_wishlist(),
        form=form,
        errors=errors,
    ), status


# 주소 "/class/번호/wish"를 연결한다. 찜을 켜고 끄는 건 값을 바꾸는 일이라 POST(봉투)만 받는다. 주소창으로 열면(GET) 405가 나온다
@app.route("/class/<int:class_id>/wish", methods=["POST"])
# 찜 켜고 끄기 함수(주방)를 만든다. 이름 toggle_wish를 url_for('toggle_wish', ...)이 찾아 쓴다
def toggle_wish(class_id):
    # 없는 클래스 번호면 찜 목록에 쓰레기 번호가 쌓이지 않도록 404로 끝낸다
    if find_class(load_classes(), class_id) is None:
        # 진짜 404(찾을 수 없음) 상태 코드로 요청을 끝낸다
        abort(404)
    # 이 손님의 찜 목록을 복사해서 꺼낸다
    ids = get_wishlist()
    # 이미 찜한 클래스면
    if class_id in ids:
        # 찜 목록에서 뺀다 (찜 취소)
        ids.remove(class_id)
    # 아직 찜하지 않은 클래스면
    else:
        # 찜 목록 맨 뒤에 더한다 (찜하기)
        ids.append(class_id)
    # 바뀐 목록을 기억 상자에 다시 넣는다. 새 목록을 통째로 넣어야 Flask가 "바뀌었네" 하고 쪽지를 새로 써서 보낸다
    session["wishlist"] = ids
    # 이 쪽지는 브라우저를 닫아도 남게(위에서 정한 30일) 표시한다
    session.permanent = True
    # 찜 목록 화면의 버튼이 보낸 요청이면(봉투 안 from 칸이 정확히 "wishlist"일 때만) 찜 목록 화면으로 돌려보낸다(302). 그 밖의 값은 믿지 않고 무시한다
    if request.form.get("from") == "wishlist":
        # 찜 목록 화면(/wishlist)으로 돌려보낸다
        return redirect(url_for("wishlist"))
    # 그 밖에는 그 클래스의 상세 화면으로 돌려보낸다(302). 새로고침해도 찜이 다시 바뀌지 않는다
    return redirect(url_for("class_detail", class_id=class_id))


# 손님이 주소 "/wishlist"로 들어오면 아래 함수를 실행하라고 연결한다
@app.route("/wishlist")
# 내 찜 목록 화면 함수(주방)를 만든다. 이름 wishlist를 url_for('wishlist')가 찾아 쓴다
def wishlist():
    # 이 손님의 찜 번호들을 꺼낸다
    ids = get_wishlist()
    # CSV의 번호는 글자("1")라서, 번호(글자) → 클래스 정보 사전을 만들어 둔다
    by_id = {item["id"]: item for item in load_classes()}
    # 가장 나중에 찜한 클래스가 위에 오도록 번호를 거꾸로 훑어서 클래스 정보를 모은다. CSV에서 사라진 번호는 건너뛴다
    items = [by_id[str(i)] for i in reversed(ids) if str(i) in by_id]
    # templates/wishlist.html에 찜한 클래스 목록을 넘겨서 화면을 만든다
    return render_template("wishlist.html", classes=items)


# 손님이 주소 "/api/classes"로 들어오면 클래스 목록을 JSON으로 돌려준다. 뒤에 ?category=공예 같은 조건이 붙을 수 있다
@app.route("/api/classes")
# 목록 JSON 함수(주방)를 만든다
def api_classes():
    # 주소의 ?category= 값을 읽는다. 없으면 빈 글자(= 거르지 않음)
    category = request.args.get("category", "").strip()
    # 카테고리로 거른 결과를 얻는다 (정렬은 하지 않는다)
    result = search(load_classes(), category)
    # 개수(count)와 클래스 목록(classes)을 JSON으로 돌려준다. 값 없음(None)은 null로 나간다
    return jsonify(count=len(result), classes=[to_api(item) for item in result])


# 손님이 주소 "/api/classes/번호"로 들어오면 클래스 한 개를 JSON으로 돌려준다
@app.route("/api/classes/<int:class_id>")
# 한 개 JSON 함수(주방)를 만든다
def api_class_detail(class_id):
    # CSV에서 읽은 전체 목록 안에서, 주소에 적힌 번호의 클래스를 찾는다
    item = find_class(load_classes(), class_id)
    # 그런 번호의 클래스가 없으면
    if item is None:
        # JSON 에러 메시지와 함께, 상태 코드도 진짜 404로 보낸다
        return jsonify(error="찾는 클래스가 없어요", status=404), 404
    # 찾았으면 그 클래스를 JSON으로 돌려준다
    return jsonify(to_api(item))


# 손님이 주소 "/api/stats"로 들어오면 전체 통계를 JSON으로 돌려준다
@app.route("/api/stats")
# 통계 JSON 함수(주방)를 만든다
def api_stats():
    # data.py가 계산해 준 통계를 그대로 JSON으로 돌려준다
    return jsonify(get_stats(load_classes()))


# 어떤 주소에서든 404(찾을 수 없음)가 나면 아래 함수가 대신 답을 만든다 (없는 클래스 번호, 없는 주소 모두)
@app.errorhandler(404)
# 오류 정보(error)를 받는 함수(주방)를 만든다. 지금은 오류 정보를 쓰지 않는다
def page_not_found(error):
    # 주소가 /api 로 시작하면, 프로그램이 읽는 JSON으로 답하고 상태 코드도 진짜 404로 보낸다 (화면 글자를 보내면 프로그램이 못 읽는다)
    if request.path == "/api" or request.path.startswith("/api/"):
        return jsonify(error="찾는 주소가 없어요", status=404), 404
    # 그 밖의 주소는 "찾는 페이지가 없어요" 화면을 만들고, 뒤에 404를 붙여서 상태 코드도 진짜 404로 보낸다 (화면만 404처럼 보이면 안 되니까)
    return render_template("not_found.html"), 404


# 서버 안에서 코드가 에러를 내서 500이 되면 아래 함수가 대신 답을 만든다
# 디버그를 끈 배포 서버에서 쓰인다. 디버그를 켠 내 컴퓨터에서는 이 화면 대신 자세한 에러 화면이 뜬다. 에러 내용은 서버 로그에 남는다
@app.errorhandler(500)
# 오류 정보(error)를 받는 함수(주방)를 만든다. 에러 내용은 손님에게 보여 주면 안 되니 쓰지 않는다
def server_error(error):
    # 주소가 /api 로 시작하면, 프로그램이 읽는 JSON으로 답하고 상태 코드도 진짜 500으로 보낸다
    if request.path == "/api" or request.path.startswith("/api/"):
        return jsonify(error="서버에 문제가 생겼어요", status=500), 500
    # 그 밖의 주소는 "문제가 생겼어요" 화면을 만들고, 뒤에 500을 붙여서 상태 코드도 진짜 500으로 보낸다
    return render_template("500.html"), 500


# 손님이 주소 "/about"으로 들어오면 아래 함수를 실행하라고 연결한다
@app.route("/about")
# 서비스 소개 화면을 돌려주는 함수(주방)를 만든다
def about():
    # templates/about.html을 골라서 화면으로 만들어 내보낸다
    return render_template("about.html")


# 주소 "/hello/이름" 형태를 연결한다. <name> 자리에는 손님이 적은 글자가 들어온다
@app.route("/hello/<name>")
# 주소에서 꺼낸 name을 함수가 받아서 쓴다 (주문서에 적힌 이름을 그대로 읽는 것과 같다)
def hello(name):
    # templates/hello.html에 name을 넘겨서 화면을 만든다. 템플릿의 {{ name }} 자리에 이름이 들어간다
    return render_template("hello.html", name=name)


# 이 파일을 직접 실행했을 때만 아래 줄이 동작한다 (다른 파일이 가져다 쓸 때는 실행되지 않는다)
if __name__ == "__main__":
    # 가게 문을 연다. debug는 코드를 고치면 자동으로 다시 시작해 주고 오류도 자세히 보여 주는 설정이다
    # 환경 변수 FLASK_DEBUG가 정확히 "1"일 때만 켠다. 내 컴퓨터의 .env에만 1을 적어 두니, 배포 서버에서는 켜지지 않는다
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
