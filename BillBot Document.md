# 📘 Project Documentation – Automated Bill Processing System (AWS)

## 1. Introduction

The **Automated Bill Processing System** is a serverless application that simplifies the process of extracting, storing, and notifying bill details. Instead of manual data entry, users can upload bill images, and the system automatically processes them using AWS managed services.

**Why AWS Serverless?**

* Scalability without server management
* Pay-per-use model (cost-effective)
* High availability and reliability

---

## 2. System Architecture

### High-Level Diagram

*(Insert architecture image here or use the mermaid diagram from README)*

### Components

* **Amazon S3** → Stores uploaded bill images and triggers Lambda.
* **AWS Lambda** → Executes serverless code to process the event.
* **Amazon Textract** → Performs OCR to extract text from the bill image.
* **Amazon DynamoDB** → Stores structured bill data (amount, date, vendor, etc.).
* **Amazon SES** → Sends extracted bill details via email.
* **Amazon CloudWatch** → Monitors executions, logs, and metrics.
* *(Optional)* **AWS CloudTrail** → Tracks API activity for compliance and auditing.

---

## 3. Deployment Guide

### Pre-requisites

* AWS Account
* Verified SES emails
* IAM role with permissions for S3, Lambda, Textract, DynamoDB, SES, CloudWatch

### Steps

1. **Create S3 bucket** for uploads.
2. **Configure Lambda** function triggered by S3 event.
3. **Grant IAM role permissions** to Lambda for Textract, DynamoDB, SES, CloudWatch.
4. **Integrate Textract** within Lambda code for OCR.
5. **Create DynamoDB table** to store extracted data.
6. **Set up SES** and verify email addresses for notifications.
7. **Enable CloudWatch** to capture logs and set alarms.

---

## 4. Data Flow

1. User uploads bill → stored in **S3**.
2. **S3 event** triggers **Lambda** function.
3. **Lambda** calls **Textract** to extract text.
4. Extracted data stored in **DynamoDB**.
5. **Lambda** sends email with details using **SES**.
6. Logs recorded in **CloudWatch**.

---

## 5. Security Considerations

* Use IAM roles with **least privileges**.
* Apply **bucket policies** to restrict S3 access.
* Verify SES emails/domains to prevent spam.
* Enable **CloudTrail** for auditing sensitive actions.

---

## 6. Monitoring

* **CloudWatch Logs** → Track Lambda executions and errors.
* **CloudWatch Alarms** → Notify on error spikes or failures.
* **CloudTrail (Optional)** → Audit API activity across services.

---

## 7. Future Enhancements

* Add a **React dashboard** for uploading and viewing bills.
* Use **API Gateway** to expose APIs for third-party apps.
* Integrate **Amazon Comprehend** for smarter data classification.
* Add a **Cost Analysis Module** for tracking expenses.
* Support multi-user authentication with **Amazon Cognito**.
* Enable **SNS notifications** for SMS or push alerts.

---

## 8. References

* [AWS Textract Documentation](https://docs.aws.amazon.com/textract/)
* [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
* [Amazon DynamoDB Documentation](https://docs.aws.amazon.com/dynamodb/)
* [Amazon SES Documentation](https://docs.aws.amazon.com/ses/)
* [Amazon CloudWatch Documentation](https://docs.aws.amazon.com/cloudwatch/)
