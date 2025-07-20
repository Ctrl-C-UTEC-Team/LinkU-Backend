import json
import boto3
import time
from decimal import Decimal
from boto3.dynamodb.conditions import Attr
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
feedback_table = dynamodb.Table('interview_feedback')

# Helper para convertir Decimal a int o float
def decimal_default(obj):
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError

def lambda_handler(event, context):
    method = event.get("httpMethod")

    if method == "POST":
        return create_feedback(event)
    elif method == "GET":
        return get_feedback_by_user(event)
    elif method == "DELETE":
        return delete_feedback(event)
    else:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Unsupported HTTP method"})
        }

# POST - Crear retroalimentación
def create_feedback(event):
    try:
        body = json.loads(event.get("body", "{}"))

        user_id = body.get("user_id")
        score = body.get("score")
        feedback = body.get("feedback")
        duration = body.get("duration")
        position = body.get("position")
        company = body.get("company")
        created_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")  # fecha legible

        if not all([user_id, score, feedback, duration, position, company]):
            return {"statusCode": 400, "body": json.dumps({"error": "All fields are required"})}

        if not (1 <= int(score) <= 100):
            return {"statusCode": 400, "body": json.dumps({"error": "Score must be between 1 and 100"})}

        feedback_id = int(time.time() * 1000)

        item = {
            "id": feedback_id,
            "user_id": int(user_id),
            "score": int(score),
            "feedback": feedback,
            "duration": int(duration),
            "position": position,
            "company": company,
            "created_at": created_at
        }

        feedback_table.put_item(Item=item)

        return {
            "statusCode": 201,
            "body": json.dumps({"message": "Interview feedback created"})
        }

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

# GET - Obtener feedback por user_id desde query param ?user_id=xxxx
def get_feedback_by_user(event):
    try:
        query = event.get("queryStringParameters", {})
        user_id_str = query.get("user_id") if query else None

        if not user_id_str or not user_id_str.isdigit():
            return {"statusCode": 400, "body": json.dumps({"error": "Invalid or missing user_id"})}

        user_id = int(user_id_str)

        response = feedback_table.scan(
            FilterExpression=Attr("user_id").eq(user_id)
        )

        items = response.get("Items", [])

        return {
            "statusCode": 200,
            "body": json.dumps(items, default=decimal_default)
        }

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

# DELETE - Eliminar feedback por ID
def delete_feedback(event):
    try:
        body = json.loads(event.get("body", "{}"))
        feedback_id = body.get("id")

        if not feedback_id:
            return {"statusCode": 400, "body": json.dumps({"error": "Missing feedback ID"})}

        feedback_id = int(feedback_id)

        response = feedback_table.delete_item(
            Key={"id": feedback_id},
            ReturnValues="ALL_OLD"
        )

        if "Attributes" not in response:
            return {"statusCode": 404, "body": json.dumps({"error": "Feedback not found"})}

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Interview feedback deleted"})
        }

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
