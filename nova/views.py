from django.http import HttpResponse, JsonResponse
from nova.models import Doctor, Patient, Conversation, Message
from django.contrib.auth.models import User
from django.core import serializers
from django.views.decorators.csrf import csrf_exempt

from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token as TokenModel
from django.contrib.auth import authenticate, login


import random
import json

def request_body(request):
  body_unicode = request.body.decode('utf-8')
  return json.loads(body_unicode)

def get_token_logged_in_user(request):
  return TokenModel.objects.get(key=request.headers['token']).user

# Create your views here.
def index(request):
  return HttpResponse("Hello, world. You're at the NOVA index.")

# Schema: {"conversations": List<List<{from: String, text: String}>>}
def conversations(request, patient_id):
  try:
    # logged_in_doctor = Doctor.objects.get(user=request.user)
    logged_in_doctor = Doctor.objects.get(user=get_token_logged_in_user(request))

    patient = Patient.objects.get(pk=patient_id)

    conversations_with_messages = []

    if patient.doctor == logged_in_doctor:
      conversations = Conversation.objects.filter(participant=patient)

      conversations_with_messages = [serializers.serialize('json', [msg,]) for convo in conversations for msg in Message.objects.filter(conversation=convo)]

      # response_data = {'conversations': conversations_with_messages}
      # return JsonResponse(response_data)

      unserialized_conversations_with_messages = [msg for convo in conversations for msg in Message.objects.filter(conversation=convo).values()]

      return JsonResponse(unserialized_conversations_with_messages, safe=False)

    else:
      response_data = {'conversations': [], 'thisIsntYourPatient': True}
      return JsonResponse(response_data)

  except Doctor.DoesNotExist as dne:
    response_data = {'conversations': [], 'youreNotADoctor': True}
    return JsonResponse(response_data)

# Takes in a set of message model objects,
# Should return a number or a dict of keys=>numbers
def anxiety_value(messages):
  return random.choice([3, 2, 5, 1, 7, 5, 2])

# Schema: {"data": List<Int>}
def anxiety(request, patient_id):
  patient = Patient.objects.get(pk=patient_id)

  conversations = Conversation.objects.filter(patient=patient)

  anx_values = [anxiety_value(Message.objects.filter(conversation=convo)) for convo in conversations]

  response_data = {'data': anx_values}
  return JsonResponse(response_data)


def create_conversation(request):
  patient = Patient.objects.get(user=get_token_logged_in_user(request))

  conversation = Conversation.objects.create(participant=patient)

  response_data = {'converation_id': conversation.pk}
  return JsonResponse(response_data)

@csrf_exempt
def create_message(request, conversation_id):
  body = request_body(request)
  from_patient = body['from_patient']
  text = body['text']
  analysis_value = analyze_text(text)
  # patient = Patient.objects.get(user=request.user)
  patient = Patient.objects.get(user=get_token_logged_in_user(request))

  conversation = Conversation.objects.get(pk=conversation_id)

  if conversation.participant == patient:
    msg = Message.objects.create(conversation=conversation, from_patient=from_patient, text=text, analysis_value=analysis_value)

    response_data = {'message': serializers.serialize('json', [msg])}
    return JsonResponse(response_data)
  else:
    response_data = {'MustBePatientAndMustBeYourConvo': True}
    return JsonResponse(response_data)

def get_doctors_patients(request):
  try:
    # logged_in_doctor = Doctor.objects.get(user=request.user)
    logged_in_doctor = Doctor.objects.get(user=get_token_logged_in_user(request))

    patients = Patient.objects.filter(doctor=logged_in_doctor)

    # response_data = {'patients': serializers.serialize('json', patients)}
    # return JsonResponse(response_data)

    return JsonResponse(list(patients.values()), safe=False)

  except Doctor.DoesNotExist as dne:
    response_data = {'conversations': [], 'youreNotADoctor': True}
    return JsonResponse(response_data)

@csrf_exempt
def login(request):
  body = request_body(request)
  username = body['username']
  password = body['password']

  user = authenticate(request, username=username, password=password)

  if user is not None:
    token = None
    try:
      token = TokenModel.objects.get(user=user)
    except TokenModel.DoesNotExist as identifier:
      token = TokenModel.objects.create(user=user)

    isDoctor = False
    try:
      doctor = Doctor.objects.get(user=user)

      if doctor.pk > 0:
        isDoctor = True
    except:
      pass

    response_data = {
      'token': token.key,
      'isDoctor': isDoctor,
      'id': user.pk,
    }
    return JsonResponse(response_data)
  else:
    response_data = {'token': 'invalid'}
    return JsonResponse(response_data)
  
from nltk.sentiment.vader import SentimentIntensityAnalyzer

def analyze_text(text):
  # install Vader and make sure you download the lexicon as well
  sid = SentimentIntensityAnalyzer()

  ss = sid.polarity_scores(text)

  if ss["compound"] == 0.0:
    return 0
  elif ss["compound"] > 0.0:
    return 1
  else:
    return -1
