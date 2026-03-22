from fastapi import FastAPI, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

app = FastAPI()
wishlist = []

courses = [
    {"id": 1, "title": "Python Basics", "instructor": "Alice", "category": "Data Science", "level": "Beginner", "price": 0, "seats_left": 10},
    {"id": 2, "title": "React JS", "instructor": "Bob", "category": "Web Dev", "level": "Intermediate", "price": 999, "seats_left": 5},
    {"id": 3, "title": "UI Design", "instructor": "Carol", "category": "Design", "level": "Beginner", "price": 499, "seats_left": 8},
    {"id": 4, "title": "Docker Mastery", "instructor": "Dan", "category": "DevOps", "level": "Advanced", "price": 1499, "seats_left": 3},
    {"id": 5, "title": "Machine Learning", "instructor": "Eve", "category": "Data Science", "level": "Advanced", "price": 1999, "seats_left": 2},
    {"id": 6, "title": "HTML & CSS", "instructor": "Frank", "category": "Web Dev", "level": "Beginner", "price": 0, "seats_left": 15},
]

enrollments = []
enrollment_counter = 1

#1
@app.get("/")
def home():
    return {"message": "Welcome to LearnHub Online Courses"}

#2
@app.get("/courses")
def get_courses():
    total_seats = sum(c["seats_left"] for c in courses)
    return {
        "courses": courses,
        "total": len(courses),
        "total_seats_available": total_seats
    }

def find_course(course_id: int):
    for c in courses:
        if c["id"] == course_id:
            return c
    return None

#5
@app.get("/courses/summary")
def course_summary():
    total_courses = len(courses)
    free_courses = len([c for c in courses if c["price"] == 0])
    most_expensive = max(courses, key=lambda c: c["price"])
    total_seats = sum(c["seats_left"] for c in courses)

    category_count = {}
    for c in courses:
        category_count[c["category"]] = category_count.get(c["category"], 0) + 1

    return {
        "total_courses": total_courses,
        "free_courses": free_courses,
        "most_expensive_course": most_expensive,
        "total_seats_available": total_seats,
        "courses_by_category": category_count
    }

@app.get("/courses/{course_id}")
def get_course(course_id: int):
    course = find_course(course_id)
    if not course:
        return {"error": "Course not found"}
    return {"course": course}

#4
@app.get("/enrollments")
def get_enrollments():
    return {
        "enrollments": enrollments,
        "total": len(enrollments)
    }

# 6
class EnrollRequest(BaseModel):
    student_name: str = Field(..., min_length=2)
    course_id: int = Field(..., gt=0)
    email: str = Field(..., min_length=5)
    payment_method: str = "card"
    coupon_code: str = ""
    gift_enrollment: bool = False
    recipient_name: str = ""

#7
def calculate_enrollment_fee(price: int, seats_left: int, coupon_code: str):
    discount_details = []
    final_price = price

    #  Early bird discount
    if seats_left > 5:
        discount = 0.10 * final_price
        final_price -= discount
        discount_details.append(f"10% early bird discount applied")

    #  Coupon logic
    if coupon_code == "STUDENT20":
        discount = 0.20 * final_price
        final_price -= discount
        discount_details.append("20% STUDENT20 coupon applied")

    elif coupon_code == "FLAT500":
        final_price -= 500
        discount_details.append("₹500 FLAT500 coupon applied")

    # Avoid negative price
    final_price = max(0, int(final_price))

    return final_price, discount_details

#8,9
@app.post("/enrollments")
def enroll_course(data: EnrollRequest):
    global enrollment_counter

    #  Validate gift logic
    if data.gift_enrollment and not data.recipient_name:
        raise HTTPException(status_code=400, detail="Recipient name required for gift enrollment")

    #  Check course exists
    course = find_course(data.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    #  Check seats
    if course["seats_left"] <= 0:
        raise HTTPException(status_code=400, detail="No seats available")

    #  Calculate fee
    final_fee, discounts = calculate_enrollment_fee(
        course["price"],
        course["seats_left"],
        data.coupon_code
    )

    #  Reduce seat
    course["seats_left"] -= 1

    #  Create enrollment
    enrollment = {
        "enrollment_id": enrollment_counter,
        "student_name": data.student_name,
        "course_title": course["title"],
        "instructor": course["instructor"],
        "original_price": course["price"],
        "final_fee": final_fee,
        "discounts_applied": discounts,
        "payment_method": data.payment_method,
        "gift": data.gift_enrollment,
        "recipient": data.recipient_name if data.gift_enrollment else None
    }

    enrollments.append(enrollment)
    enrollment_counter += 1

    return {
        "message": "Enrollment successful",
        "enrollment": enrollment
    }

#10
def filter_courses_logic(category=None, level=None, max_price=None, has_seats=None):
    result = courses

    if category is not None:
        result = [c for c in result if c["category"] == category]

    if level is not None:
        result = [c for c in result if c["level"] == level]

    if max_price is not None:
        result = [c for c in result if c["price"] <= max_price]

    if has_seats is not None:
        if has_seats:
            result = [c for c in result if c["seats_left"] > 0]
        else:
            result = [c for c in result if c["seats_left"] == 0]

    return result


@app.get("/courses/filter")
def filter_courses(
    category: str = Query(None),
    level: str = Query(None),
    max_price: int = Query(None),
    has_seats: bool = Query(None),
):
    result = filter_courses_logic(category, level, max_price, has_seats)

    return {
        "filtered_courses": result,
        "count": len(result)
    }

#11
class NewCourse(BaseModel):
    title: str = Field(..., min_length=2)
    instructor: str = Field(..., min_length=2)
    category: str = Field(..., min_length=2)
    level: str = Field(..., min_length=2)
    price: int = Field(..., ge=0)
    seats_left: int = Field(..., gt=0)


@app.post("/courses")
def add_course(new_course: NewCourse, response: Response):
    #  Duplicate check
    existing_titles = [c["title"].lower() for c in courses]
    if new_course.title.lower() in existing_titles:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"error": "Course with this title already exists"}

    new_id = max(c["id"] for c in courses) + 1

    course = {
        "id": new_id,
        "title": new_course.title,
        "instructor": new_course.instructor,
        "category": new_course.category,
        "level": new_course.level,
        "price": new_course.price,
        "seats_left": new_course.seats_left
    }

    courses.append(course)
    response.status_code = status.HTTP_201_CREATED

    return {"message": "Course added", "course": course}

#12
@app.put("/courses/{course_id}")
def update_course(
    course_id: int,
    response: Response,
    price: int = Query(None),
    seats_left: int = Query(None),
):
    course = find_course(course_id)

    if not course:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "Course not found"}

    if price is not None:
        course["price"] = price

    if seats_left is not None:
        course["seats_left"] = seats_left

    return {"message": "Course updated", "course": course}

#13
@app.delete("/courses/{course_id}")
def delete_course(course_id: int, response: Response):
    course = find_course(course_id)

    if not course:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "Course not found"}

    #  Check enrollments dependency
    for e in enrollments:
        if e["course_title"] == course["title"]:
            return {"error": "Cannot delete course with enrolled students"}

    courses.remove(course)
    return {"message": f"Course '{course['title']}' deleted"}

#14
@app.post("/wishlist/add")
def add_to_wishlist(
    student_name: str = Query(...),
    course_id: int = Query(...)
):
    course = find_course(course_id)

    if not course:
        return {"error": "Course not found"}

    #  Prevent duplicate
    for item in wishlist:
        if item["student_name"] == student_name and item["course_id"] == course_id:
            return {"error": "Already in wishlist"}

    wishlist.append({
        "student_name": student_name,
        "course_id": course_id,
        "course_title": course["title"],
        "price": course["price"]
    })

    return {"message": "Added to wishlist"}

@app.get("/wishlist")
def view_wishlist():
    total_value = sum(item["price"] for item in wishlist)

    return {
        "wishlist": wishlist,
        "total_items": len(wishlist),
        "total_value": total_value
    }

#15
@app.delete("/wishlist/remove/{course_id}")
def remove_from_wishlist(course_id: int, student_name: str = Query(...)):
    for item in wishlist:
        if item["course_id"] == course_id and item["student_name"] == student_name:
            wishlist.remove(item)
            return {"message": "Removed from wishlist"}

    return {"error": "Item not found in wishlist"}

@app.post("/wishlist/enroll-all")
def enroll_all(student_name: str, payment_method: str = "card"):
    global enrollment_counter

    student_items = [w for w in wishlist if w["student_name"] == student_name]

    if not student_items:
        return {"error": "Wishlist empty for this student"}

    enrolled = []
    total_cost = 0

    for item in student_items:
        course = find_course(item["course_id"])

        if not course or course["seats_left"] <= 0:
            continue  # skip unavailable

        final_fee, discounts = calculate_enrollment_fee(
            course["price"],
            course["seats_left"],
            ""
        )

        course["seats_left"] -= 1

        enrollment = {
            "enrollment_id": enrollment_counter,
            "student_name": student_name,
            "course_title": course["title"],
            "final_fee": final_fee,
            "payment_method": payment_method
        }

        enrollments.append(enrollment)
        enrolled.append(enrollment)

        total_cost += final_fee
        enrollment_counter += 1

    #  Remove enrolled items from wishlist
    wishlist[:] = [w for w in wishlist if w["student_name"] != student_name]

    return {
        "message": "Bulk enrollment successful",
        "total_enrolled": len(enrolled),
        "grand_total": total_cost,
        "enrollments": enrolled
    }

#16
@app.get("/courses/search")
def search_courses(keyword: str = Query(...)):
    results = [
        c for c in courses
        if keyword.lower() in c["title"].lower()
        or keyword.lower() in c["instructor"].lower()
        or keyword.lower() in c["category"].lower()
    ]

    return {
        "keyword": keyword,
        "total_found": len(results),
        "results": results
    }

#17
@app.get("/courses/sort")
def sort_courses(
    sort_by: str = Query("price"),
    order: str = Query("asc")
):
    if sort_by not in ["price", "title", "seats_left"]:
        return {"error": "Invalid sort_by"}

    if order not in ["asc", "desc"]:
        return {"error": "Invalid order"}

    reverse = (order == "desc")

    sorted_courses = sorted(courses, key=lambda c: c[sort_by], reverse=reverse)

    return {
        "sort_by": sort_by,
        "order": order,
        "courses": sorted_courses
    }

#18
@app.get("/courses/page")
def paginate_courses(
    page: int = Query(1, ge=1),
    limit: int = Query(3, ge=1)
):
    start = (page - 1) * limit
    end = start + limit

    paginated = courses[start:end]

    return {
        "page": page,
        "limit": limit,
        "total": len(courses),
        "total_pages": -(-len(courses) // limit),  # ceiling division
        "courses": paginated
    }

#19
@app.get("/enrollments/search")
def search_enrollments(student_name: str = Query(...)):
    results = [
        e for e in enrollments
        if student_name.lower() in e["student_name"].lower()
    ]

    return {
        "student_name": student_name,
        "total_found": len(results),
        "enrollments": results
    }

@app.get("/enrollments/sort")
def sort_enrollments(order: str = Query("asc")):
    reverse = (order == "desc")

    sorted_data = sorted(enrollments, key=lambda e: e["final_fee"], reverse=reverse)

    return {
        "order": order,
        "enrollments": sorted_data
    }

@app.get("/enrollments/page")
def paginate_enrollments(
    page: int = Query(1, ge=1),
    limit: int = Query(3, ge=1)
):
    start = (page - 1) * limit
    end = start + limit

    paginated = enrollments[start:end]

    return {
        "page": page,
        "limit": limit,
        "total": len(enrollments),
        "total_pages": -(-len(enrollments) // limit),
        "enrollments": paginated
    }

#20
@app.get("/courses/browse")
def browse_courses(
    keyword: str = Query(None),
    category: str = Query(None),
    level: str = Query(None),
    max_price: int = Query(None),
    sort_by: str = Query("price"),
    order: str = Query("asc"),
    page: int = Query(1, ge=1),
    limit: int = Query(3, ge=1)
):
    result = courses

    #  Step 1: Keyword search
    if keyword:
        result = [
            c for c in result
            if keyword.lower() in c["title"].lower()
            or keyword.lower() in c["instructor"].lower()
            or keyword.lower() in c["category"].lower()
        ]

    #  Step 2: Filters
    if category:
        result = [c for c in result if c["category"] == category]

    if level:
        result = [c for c in result if c["level"] == level]

    if max_price is not None:
        result = [c for c in result if c["price"] <= max_price]

    #  Step 3: Sorting
    if sort_by not in ["price", "title", "seats_left"]:
        return {"error": "Invalid sort_by"}

    if order not in ["asc", "desc"]:
        return {"error": "Invalid order"}

    reverse = (order == "desc")
    result = sorted(result, key=lambda c: c[sort_by], reverse=reverse)

    #  Step 4: Pagination
    total = len(result)
    start = (page - 1) * limit
    end = start + limit
    paginated = result[start:end]

    return {
        "filters": {
            "keyword": keyword,
            "category": category,
            "level": level,
            "max_price": max_price
        },
        "sort": {
            "sort_by": sort_by,
            "order": order
        },
        "pagination": {
            "page": page,
            "limit": limit,
            "total_found": total,
            "total_pages": -(-total // limit)
        },
        "courses": paginated
    }
