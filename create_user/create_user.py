import json 
import boto3
import re
import time
from decimal import Decimal
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb')
users_table = dynamodb.Table('users')

# Helper function to serialize Decimal to int or float
def decimal_default(obj):
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError

# Validations
def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def is_valid_password(password):
    return len(password) >= 8

def is_valid_username(username):
    return 3 <= len(username) <= 30

# Main handler
def lambda_handler(event, context):
    method = event.get("httpMethod")
    
    if method == "POST":
        return create_user(event)
    elif method == "GET":
        return get_user(event)
    elif method == "DELETE":
        return delete_user(event)
    else:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Unsupported HTTP method"})
        }

# Create user
def create_user(event):
    try:
        body = json.loads(event.get("body", "{}"))
        email = body.get("email")
        password = body.get("password")
        username = body.get("username")
        education_level = body.get("education_level", "")  # Optional

        if not all([email, password, username]):
            return {"statusCode": 400, "body": json.dumps({"error": "Email, password, and username are required"})}

        if not is_valid_email(email):
            return {"statusCode": 400, "body": json.dumps({"error": "Invalid email format"})}

        if not is_valid_password(password):
            return {"statusCode": 400, "body": json.dumps({"error": "Password must be at least 8 characters"})}

        if not is_valid_username(username):
            return {"statusCode": 400, "body": json.dumps({"error": "Username must be between 3 and 30 characters"})}

        scan = users_table.scan(
            FilterExpression="email = :emailVal",
            ExpressionAttributeValues={":emailVal": email}
        )
        if scan['Items']:
            return {"statusCode": 400, "body": json.dumps({"error": "A user with this email already exists"})}

        user_id = int(time.time() * 1000)

        item = {
            "id": user_id,
            "email": email,
            "password": password,
            "username": username
        }

        if education_level:
            item["education_level"] = education_level

        users_table.put_item(Item=item)

        return {
            "statusCode": 201,
            "body": json.dumps({"message": "User successfully created"})
        }

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

# Get user by ID from path: /users/{user_id}
def get_user(event):
    try:
        path_params = event.get("pathParameters", {})
        id_str = path_params.get("user_id")

        if not id_str or not id_str.isdigit():
            return {"statusCode": 400, "body": json.dumps({"error": "Invalid or missing ID"})}

        user_id = int(id_str)

        response = users_table.get_item(Key={"id": user_id})
        user = response.get("Item")

        if not user:
            return {"statusCode": 404, "body": json.dumps({"error": "User not found"})}

        user.pop("password", None)

        return {"statusCode": 200, "body": json.dumps(user, default=decimal_default)}

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

# Delete user by ID
def delete_user(event):
    try:
        body = json.loads(event.get("body", "{}"))
        user_id_raw = body.get("id")

        try:
            user_id = int(user_id_raw)
        except (TypeError, ValueError):
            return {"statusCode": 400, "body": json.dumps({"error": "Invalid or missing ID"})}

        response = users_table.delete_item(
            Key={"id": user_id},
            ReturnValues="ALL_OLD"
        )

        if "Attributes" not in response:
            return {"statusCode": 404, "body": json.dumps({"error": "User not found"})}

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "User deleted"})
        }

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
