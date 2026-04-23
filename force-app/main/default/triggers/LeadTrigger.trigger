trigger LeadTrigger on Lead (after insert) {
    // Delegate logic to the handler class
    LeadTriggerHandler.handleAfterInsert(Trigger.new);
}
