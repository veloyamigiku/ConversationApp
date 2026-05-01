import boto3
from datetime import datetime
from datetime import timezone
import time

dynamodb = boto3.resource('dynamodb')
conversation_table = dynamodb.Table('ConversationProto')

def lambda_handler(event, context):
  print('exec.')

  now = datetime.now(timezone.utc)
  iso_date = now.isoformat()
  timestamp = int(time.time())

  body_data = event.get('body', {})
  print('type(body_data): {}'.format(type(body_data)))
  print('body_data: {}'.format(body_data))
  conversation_id = body_data.get('conversation_id')
  comment = body_data.get('comment')

  item = {
    'conversation_id': conversation_id,
    'comment': comment,
    'created_at': iso_date,
    'timestamp': timestamp
  }
  print('item: {}'.format(item))

  try:
    conversation_table.put_item(Item=item)
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
