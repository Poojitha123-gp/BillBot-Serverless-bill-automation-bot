import json
import os
import boto3
import uuid
import re
from decimal import Decimal
from datetime import datetime

s3 = boto3.client('s3')
textract = boto3.client('textract')
dynamodb = boto3.resource('dynamodb')
ses = boto3.client('ses')

TABLE_NAME = os.environ.get('BILLS_TABLE', 'Bills')
SOURCE_EMAIL = os.environ.get('SOURCE_EMAIL')
DEST_EMAIL = os.environ.get('DEST_EMAIL')

table = dynamodb.Table(TABLE_NAME)

AMOUNT_RE = re.compile(r'(?:₹|Rs\.?|INR)?\s*([0-9\.,]+)', re.IGNORECASE)
DATE_RE = re.compile(r'(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})')

def extract_text_blocks(blocks):
    """Return concatenated text and dict of key->value from KEY_VALUE_SET blocks."""
    lines = []
    key_map = {}
    val_map = {}
    block_map = {}
    for b in blocks:
        block_map[b['Id']] = b
        if b['BlockType'] == 'LINE':
            lines.append(b.get('Text',''))
    # KEY_VALUE_SET parsing
    for b in blocks:
        if b['BlockType'] == 'KEY_VALUE_SET' and b['EntityTypes'][0] == 'KEY':
            key_text = ''
            val_text = ''
            # collect child WORDS for key
            for rel in b.get('Relationships', []):
                if rel['Type'] == 'CHILD':
                    for cid in rel['Ids']:
                        if block_map[cid]['BlockType'] == 'WORD':
                            key_text += block_map[cid].get('Text','') + ' '
                if rel['Type'] == 'VALUE':
                    for vid in rel['Ids']:
                        vblock = block_map.get(vid)
                        if vblock:
                            # get words inside VALUE block
                            for rel2 in vblock.get('Relationships', []):
                                if rel2['Type'] == 'CHILD':
                                    for w in rel2['Ids']:
                                        if block_map[w]['BlockType'] == 'WORD':
                                            val_text += block_map[w].get('Text','') + ' '
            if key_text.strip():
                key_map[key_text.strip()] = val_text.strip()
    return ' \n'.join(lines), key_map

def heuristics_from_text(raw_text, kv):
    """Try to guess vendor, date, amount."""
    vendor = None
    amount = None
    date = None
    # vendor: often in top lines
    first_lines = raw_text.splitlines()
    if first_lines:
        vendor = first_lines[0].strip()
    # check kv pairs for common keys
    for k, v in kv.items():
        lk = k.lower()
        if 'total' in lk or 'amount' in lk or 'balance' in lk:
            m = AMOUNT_RE.search(v)
            if m:
                amount = m.group(1).replace(',', '')
        if 'date' in lk:
            d = DATE_RE.search(v)
            if d:
                date = d.group(1)
        if 'vendor' in lk or 'seller' in lk or 'from' in lk:
            vendor = v
    # fallback scans on whole text for amount / date
    if not amount:
        m = AMOUNT_RE.search(raw_text)
        if m:
            amount = m.group(1).replace(',', '')
    if not date:
        d = DATE_RE.search(raw_text)
        if d:
            date = d.group(1)
    return vendor or "Unknown Vendor", date or str(datetime.utcnow().date()), amount or "N/A"

def lambda_handler(event, context):
    try:
        rec = event['Records'][0]
        bucket = rec['s3']['bucket']['name']
        key = rec['s3']['object']['key']
    except Exception as e:
        print("Event parsing error", e)
        raise

    # Call Textract synchronously (only works for images).
    try:
        response = textract.analyze_document(
            Document={'S3Object': {'Bucket': bucket, 'Name': key}},
            FeatureTypes=['FORMS', 'TABLES']
        )
    except Exception as e:
        print("Textract error:", e)
        raise

    blocks = response.get('Blocks', [])
    raw_text, kv = extract_text_blocks(blocks)
    vendor, date, amount = heuristics_from_text(raw_text, kv)
    bill_id = str(uuid.uuid4())

    item = {
        'BillId': bill_id,
        'S3Bucket': bucket,
        'S3Key': key,
        'Vendor': vendor,
        'Date': date,
        'Amount': str(amount),
        'RawText': raw_text[:20000]  # truncate long text
    }

    # to store in DynamoDB
    table.put_item(Item=item)

    # email summary with HTML formatting
    subject = f"Bill Processed: {vendor} - {amount}"

    body_text = f"""
    BillId: {bill_id}
    Vendor: {vendor}
    Date: {date}
    Amount: {amount}
    S3: s3://{bucket}/{key}

    RawText:
    {raw_text[:2000]}
    """

    body_html = f"""
    <html>
    <head>
      <style>
        body {{ font-family: Arial, sans-serif; }}
        .container {{ max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }}
        h2 {{ color: #2d6cdf; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th, td {{ text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }}
        .footer {{ margin-top: 20px; font-size: 12px; color: #666; }}
      </style>
    </head>
    <body>
      <div class="container">
        <h2>Bill Processed ✅</h2>
        <table>
          <tr><th>Bill ID</th><td>{bill_id}</td></tr>
          <tr><th>Vendor</th><td>{vendor}</td></tr>
          <tr><th>Date</th><td>{date}</td></tr>
          <tr><th>Amount</th><td>{amount}</td></tr>
          <tr><th>S3 Location</th><td>s3://{bucket}/{key}</td></tr>
        </table>

        <h3>Extracted Text (Preview)</h3>
        <pre style="white-space: pre-wrap; font-size: 13px; background: #f9f9f9; padding: 10px; border-radius: 5px;">
{raw_text[:1000]}
        </pre>

        <div class="footer">Automated by AWS Lambda + Textract + DynamoDB + SES</div>
      </div>
    </body>
    </html>
    """

    ses.send_email(
        Source=SOURCE_EMAIL,
        Destination={'ToAddresses': [DEST_EMAIL]},
        Message={
            'Subject': {'Data': subject},
            'Body': {
                'Text': {'Data': body_text},
                'Html': {'Data': body_html}
            }
        }
    )

    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Processed', 'BillId': bill_id})
    }
