import boto3
from boto3.dynamodb.conditions import Key
from datetime import datetime
from datetime import timezone
from fastapi import FastAPI
import json
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from mangum import Mangum
import os
from pydantic import BaseModel
import time

class ConversationRequest(BaseModel):
  conversation_id: str
  comment: str

app = FastAPI()

# dynamodb init.
dynamodb = boto3.resource('dynamodb')
conversation_table = dynamodb.Table('ConversationProto')

# lambda init
lambda_client = boto3.client('lambda')

# llm init.
llm = ChatGoogleGenerativeAI(
  model='gemini-2.5-flash',
  temperature=0.7,
  max_tokens=None,
  timeout=None,
  max_retries=2
)

def get_datetime_info_for_logging():
  now = datetime.now(timezone.utc)
  iso_date = now.isoformat()
  timestamp = int(time.time())
  return iso_date, timestamp

@app.post('/conversation')
def conversation(request: ConversationRequest):
  print('exec.')

  my_function_name = os.getenv('AWS_LAMBDA_FUNCTION_NAME', None)

  payload = {
    'resource': '/{proxy+}',
    'path': '/conversation_worker_task',
    'httpMethod': 'POST',
    'headers': {
      'content-type': 'application/json'
    },
    'multiValueHeaders': {},
    'requestContext': {
      'httpMethod': 'POST',
      'path': '/conversation_worker_task',
    },
    'body': json.dumps({
      'conversation_id': request.conversation_id,
      'comment': request.comment
    }),
    'isBase64Encoded': False
  }
  print('/conversation payload: {}'.format(payload))

  lambda_client.invoke(
    FunctionName=my_function_name,
    InvocationType='Event',
    Payload=json.dumps(payload)
  )

  return {
    'status': 'Accepted',
    'detail': 'Called conversation_worker_task asynchronously.'
  }

@app.post('/conversation_worker_task')
def conversation_worker_task(payload: dict):
  print('/conversation_worker_task payload: {}'.format(payload))
  
  request_iso_date, request_timestamp = get_datetime_info_for_logging()
  conversation_id = payload['conversation_id']
  comment = payload['comment']

  conversation_query_response = conversation_table.query(
    KeyConditionExpression=Key('conversation_id').eq(conversation_id),
    ScanIndexForward=True,
    Limit=5
  )
  conversation_items = conversation_query_response.get('Items', [])
  past_comments = [(item['role'], item['comment']) for item in conversation_items]

  request_log_item = {
    'conversation_id': conversation_id,
    'comment': comment,
    'created_at': request_iso_date,
    'timestamp': request_timestamp,
    'role': 'human',
  }
  print('request_log_item: {}'.format(request_log_item))
  
  try:
    conversation_table.put_item(Item=request_log_item)
  except Exception as e:
    print('===error: {}'.format(e))
  
  messages = []
  messages.append(('system', '英会話講師として世界共通基準CEFRのレベルA1で会話してください。'))
  if len(past_comments) > 0:
    messages.append(MessagesPlaceholder(variable_name='past_comments'))
  messages.append(('human', '{input}'))
  
  prompt = ChatPromptTemplate.from_messages(messages)

  chain = prompt | llm | StrOutputParser()
  
  response_text = chain.invoke({
    'input': comment,
    'past_comments': past_comments
  })
  response_iso_date, response_timestamp = get_datetime_info_for_logging()
  response_log_item = {
    'conversation_id': conversation_id,
    'comment': response_text,
    'created_at': response_iso_date,
    'timestamp': response_timestamp,
    'role': 'ai',
  }
  print('response_log_item: {}'.format(response_log_item))
  try:
    conversation_table.put_item(Item=response_log_item)
  except Exception as e:
    print('===error: {}'.format(e))

handler = Mangum(app)

if __name__ == '__main__':
  
  import uvicorn
  uvicorn.run(
    app,
    host='0.0.0.0',
    port=8000)
