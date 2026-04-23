public class LeadTriggerHandler {
    
    /**
     * Handles Lead Conversion for Leads coming from the 'PlanHub' source.
     * Matches Leads to Accounts based on email domain, or creates a new Account.
     * Also initializes the resulting Opportunity.
     */
    public static void handleAfterInsert(List<Lead> newLeads) {
        List<Lead> leadsToConvert = new List<Lead>();
        Set<String> domains = new Set<String>();
        Map<Id, String> leadIdToDomain = new Map<Id, String>();

        // 1. Filter Leads and extract domains
        for (Lead l : newLeads) {
            // Check for PlanHub source and ensure email exists
            if (l.Lead_Source_Detail__c == 'PlanHub' && String.isNotBlank(l.Email)) {
                String domain = l.Email.substringAfter('@').toLowerCase();
                if (String.isNotBlank(domain)) {
                    leadsToConvert.add(l);
                    domains.add(domain);
                    leadIdToDomain.put(l.Id, domain);
                }
            }
        }

        if (leadsToConvert.isEmpty()) {
            return; // Nothing to process
        }

        // 2. Query existing Accounts by Domain__c
        Map<String, Account> domainToAccount = new Map<String, Account>();
        for (Account acc : [SELECT Id, Domain__c FROM Account WHERE Domain__c IN :domains]) {
            domainToAccount.put(acc.Domain__c.toLowerCase(), acc);
        }

        // 3. Explicitly create missing Accounts
        // We do this instead of letting standard lead conversion auto-create it, 
        // because we need to ensure the Domain__c field is populated immediately.
        List<Account> accountsToInsert = new List<Account>();
        Map<String, Lead> domainToFirstLead = new Map<String, Lead>(); 

        for (Lead l : leadsToConvert) {
            String domain = leadIdToDomain.get(l.Id);
            if (!domainToAccount.containsKey(domain) && !domainToFirstLead.containsKey(domain)) {
                // Prevent duplicate accounts if multiple leads share the same new domain
                domainToFirstLead.put(domain, l);
                accountsToInsert.add(new Account(
                    Name = String.isNotBlank(l.Company) ? l.Company : domain + ' Account',
                    Domain__c = domain
                ));
            }
        }

        if (!accountsToInsert.isEmpty()) {
            insert accountsToInsert;
            for (Account acc : accountsToInsert) {
                domainToAccount.put(acc.Domain__c.toLowerCase(), acc);
            }
        }

        // 4. Prepare Lead Conversions
        List<Database.LeadConvert> converts = new List<Database.LeadConvert>();
        LeadStatus convertStatus = [SELECT Id, MasterLabel FROM LeadStatus WHERE IsConverted = true LIMIT 1];

        for (Lead l : leadsToConvert) {
            String domain = leadIdToDomain.get(l.Id);
            Account targetAcc = domainToAccount.get(domain);

            Database.LeadConvert lc = new Database.LeadConvert();
            lc.setLeadId(l.Id);
            lc.setAccountId(targetAcc.Id); // Attach to existing or newly created matched Account
            lc.setConvertedStatus(convertStatus.MasterLabel);
            lc.setDoNotCreateOpportunity(false); // Ensure Opportunity is created
            
            converts.add(lc);
        }

        // 5. Execute Conversions
        List<Database.LeadConvertResult> results = Database.convertLead(converts, false);

        // 6. Post-process: Update created Opportunities
        List<Id> oppIds = new List<Id>();
        for (Database.LeadConvertResult res : results) {
            if (res.isSuccess() && res.getOpportunityId() != null) {
                oppIds.add(res.getOpportunityId());
            } else if (!res.isSuccess()) {
                System.debug('Lead Conversion Failed for Lead ' + res.getLeadId() + ': ' + res.getErrors()[0].getMessage());
            }
        }

        if (!oppIds.isEmpty()) {
            List<Opportunity> oppsToUpdate = new List<Opportunity>();
            for (Id oppId : oppIds) {
                oppsToUpdate.add(new Opportunity(
                    Id = oppId,
                    StageName = 'Prospecting',
                    CloseDate = Date.today().addDays(30)
                ));
            }
            update oppsToUpdate;
        }
    }
}
