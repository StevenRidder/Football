# Cloud Deployment Guide - NFL Predictions Platform

## Overview
This guide shows how to deploy the NFL predictions platform with automated live score fetching in cloud environments.

---

## 🔧 Live Score Automation Options

### Option 1: AWS (Recommended)

**AWS EventBridge + Lambda**

```yaml
# serverless.yml or SAM template
Resources:
  ScoreFetcherFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: fetch_scores_lambda.handler
      Runtime: python3.9
      Timeout: 120
      Environment:
        Variables:
          PREDICTIONS_FILE_S3: s3://your-bucket/simulator_predictions.csv
      Events:
        HourlySchedule:
          Type: Schedule
          Properties:
            Schedule: cron(0 * * * ? *)  # Every hour
        SundayFrequent:
          Type: Schedule
          Properties:
            Schedule: cron(*/15 13-20 ? * SUN *)  # Every 15 min on Sundays 1-8pm ET
```

**Lambda Function** (`fetch_scores_lambda.py`):
```python
import json
import boto3
import requests
import pandas as pd
from io import StringIO

s3 = boto3.client('s3')

def handler(event, context):
    """Lambda handler to fetch scores and update S3 CSV"""
    
    # Download current predictions from S3
    bucket = 'your-bucket'
    key = 'simulator_predictions.csv'
    
    obj = s3.get_object(Bucket=bucket, Key=key)
    df = pd.read_csv(obj['Body'])
    
    # Fetch live scores from ESPN
    updates = fetch_and_update_scores(df)
    
    # Upload updated CSV back to S3
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    s3.put_object(Bucket=bucket, Key=key, Body=csv_buffer.getvalue())
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': f'Updated {updates} games',
            'timestamp': event['time']
        })
    }

def fetch_and_update_scores(df):
    # Same logic as /api/fetch-live-scores endpoint
    pass
```

**Deployment**:
```bash
# Install AWS SAM CLI
brew install aws-sam-cli

# Deploy
sam build
sam deploy --guided
```

**Cost**: ~$0.50/month (120 invocations/week × 4 weeks × $0.20/1M requests + compute)

---

### Option 2: Google Cloud Platform

**Cloud Scheduler + Cloud Functions**

```bash
# Deploy function
gcloud functions deploy fetch-nfl-scores \
  --runtime python39 \
  --trigger-http \
  --entry-point fetch_scores \
  --timeout 120s \
  --memory 512MB

# Create schedulers
gcloud scheduler jobs create http nfl-scores-hourly \
  --schedule="0 * * * *" \
  --uri="https://us-central1-YOUR_PROJECT.cloudfunctions.net/fetch-nfl-scores" \
  --http-method=POST

gcloud scheduler jobs create http nfl-scores-sunday-live \
  --schedule="*/15 13-20 * * 0" \
  --uri="https://us-central1-YOUR_PROJECT.cloudfunctions.net/fetch-nfl-scores" \
  --http-method=POST \
  --time-zone="America/New_York"
```

**Cost**: ~$0.80/month (120 invocations + Cloud Scheduler)

---

### Option 3: Azure

**Azure Functions + Timer Trigger**

```json
{
  "bindings": [
    {
      "name": "myTimer",
      "type": "timerTrigger",
      "direction": "in",
      "schedule": "0 0 * * * *"
    }
  ]
}
```

**Cost**: ~$0.40/month (Consumption plan)

---

### Option 4: Heroku (Simplest)

**Heroku Scheduler Add-on**

```bash
# Add scheduler
heroku addons:create scheduler:standard

# Configure via dashboard or CLI
heroku addons:open scheduler

# Add job: python scripts/fetch_live_scores.py
# Frequency: Every hour
```

**Cost**: $25/month (includes dyno + scheduler add-on)

---

### Option 5: Railway/Render (Modern PaaS)

**Railway Cron Jobs**

```toml
# railway.toml
[deploy]
  startCommand = "gunicorn app_flask:app"

[[cron]]
  schedule = "0 * * * *"
  command = "python scripts/fetch_live_scores.py"
```

**Cost**: ~$5-10/month

---

## 🖥️ Frontend Hosting Options

### Option A: Static Site (S3 + CloudFront)
- **Pros**: Cheapest, fastest
- **Cons**: Need API Gateway for backend
- **Cost**: ~$1/month

### Option B: Container (ECS Fargate / Cloud Run)
- **Pros**: Full Flask app, easy to scale
- **Cons**: More expensive
- **Cost**: ~$15-30/month

### Option C: Serverless (AWS Lambda + API Gateway)
- **Pros**: Pay per use, auto-scaling
- **Cons**: Cold starts
- **Cost**: ~$5/month

---

## 📊 Current Architecture

```
┌─────────────────┐
│  Flask Frontend │  (Port 9876)
│  app_flask.py   │
└────────┬────────┘
         │
         ├──────────> /api/fetch-live-scores  (Manual button trigger)
         ├──────────> /api/reload-data        (Cache refresh)
         └──────────> /                       (Dashboard)
                      
┌─────────────────────┐
│  ESPN API           │  (Live scores)
│  site.api.espn.com  │
└─────────────────────┘
```

---

## 🚀 Recommended Cloud Setup (Budget-Friendly)

**For Production:**

1. **Backend**: AWS Lambda + API Gateway (~$5/month)
   - Serverless Flask via Zappa or AWS SAM
   - Auto-scales, pay per use
   
2. **Score Fetching**: AWS EventBridge + Lambda (~$0.50/month)
   - Runs every hour + frequent on game days
   - Updates S3-hosted CSV
   
3. **Frontend**: S3 + CloudFront (~$1/month)
   - Static hosting for fast page loads
   - CDN for global access
   
4. **Database**: S3 for CSVs or DynamoDB (~$1/month)
   - CSV files work fine at current scale
   - Switch to DynamoDB if scaling to 100K+ users

**Total Cost**: ~$7-10/month

---

## 🔐 Environment Variables for Cloud

```bash
# AWS
AWS_REGION=us-east-1
S3_BUCKET=nfl-predictions-data
PREDICTIONS_FILE_KEY=simulator_predictions.csv

# ESPN API (no key needed - public)
ESPN_API_URL=https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard

# Flask
SECRET_KEY=your-secret-key-here
DEBUG=False
```

---

## 📝 Deployment Checklist

- [ ] Set up cloud account (AWS/GCP/Azure)
- [ ] Create S3 bucket or Cloud Storage for CSV files
- [ ] Deploy score fetching Lambda/Function
- [ ] Set up EventBridge/Scheduler for automation
- [ ] Deploy Flask app (Lambda/Cloud Run/ECS)
- [ ] Configure domain + SSL certificate
- [ ] Set up monitoring (CloudWatch/Stackdriver)
- [ ] Test live score fetching manually
- [ ] Verify scheduled triggers work
- [ ] Set up alerts for failed fetches

---

## 🧪 Testing Cloud Deployment

### Local Test
```bash
# Test the API endpoint
curl -X POST http://localhost:9876/api/fetch-live-scores

# Should return:
# {
#   "success": true,
#   "message": "Updated 107 games",
#   "games_updated": [...],
#   "timestamp": "2025-10-31T14:57:11"
# }
```

### Cloud Test (AWS Lambda)
```bash
# Invoke Lambda directly
aws lambda invoke \
  --function-name fetch-nfl-scores \
  --payload '{}' \
  response.json

cat response.json
```

---

## 📞 Support

For questions about cloud deployment:
1. Check AWS/GCP documentation
2. Review serverless framework docs
3. Test locally first before deploying

**Next Steps**: 
- Choose your cloud provider
- Follow the deployment guide above
- Set up monitoring and alerts
- Test the automation during a game day

