import json 
import boto3
from decimal import Decimal
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb')
users_table = dynamodb.Table('users')

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError

def lambda_handler(event, context):
    method = event.get("httpMethod")
    
    if method == "POST":
        return login_user(event)
    else:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Unsupported HTTP method"})
        }

def login_user(event):
    try:
        body = json.loads(event.get("body", "{}"))
        email = body.get("email")
        password = body.get("password")

        if not email or not password:
            return {"statusCode": 400, "body": json.dumps({"error": "Email and password are required"})}

        scan = users_table.scan(
            FilterExpression="email = :e AND password = :p",
            ExpressionAttributeValues={
                ":e": email,
                ":p": password
            }
        )

        if not scan["Items"]:
            return {"statusCode": 401, "body": json.dumps({"error": "Invalid credentials"})}

        user = scan["Items"][0]
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Login successful",
                "id": user["id"]
            }, default=decimal_default)
        }

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
