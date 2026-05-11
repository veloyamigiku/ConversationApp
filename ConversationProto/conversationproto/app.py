import boto3
from datetime import datetime
from datetime import timezone
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
import os
import time

# dynamodb init.
dynamodb = boto3.resource('dynamodb')
conversation_table = dynamodb.Table('ConversationProto')

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

def lambda_handler(event, context):
  print('exec.')

  request_iso_date, request_timestamp = get_datetime_info_for_logging()
  """
  request_now = datetime.now(timezone.utc)
  request_iso_date = request_now.isoformat()
  request_timestamp = int(time.time())
  """

  body_data = event.get('body', {})
  print('type(body_data): {}'.format(type(body_data)))
  print('body_data: {}'.format(body_data))
  conversation_id = body_data.get('conversation_id')
  comment = body_data.get('comment')

  request_log_item = {
    'conversation_id': conversation_id,
    'comment': comment,
    'created_at': request_iso_date,
    'timestamp': request_timestamp
  }
  print('request_log_item: {}'.format(request_log_item))

  try:
    conversation_table.put_item(Item=request_log_item)
  except Exception as e:
    print('===error: {}'.format(e))
  
  prompt = ChatPromptTemplate.from_messages([
    ('system', 'あなたは親切で簡潔に答えるAIアシスタントです。'),
    ('human', '{input}')
  ])

  chain = prompt | llm | StrOutputParser()

  response_text = chain.invoke({'input': comment})
  response_iso_date, response_timestamp = get_datetime_info_for_logging()
  response_log_item = {
    'conversation_id': conversation_id,
    'comment': response_text,
    'created_at': response_iso_date,
    'timestamp': response_timestamp
  }
  print('response_log_item: {}'.format(response_log_item))
  try:
    conversation_table.put_item(Item=response_log_item)
  except Exception as e:
    print('===error: {}'.format(e))

if __name__ == '__main__':
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument('--conversation_id', type=str, default=None)
  parser.add_argument('--comment', type=str, default=None)
  args = parser.parse_args()
  body = {
    'conversation_id': args.conversation_id,
    'comment': args.comment
  }
  event = {
    'body': body
  }
  lambda_handler(
    event=event,
    context=None)
