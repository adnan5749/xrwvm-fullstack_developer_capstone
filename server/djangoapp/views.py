from django.contrib.auth.models import User
from django.contrib.auth import logout, login, authenticate
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import logging
import json
from urllib.parse import quote

from .models import CarMake, CarModel
from .populate import initiate
from .restapis import get_request, analyze_review_sentiments, post_review

logger = logging.getLogger(__name__)

@csrf_exempt
def login_user(request):
    data = json.loads(request.body)
    username = data.get('userName')
    password = data.get('password')

    user = authenticate(username=username, password=password)
    ret = {"userName": username}

    if user is not None:
        login(request, user)
        ret = {"userName": username, "status": "Authenticated"}

    return JsonResponse(ret)

@csrf_exempt
def logout_user(request):
    logout(request)
    return JsonResponse({"status": "Logged out"})

@csrf_exempt
def register_user(request):
    if request.method != "POST":
        return JsonResponse({"status": False, "error": "Invalid Method"})

    data = json.loads(request.body)
    username = data.get("userName", "").strip()
    password = data.get("password", "")
    first_name = data.get("firstName", "").strip()
    last_name = data.get("lastName", "").strip()
    email = data.get("email", "").strip()

    if not username or not password:
        return JsonResponse({"status": False, "error": "Missing Credentials"})

    if User.objects.filter(username=username).exists():
        return JsonResponse({"status": False, "error": "Already Registered"})

    user = User.objects.create_user(
        username=username,
        password=password,
        first_name=first_name,
        last_name=last_name,
        email=email,
    )
    login(request, user)
    return JsonResponse({"status": True, "userName": username})

def get_cars(request):
    count = CarMake.objects.filter().count()
    if count == 0:
        initiate()

    car_models = CarModel.objects.select_related('car_make').all()
    cars = []
    for car_model in car_models:
        cars.append({"CarModel": car_model.name, "CarMake": car_model.car_make.name})
    return JsonResponse({"CarModels": cars})

def get_dealerships(request, state="All"):
    if state == "All":
        endpoint = "/fetchDealers"
    else:
        endpoint = "/fetchDealers/" + state

    dealerships = get_request(endpoint)
    return JsonResponse({"status": 200, "dealers": dealerships})

def get_dealer_details(request, dealer_id):
    endpoint = f"/fetchDealer/{dealer_id}"
    dealer = get_request(endpoint)
    return JsonResponse({"status": 200, "dealer": dealer})

def get_dealer_reviews(request, dealer_id):
    endpoint = f"/fetchReviews/dealer/{dealer_id}"
    reviews = get_request(endpoint)

    if reviews is None:
        return JsonResponse({"status": 500, "reviews": [], "message": "Failed to fetch reviews"})

     for r in reviews:
        review_text = r.get("review", "")
        if review_text:
            senti = analyze_review_sentiments(quote(review_text))
             if isinstance(senti, dict) and senti.get("sentiment"):
                r["sentiment"] = senti["sentiment"]
            else:
                r["sentiment"] = "neutral"
        else:
            r["sentiment"] = "neutral"

    return JsonResponse({"status": 200, "reviews": reviews})

@csrf_exempt
def add_review(request):
    if request.user.is_anonymous:
        return JsonResponse({"status": 403, "message": "Unauthorized"})

    data = json.loads(request.body)
    response = post_review(data)
    if response is None:
        return JsonResponse({"status": 401, "message": "Error in posting review"})

    return JsonResponse({"status": 200})
