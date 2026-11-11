# 파일 경로를 다루는 도구(Path)를 가져온다
from pathlib import Path
# CSV(쉼표로 칸을 나눈 표) 파일을 읽는 도구를 가져온다
import csv
# 숫자가 정상인지(nan이나 무한대가 아닌지) 검사하는 도구를 가져온다
import math

# 이 파일(data.py) 옆 data 폴더의 classes.csv 위치를 적어 둔다 (어느 폴더에서 켜도 길을 잃지 않는다)
CSV_PATH = Path(__file__).parent / "data" / "classes.csv"


# 글자의 앞뒤 공백을 지우는 함수. 칸이 아예 없으면(None) 빈 글자로 바꿔 준다
def clean(text):
    # None이면 빈 글자로 바꾸고, 앞뒤 공백을 지워서 돌려준다
    return (text or "").strip()


# 글자를 숫자로 바꾸는 함수. 쓸 수 없는 값이면 "값 없음(None)"을 돌려준다
def to_number(text):
    # 먼저 공백을 정리한다
    text = clean(text)
    # 칸이 비어 있으면 값 없음
    if text == "":
        return None
    # 숫자로 바꿔 본다
    try:
        number = float(text)
    # 숫자가 아닌 글자(예: "abc")이면 값 없음
    except ValueError:
        return None
    # nan, 무한대, 0 이하는 화면에 보이면 안 되니 값 없음으로 본다
    if not math.isfinite(number) or number <= 0:
        return None
    # 쓸 수 있는 숫자만 돌려준다
    return number


# 가격 글자를 정수로 바꾸는 함수 (25000.0 → 25000). 쓸 수 없으면 값 없음
def to_price(text):
    # 먼저 쓸 수 있는 숫자인지 확인한다
    number = to_number(text)
    # 쓸 수 없으면 값 없음
    if number is None:
        return None
    # 소수점을 떼고 정수로 돌려준다
    return int(number)


# CSV 파일을 읽어서 클래스 목록(사전들의 목록)으로 만들어 주는 함수
def load_classes():
    # 결과를 담을 빈 목록을 만든다
    classes = []
    # 파일을 연다. utf-8-sig는 한글과 엑셀이 붙이는 숨은 표시를 함께 처리해 준다
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as file:
        # 첫 줄(칸 이름)을 기준으로 한 줄씩 사전으로 읽는다
        for row in csv.DictReader(file):
            # 정가를 읽는다 (비면 값 없음)
            list_price = to_price(row["정가"])
            # 할인가를 읽는다 (비면 값 없음)
            discount_price = to_price(row["할인가"])
            # 판매가: 할인가가 있으면 할인가, 없으면 정가
            sale_price = discount_price if discount_price is not None else list_price
            # 클래스 한 개의 정보를 사전으로 묶어서 목록에 넣는다
            classes.append({
                # 번호
                "id": clean(row["id"]),
                # 카테고리
                "category": clean(row["카테고리"]),
                # 지역
                "region": clean(row["지역"]),
                # 클래스 이름
                "name": clean(row["클래스명"]),
                # 정가 (취소선으로 보여 줄 때 쓴다)
                "list_price": list_price,
                # 판매가 (비어 있으면 화면에서 '가격 문의'로 바뀐다)
                "sale_price": sale_price,
                # 할인 중인지: 정가와 할인가가 둘 다 있고 할인가가 더 쌀 때만 참
                "on_sale": (
                    discount_price is not None
                    and list_price is not None
                    and discount_price < list_price
                ),
                # 평점 (비어 있거나 0이면 값 없음)
                "rating": to_number(row["평점"]),
                # 리뷰 수 (비어 있으면 0으로 본다)
                "reviews": int(to_number(row["리뷰수"]) or 0),
            })
    # 완성된 목록을 돌려준다
    return classes


# 카테고리 이름을 처음 나온 순서대로 모아 주는 함수 (중복은 한 번만)
def get_categories(classes):
    # 결과를 담을 빈 목록
    categories = []
    # 클래스를 하나씩 살펴본다
    for item in classes:
        # 이름이 있고 아직 목록에 없으면 추가한다
        if item["category"] and item["category"] not in categories:
            categories.append(item["category"])
    # 모은 카테고리를 돌려준다
    return categories


# 번호(id)로 클래스 한 개를 찾아 주는 함수. 없으면 값 없음(None)을 돌려준다
def find_class(classes, class_id):
    # 클래스를 하나씩 살펴본다
    for item in classes:
        # CSV의 번호는 글자("1")로 저장돼 있으니, 찾는 번호도 글자로 바꿔서 비교한다
        if item["id"] == str(class_id):
            # 찾았으면 그 클래스를 바로 돌려준다
            return item
    # 끝까지 못 찾았으면 값 없음
    return None


# 클래스 한 개를 JSON으로 내보낼 모양의 사전으로 바꿔 주는 함수. 값 없음(None)은 JSON에서 null이 된다
def to_api(item):
    # 번호를 숫자로 바꿔 본다 (CSV에서는 글자로 읽었기 때문)
    try:
        class_id = int(item["id"])
    # 숫자로 바꿀 수 없는 번호면 글자 그대로 둔다
    except ValueError:
        class_id = item["id"]
    # 내보낼 항목을 정해진 순서로 묶어서 돌려준다
    return {
        # 번호
        "id": class_id,
        # 카테고리
        "category": item["category"],
        # 지역
        "region": item["region"],
        # 클래스 이름
        "name": item["name"],
        # 정가 (비어 있으면 null)
        "list_price": item["list_price"],
        # 판매가: 할인가가 있으면 할인가, 없으면 정가 (둘 다 비어 있으면 null = 가격 문의)
        "sale_price": item["sale_price"],
        # 할인 중인지 (true/false)
        "on_sale": item["on_sale"],
        # 평점 (비어 있으면 null)
        "rating": item["rating"],
        # 리뷰 수
        "reviews": item["reviews"],
    }


# 전체 통계를 계산해 주는 함수. 빈칸(None)은 평균 계산에서 뺀다
def get_stats(classes):
    # 판매가가 있는 클래스들의 판매가만 모은다 (가격 문의는 빠진다)
    prices = [item["sale_price"] for item in classes if item["sale_price"] is not None]
    # 평점이 있는 클래스들의 평점만 모은다 (리뷰 없음은 빠진다)
    ratings = [item["rating"] for item in classes if item["rating"] is not None]
    # 카테고리별 개수를 세어 담을 빈 사전을 만든다
    category_counts = {}
    # 클래스를 하나씩 살펴본다
    for item in classes:
        # 카테고리 이름이 있을 때만 센다
        if item["category"]:
            # 지금까지 센 개수(없으면 0)에 1을 더한다
            category_counts[item["category"]] = category_counts.get(item["category"], 0) + 1
    # 통계를 정해진 순서로 묶어서 돌려준다
    return {
        # 전체 개수
        "total": len(classes),
        # 평균 판매가: 원 단위로 반올림. 계산할 값이 하나도 없으면 null (0으로 나누지 않게)
        "average_sale_price": round(sum(prices) / len(prices)) if prices else None,
        # 가격 문의 수: 전체에서 판매가가 있는 수를 뺀 것
        "price_inquiry_count": len(classes) - len(prices),
        # 평균 평점: 소수 둘째 자리까지 반올림. 계산할 값이 하나도 없으면 null
        "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
        # 리뷰 없음 수: 평점이 비어 있는 수
        "no_review_count": len(classes) - len(ratings),
        # 카테고리별 개수
        "category_counts": category_counts,
    }


# 카테고리로 거르고 정렬해서 돌려주는 함수
def search(classes, category="", sort=""):
    # 처음에는 전체 목록에서 시작한다
    result = classes
    # 카테고리가 정해져 있으면, 그 카테고리인 클래스만 남긴다
    if category:
        result = [item for item in result if item["category"] == category]
    # 가격순: 판매가가 싼 순서. '가격 문의'(값 없음)는 맨 뒤로 보낸다
    if sort == "price":
        result = sorted(
            result,
            key=lambda item: (item["sale_price"] is None, item["sale_price"] or 0),
        )
    # 평점순: 높은 순서. 리뷰 없음은 맨 뒤, 평점이 같으면 리뷰가 많은 쪽이 앞
    elif sort == "rating":
        result = sorted(
            result,
            key=lambda item: (item["rating"] is None, -(item["rating"] or 0), -item["reviews"]),
        )
    # 거르고 정렬한 결과를 돌려준다
    return result
