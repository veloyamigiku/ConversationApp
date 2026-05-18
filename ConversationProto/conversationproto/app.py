import boto3
from boto3.dynamodb.conditions import Key
from datetime import datetime
from datetime import timezone
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import MessagesPlaceholder
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

  body_data = event.get('body', {})
  print('type(body_data): {}'.format(type(body_data)))
  print('body_data: {}'.format(body_data))
  conversation_id = body_data.get('conversation_id')
  comment = body_data.get('comment')

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
  messages.append(('system', 'あなたは親切なアシスタントです。'))
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
