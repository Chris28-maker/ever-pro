// Test 1: New Account scenario
Lead l1 = new Lead(
    FirstName = 'Chris', 
    LastName = 'TestOne', 
    Company = 'New Domain Company', 
    Email = 'chris@brandnewdomain.com', 
    Lead_Source_Detail__c = 'PlanHub'
);
insert l1;

// Test 2: Existing Account scenario
Lead l2 = new Lead(
    FirstName = 'Chris', 
    LastName = 'TestTwo', 
    Company = 'Different Company Name', 
    Email = 'chris2@brandnewdomain.com', 
    Lead_Source_Detail__c = 'PlanHub'
);
insert l2;

// Test 3: Control Group (No conversion)
Lead l3 = new Lead(
    FirstName = 'Chris', 
    LastName = 'TestThree', 
    Company = 'Control Company', 
    Email = 'chris@control.com', 
    Lead_Source_Detail__c = 'OtherSource'
);
insert l3;
