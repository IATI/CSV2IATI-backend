activity_order = [
'overview',
'iati-activities',
'iati-activity',
'reporting-org',
'iati-identifier',
'other-activity-identifiers',
'activity-website',
'title',
'description',
'activity-status',
'activity-dates',
'contact-info',
'participating-org',
'activity-scope',
'recipient-country',
'recipient-region',
'location',
'sector',
'country_budget_items',
'thematic-marker',
'collaboration-type',
'default-finance-type',
'default-flow-type',
'default-aid-type',
'default-tied-status',
'budget',
'planned-disbursement',
'capital_spend',
'transaction',
'document-link',
'related-activity',
'conditions',
'result',
'legacy-data',
'crs-add',
'fss'
]

def key(s):
    if s in activity_order:
        return activity_order.index(s)
    else:
        return s

def order_activity(l):
    return sorted(l, key=key)
