# EverPro Lead-to-Opportunity Automation: Architecture & AI Workflow

## Architecture Summary
The solution implements an event-driven architecture utilizing Salesforce Apex Triggers and Flows to automate the conversion of `PlanHub` leads. 
1. **Trigger Phase:** An `after insert` Apex Trigger (`LeadTrigger`) fires when a Lead is created. It delegates logic to a handler class (`LeadTriggerHandler`).
2. **Domain Matching & Account Management:** The handler filters Leads with `Lead_Source_Detail__c = 'PlanHub'`. It extracts the email domain, queries existing Accounts by `Domain__c`, and explicitly creates missing Accounts, stamping them with the correct `Domain__c` value. This explicitly ensures accurate relational mapping before lead conversion occurs.
3. **Automated Conversion:** The handler executes `Database.convertLead` to map the Lead to its matched Account, creating a Contact and an Opportunity.
4. **Opportunity Post-Processing:** The handler gathers the resulting `OpportunityId`s and synchronously updates their `StageName` to "Prospecting" and `CloseDate` to 30 days from `Date.today()`.
5. **Notification Flow:** A Record-Triggered Flow listens for `Opportunity` creations where `StageName = 'Prospecting'` (and the originating Lead Source details pass the condition) to dispatch an email alert asynchronously without blocking DML operations.

## Proposed Changes for Production at Scale
If this solution were moving to production with high transaction volumes, I would **decouple the Lead Conversion process into an Asynchronous context (Queueable Apex or Batch Apex).** 
* **Why:** The `Database.convertLead()` method is highly CPU-intensive and can consume substantial limits during bulk data imports (e.g., Data Loader or large API payloads). By evaluating criteria synchronously but processing the conversion in a Queueable job, we ensure bulk safety, avoid `System.LimitException: Too many SOQL queries` or `CPU time limit exceeded` errors, and guarantee resilience at scale. 

## AI Workflow
**AI Tool Used:** Claude 3.5 Sonnet / Trae AI (jarviz)

**Example Prompt 1 (Architecture & Apex Structure):**
> "Write a bulkified Salesforce Apex trigger and handler class. The logic needs to run after insert on the Lead object. Only process leads where the custom field Lead_Source_Detail__c equals 'PlanHub'. Extract the email domain from the lead's email. Check if an Account exists with that Domain__c. If it does, convert the lead into that account. If it doesn't, create the account first with the Domain__c populated, then convert the lead. Set the new Opportunity Stage to 'Prospecting' and Close Date to 30 days from today."

**Example Prompt 2 (Flow Configuration Guidance):**
> "How do I configure a Record-Triggered Flow to send an email alert when an Opportunity is created from this PlanHub lead conversion? What is the exact criteria I should use for the Start element so it only fires when StageName is 'Prospecting' and originated from PlanHub?"

**What the AI got right vs. What required manual adjustment:**
* **Got Right:** The AI perfectly structured the bulkified maps (`Map<String, Account>`, `Set<String> domains`) and correctly utilized the `Database.LeadConvert` class and `Database.convertLead` method, understanding the need to bulk-process the conversions.
* **Manual Adjustment:** Initially, AI suggestions often assume standard lead field mapping will handle custom field population on Account creation during native conversion. I had to manually adjust the architecture to *explicitly create the Account first* if it didn't exist. This is because letting the native `convertLead` method implicitly create the Account doesn't provide a direct way to populate the Account's `Domain__c` field without relying on declarative Lead Field Mapping in Setup, which violates the programmatic requirements of ensuring `Domain__c` is populated accurately in code. I also added a check to ensure `domainToFirstLead` map is used to prevent duplicate Account creation if a bulk upload contains multiple Leads with the same *new* domain.
